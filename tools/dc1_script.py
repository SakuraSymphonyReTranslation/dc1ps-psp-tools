#!/usr/bin/env python3
"""Read-only analyzer/dumper for D.C.P.S. (DC1) PSP script.bin."""

import argparse
import collections
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
    table_end = 0x10 + count * 4
    if table_end > len(data):
        raise ValueError("DC1 offset table exceeds file")
    offsets = list(struct.unpack_from("<%dI" % count, data, 0x10))
    if not offsets or offsets[0] != table_end:
        raise ValueError("DC1 first offset does not end the table")
    if any(b <= a for a, b in zip(offsets, offsets[1:])):
        raise ValueError("DC1 offsets are not strictly increasing")
    if offsets[-1] != len(data):
        raise ValueError("DC1 final offset 0x%X != file size 0x%X" % (offsets[-1], len(data)))
    return offsets


def parse_obj(blob):
    if len(blob) < 8 or blob[:4] != OBJ_MAGIC:
        return None
    declared = struct.unpack_from("<I", blob, 4)[0]
    return declared


def valid_sjis(raw):
    try:
        raw.decode(SJIS, "strict")
        return True
    except UnicodeDecodeError:
        return False


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
            if not valid_sjis(raw) or (op == MSG_OP and not raw.endswith(b"\n")):
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
            if valid_sjis(raw) and raw.endswith(b"\n"):
                yield i, op, raw
                i += 4 + length
                continue
        if op == CLEAR_OP:
            yield i, op, b""
            i += 2
            continue
        i += 1


def decode_payload(op, raw):
    if op in (MSG_OP, CHOICE2_OP) and raw.endswith(b"\n"):
        raw = raw[:-1]
    return raw.decode(SJIS, "replace")


def extract_blob(blob, script_index):
    lines = []
    current_name = ""
    current_name_offset = None
    for off, op, raw in scan_tokens(blob):
        if op == NAME_OP:
            current_name = decode_payload(op, raw)
            current_name_offset = off
        elif op == CLEAR_OP:
            current_name = ""
            current_name_offset = None
        elif op == MSG_OP:
            lines.append({
                "type": "dialogue",
                "script": script_index,
                "name": current_name,
                "message": decode_payload(op, raw),
                "name_offset": current_name_offset,
                "message_offset": off,
            })
        elif op in (NAV_OP, CHOICE_OP, CHOICE2_OP):
            lines.append({
                "type": "choice" if op in (CHOICE_OP, CHOICE2_OP) else "navigation",
                "script": script_index,
                "name": "",
                "message": decode_payload(op, raw),
                "name_offset": None,
                "message_offset": off,
            })
    return lines


def iter_scripts(data):
    offsets = parse_dc1(data)
    for index in range(len(offsets) - 1):
        yield index, data[offsets[index]:offsets[index + 1]]


def command_info(path):
    data = open(path, "rb").read()
    offsets = parse_dc1(data)
    blob_sizes = []
    token_counts = collections.Counter()
    lines = 0
    names = collections.Counter()
    placeholders = []
    bad_obj = 0
    for index, blob in iter_scripts(data):
        declared = parse_obj(blob)
        if declared != len(blob):
            bad_obj += 1
        blob_sizes.append(len(blob))
        for off, op, raw in scan_tokens(blob):
            token_counts[op.hex()] += 1
        extracted = extract_blob(blob, index)
        lines += len(extracted)
        for item in extracted:
            if item["name"]:
                names[item["name"]] += 1
            if "[name]" in item["message"]:
                placeholders.append({"script": index, "offset": item["message_offset"], "message": item["message"]})
    print("file:", path)
    print("magic: DC1\\0")
    print("size:", len(data), "(0x%X)" % len(data))
    print("format:", struct.unpack_from("<I", data, 0x0C)[0])
    print("offset_entries:", len(offsets), "scripts:", len(offsets) - 1)
    print("first_offset: 0x%X" % offsets[0], "last_offset: 0x%X" % offsets[-1])
    print("obj_size_mismatches:", bad_obj)
    print("blob_size_min_max:", min(blob_sizes), max(blob_sizes))
    print("token_counts:", dict(token_counts))
    print("text_lines:", lines, "unique_speakers:", len(names))
    print("custom_name_placeholders:", len(placeholders))
    for item in placeholders:
        print("  script_%04d +0x%X: %s" % (item["script"], item["offset"], item["message"]))


def command_dump(path, out_path):
    data = open(path, "rb").read()
    files = []
    index_files = []
    total = 0
    placeholder_count = 0
    for index, blob in iter_scripts(data):
        lines = extract_blob(blob, index)
        if not lines:
            continue
        fname = "script_%04d.obj" % index
        public = []
        sidecar = []
        for item in lines:
            row = {"message": item["message"]}
            if item["name"]:
                row["name"] = item["name"]
            public.append(row)
            sidecar.append({
                "type": item["type"],
                "name_offset": item["name_offset"],
                "message_offset": item["message_offset"],
            })
            placeholder_count += item["message"].count("[name]")
        files.append({"file": fname, "lines": public})
        index_files.append({"file": fname, "lines": sidecar})
        total += len(lines)
    out = {
        "game": "D.C.P.S. - Da Capo 1 Plus Situation Portable (PSP, NPJH50731)",
        "container": "DC1",
        "encoding": SJIS,
        "encryption": {"mode": "none"},
        "custom_name_placeholder": "[name]",
        "mc_name": {
            "japanese_default": "朝倉 純一",
            "romanized_default": "Asakura Jun'ichi",
            "display_name": "Jun'ichi",
            "surname": "Asakura",
            "given_name": "Jun'ichi",
            "note": "Keep [name] markers; they are runtime substitutions for the editable MC given name.",
        },
        "files": files,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    sidecar_path = os.path.splitext(out_path)[0] + ".index.json"
    with open(sidecar_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"files": index_files}, f, ensure_ascii=False, indent=1)
    print("wrote %s (%d scripts, %d lines, %d [name] markers)" % (out_path, len(files), total, placeholder_count))
    print("wrote %s" % sidecar_path)


def command_extract(path, out_dir):
    data = open(path, "rb").read()
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for index, blob in iter_scripts(data):
        out = os.path.join(out_dir, "script_%04d.obj" % index)
        with open(out, "wb") as f:
            f.write(blob)
        count += 1
    print("extracted %d OBJ blobs to %s" % (count, out_dir))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_info = sub.add_parser("info")
    p_info.add_argument("script_bin")
    p_dump = sub.add_parser("dump")
    p_dump.add_argument("script_bin")
    p_dump.add_argument("out_json")
    p_extract = sub.add_parser("extract")
    p_extract.add_argument("script_bin")
    p_extract.add_argument("out_dir")
    args = parser.parse_args(argv)
    try:
        if args.command == "info":
            command_info(args.script_bin)
        elif args.command == "dump":
            command_dump(args.script_bin, args.out_json)
        else:
            command_extract(args.script_bin, args.out_dir)
    except (OSError, ValueError, struct.error) as exc:
        print("error:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
