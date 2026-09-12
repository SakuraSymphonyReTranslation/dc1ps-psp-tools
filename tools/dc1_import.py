#!/usr/bin/env python3
"""Rebuild D.C.P.S. (DC1) script.bin with English text from transfer.json.

Ports the proven D.C.II importer logic (dc2_psp_script.py):
  * token-level splice: replace 43 01/43 03/46 01/36 05/36 06 payloads by
    offset, keep everything else verbatim;
  * refresh OBJ size fields and the DC1 offset table;
  * re-anchor every relative-jump operand whose target moved:
      - 46 02 [u16] jumps that precede each 46 01 choice option;
      - the 22 00/01/02/03/05 control-flow family (scene re-entry /
        fast-forward / conditional-skip / skip-bookmark).
    Skipping either re-anchor crashes the VM once translated text changes
    any length ("Bad Execution Address" / jump to 0x00000000).
"""

import argparse
import bisect
import json
import os
import struct
import sys

DC1_MAGIC = b"DC1\x00"
OBJ_MAGIC = b"OBJ\x00"
SJIS = "shift_jis"

MSG_OP = b"\x43\x01"
CLEAR_OP = b"\x43\x02"
NAME_OP = b"\x43\x03"
NAV_OP = b"\x36\x05"
CHOICE_OP = b"\x36\x06"
CHOICE2_OP = b"\x46\x01"

MAX_MSG_LEN = 4096
MAX_NAME_LEN = 128
MAX_CHOICE_LEN = 512


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def valid_sjis(raw):
    try:
        raw.decode(SJIS, "strict")
        return True
    except UnicodeDecodeError:
        return False


def parse_dc1(data):
    if len(data) < 0x20 or data[:4] != DC1_MAGIC:
        raise ValueError("not a DC1 script.bin (bad magic)")
    total = struct.unpack_from("<I", data, 8)[0]
    if total != len(data):
        raise ValueError("size field 0x%X != file size 0x%X" % (total, len(data)))
    first = struct.unpack_from("<I", data, 0x10)[0]
    if first < 0x10 or (first - 0x10) % 4:
        raise ValueError("invalid DC1 offset table start 0x%X" % first)
    count = (first - 0x10) // 4
    offsets = list(struct.unpack_from("<%dI" % count, data, 0x10))
    if not offsets or offsets[0] != 0x10 + count * 4:
        raise ValueError("DC1 first offset does not end the table")
    if any(b <= a for a, b in zip(offsets, offsets[1:])):
        raise ValueError("DC1 offsets are not strictly increasing")
    if offsets[-1] != len(data):
        raise ValueError("DC1 final offset != file size")
    return offsets


def scan_tokens(blob):
    """Yield (offset, opcode, raw_payload) for verified string/control tokens."""
    i = 8  # OBJ header is not bytecode
    n = len(blob)
    while i < n:
        op = blob[i:i + 2]
        if op in (MSG_OP, NAME_OP):
            if i + 4 > n:
                i += 1
                continue
            length = u16(blob, i + 2)
            cap = MAX_MSG_LEN if op == MSG_OP else MAX_NAME_LEN
            if not (1 <= length <= cap) or i + 4 + length > n:
                i += 1
                continue
            raw = blob[i + 4:i + 4 + length]
            if not valid_sjis(raw) or (op == MSG_OP and not raw.endswith(b"\x0a")):
                i += 1
                continue
            yield i, op, raw
            i += 4 + length
            continue
        if op in (NAV_OP, CHOICE_OP):
            if i + 5 > n:
                i += 1
                continue
            length = u16(blob, i + 3)
            if not (1 <= length <= MAX_CHOICE_LEN) or i + 5 + length > n:
                i += 1
                continue
            raw = blob[i + 5:i + 5 + length]
            if valid_sjis(raw):
                yield i, op, raw
                i += 5 + length
                continue
        if op == CHOICE2_OP:
            if i + 4 > n:
                i += 1
                continue
            length = u16(blob, i + 2)
            if not (1 <= length <= MAX_MSG_LEN) or i + 4 + length > n:
                i += 1
                continue
            raw = blob[i + 4:i + 4 + length]
            if valid_sjis(raw) and raw.endswith(b"\x0a"):
                yield i, op, raw
                i += 4 + length
                continue
        if op == CLEAR_OP:
            yield i, op, b""
            i += 2
            continue
        i += 1


def _repl_token(op, new_txt, id_byte=None, suffix=b""):
    """Build the replacement token bytes; None = keep original."""
    if not new_txt:
        return None
    try:
        payload = new_txt.encode(SJIS)
    except UnicodeEncodeError:
        return None
    if suffix and not payload.endswith(suffix):
        payload += suffix
    head = op + (bytes([id_byte]) if id_byte is not None else b"")
    if len(payload) > 0xFFFF:
        return None
    return head + struct.pack("<H", len(payload)) + payload


def _scan_rel_jumps(blob, tokens):
    """Find the `22 xx` relative-control-flow instructions in one OBJ blob.

    (Ported from the DC2 tool; see PSP_TRANSLATION.md §4.3.)

        22 00 [u16 dist]                    jump forward  (target = pos+4+dist)
        22 01/02 [var][cmp][val][u16 skip]  conditional skip (patch u16 @+7)
        22 03/05 [u16 dist]                 skip-bookmark (target = pos+4+dist)

    A candidate is accepted only when it sits outside string tokens, its
    target is in bounds and looks like an instruction boundary (code-run byte
    <= 0x5F or exactly a token start).
    """
    spans = []
    for off, op, raw in tokens:
        hdr = 4 + (1 if op in (NAV_OP, CHOICE_OP) else 0)
        spans.append((off, off + hdr + len(raw)))
    span_starts = [s for s, _e in spans]

    def interval_free(lo, hi):
        i = bisect.bisect_right(span_starts, lo) - 1
        if i >= 0 and spans[i][1] > lo:
            return False
        j = bisect.bisect_right(span_starts, hi - 1) - 1
        return j == i

    def boundary_ok(x):
        i = bisect.bisect_right(span_starts, x) - 1
        if i < 0:
            return True
        s, e = spans[i]
        return x == s or x >= e

    out = []
    n = len(blob)
    for sub, size, opnd_off in ((0x00, 4, 2), (0x01, 9, 7), (0x02, 9, 7),
                                (0x03, 4, 2), (0x05, 4, 2)):
        pat = b"\x22" + bytes([sub])
        pos = 8
        while True:
            pos = blob.find(pat, pos)
            if pos < 0 or pos + size > n:
                break
            if interval_free(pos, pos + size):
                operand = u16(blob, pos + opnd_off)
                target = pos + size + operand
                if (8 <= target < n and boundary_ok(target)
                        and blob[target] <= 0x5F):
                    out.append((pos, size, opnd_off, operand, target))
            pos += 1
    out.sort()
    kept = []
    taken = []
    for pos, size, opnd_off, operand, target in out:
        lo, hi = pos + opnd_off, pos + opnd_off + 2
        if any(lo < t_hi and hi > t_lo for t_lo, t_hi in taken):
            continue
        taken.append((lo, hi))
        kept.append((pos, size, opnd_off, operand, target))
    return kept


def rebuild_blob(blob, msg_map, name_map, choice_map):
    """Rebuild one OBJ blob with translated tokens + re-anchored jumps."""
    tokens = list(scan_tokens(blob))

    events = []
    changes = []
    for off, op, raw in tokens:
        if op == MSG_OP:
            tok = _repl_token(op, msg_map.get(off), suffix=b"\x0a")
            old_len = 4 + len(raw)
        elif op == NAME_OP:
            tok = _repl_token(op, name_map.get(off))
            old_len = 4 + len(raw)
        elif op in (CHOICE_OP, NAV_OP):
            tok = _repl_token(op, choice_map.get(off), id_byte=blob[off + 2])
            old_len = 5 + len(raw)
        elif op == CHOICE2_OP:
            tok = _repl_token(op, choice_map.get(off), suffix=b"\x0a")
            old_len = 4 + len(raw)
        elif op == CLEAR_OP:
            tok = blob[off:off + 2]
            old_len = 2
        else:  # pragma: no cover
            tok = None
            old_len = 2
        new_bytes = tok if tok is not None else blob[off:off + old_len]
        events.append((off, old_len, new_bytes))
        changes.append((off, old_len, len(new_bytes)))

    changes.sort(key=lambda c: c[0])
    starts = [c[0] for c in changes]
    prefix = []
    acc = 0
    for _o, _ol, nl in changes:
        prefix.append(acc)
        acc += nl - _ol
    prefix.append(acc)

    def new_offset(x):
        return x + prefix[bisect.bisect_left(starts, x)]

    # re-anchor 46 02 jumps (choice menus)
    for off, op, _raw in tokens:
        if op != CHOICE2_OP:
            continue
        jpos = off - 4
        if jpos < 0 or blob[jpos:jpos + 2] != b"\x46\x02":
            continue
        operand = u16(blob, jpos + 2)
        target = off + operand
        new_operand = new_offset(target) - (new_offset(jpos) + 4)
        if not (0 <= new_operand <= 0xFFFF):
            print("warning: 46 02 jump @0x%X operand overflow %d"
                  % (jpos, new_operand), file=sys.stderr)
            new_operand &= 0xFFFF
        events.append((jpos, 4, b"\x46\x02" + struct.pack("<H", new_operand)))

    # re-anchor the 22 xx family
    occupied = [(s, s + l) for s, l, _b in events]
    for pos, size, opnd_off, operand, target in _scan_rel_jumps(blob, tokens):
        lo, hi = pos + opnd_off, pos + opnd_off + 2
        if any(lo < o_hi and hi > o_lo for o_lo, o_hi in occupied):
            continue
        new_operand = new_offset(target) - (new_offset(pos) + size)
        if new_operand == operand:
            continue
        if not (0 <= new_operand <= 0xFFFF):
            print("warning: 22 %02x jump @0x%X operand overflow %d"
                  % (blob[pos + 1], pos, new_operand), file=sys.stderr)
            continue
        events.append((lo, 2, struct.pack("<H", new_operand)))
        occupied.append((lo, hi))

    events.sort(key=lambda e: e[0])

    out = bytearray()
    cursor = 0
    for old_start, old_len, new_bytes in events:
        out += blob[cursor:old_start]
        out += new_bytes
        cursor = old_start + old_len
    out += blob[cursor:]
    out[4:8] = struct.pack("<I", len(out))  # refresh OBJ size
    return bytes(out)


def import_script_bin(src_bin, transfer_path, out_bin):
    data = open(src_bin, "rb").read()
    offsets = parse_dc1(data)
    doc = json.load(open(transfer_path, encoding="utf-8"))
    tfiles = doc.get("files", {})

    # convert string keys to int
    for blob, entry in tfiles.items():
        for k in entry:
            entry[k] = {int(off): txt for off, txt in entry[k].items()}

    new_blobs = []
    n_lines = 0
    n_skipped = 0
    for index in range(len(offsets) - 1):
        blob = data[offsets[index]:offsets[index + 1]]
        fname = "script_%04d.obj" % index
        entry = tfiles.get(fname)
        if entry:
            msg_map = entry.get("messages", {})
            name_map = entry.get("names", {})
            choice_map = entry.get("choices", {})
            n_lines += len(msg_map) + len(choice_map) + len(name_map)
            rebuilt = rebuild_blob(blob, msg_map, name_map, choice_map)
            if len(rebuilt) == len(blob) and rebuilt != blob:
                pass
            new_blobs.append(rebuilt)
        else:
            new_blobs.append(blob)

    # rebuild container: keep the original 16-byte header, fresh offset table
    n = len(new_blobs)
    body_start = 0x10 + 4 * (n + 1)
    total = body_start + sum(len(b) for b in new_blobs)
    out = bytearray()
    out += data[:0x10]
    out[8:12] = struct.pack("<I", total)  # refresh total-size field
    off = body_start
    for b in new_blobs:
        out += struct.pack("<I", off)
        off += len(b)
    out += struct.pack("<I", total)
    for b in new_blobs:
        out += b

    with open(out_bin, "wb") as f:
        f.write(out)
    print("wrote %s: %d scripts, %d replacements (%d -> %d bytes)"
          % (out_bin, n, n_lines, len(data), len(out)))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("script_bin")
    ap.add_argument("transfer_json")
    ap.add_argument("out_bin")
    args = ap.parse_args()
    import_script_bin(args.script_bin, args.transfer_json, args.out_bin)


if __name__ == "__main__":
    main()
