#!/usr/bin/env python3
"""Verify a rebuilt DC1 script.bin.

  1. container + OBJ headers valid;
  2. every re-anchored 22 xx / 46 02 jump in the NEW blob lands on the same
     opcode byte as the old target did in the OLD blob (pairwise check);
  3. no remaining untranslated-looking text inside replaced regions
     (spot check: dump a few translated lines);
  4. [name] markers preserved.
"""

import json
import struct
import sys

sys.path.insert(0, r"F:\Games\PSP\dc1ps-psp-tools\tools")
import dc1_import as I  # noqa: E402

OLD = r"F:\Games\PSP\dc1ps-psp-tools\work\extracted\script.bin"
NEW = r"F:\Games\PSP\dc1ps-psp-tools\work\script_en.bin"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    old = open(OLD, "rb").read()
    new = open(NEW, "rb").read()
    off_o = I.parse_dc1(old)
    off_n = I.parse_dc1(new)
    print("scripts: old %d, new %d" % (len(off_o) - 1, len(off_n) - 1))
    assert len(off_o) == len(off_n)

    bad_obj = 0
    total_jumps_checked = 0
    jump_mismatches = []
    name_markers = 0
    en_lines = 0
    for idx in range(len(off_o) - 1):
        ob = old[off_o[idx]:off_o[idx + 1]]
        nb = new[off_n[idx]:off_n[idx + 1]]
        if nb[:4] != I.OBJ_MAGIC or struct.unpack_from("<I", nb, 4)[0] != len(nb):
            bad_obj += 1
        # token scan both
        ot = list(I.scan_tokens(ob))
        nt = list(I.scan_tokens(nb))
        # count English-looking messages + [name] markers
        for _o, op, raw in nt:
            if op in (I.MSG_OP, I.CHOICE2_OP):
                txt = raw.decode("shift_jis", "replace")
                if "[name]" in txt:
                    name_markers += 1
                if txt[:1].isascii() and any(c.isalpha() for c in txt[:20]):
                    en_lines += 1
        # jump verification: for each rel-jump found in the OLD blob, the
        # corresponding instruction in the NEW blob must have a target whose
        # first opcode byte matches the old target's byte.
        ojumps = I._scan_rel_jumps(ob, ot)
        if not ojumps:
            continue
        # build new offset map exactly like rebuild does
        changes = []
        for off, op, raw in ot:
            if op == I.MSG_OP or op == I.NAME_OP:
                old_len = 4 + len(raw)
            elif op in (I.CHOICE_OP, I.NAV_OP):
                old_len = 5 + len(raw)
            elif op == I.CHOICE2_OP:
                old_len = 4 + len(raw)
            else:
                old_len = 2
            # find matching token in new by order
            changes.append((off, old_len))
        # match tokens by order (rebuild preserves order)
        if len(nt) != len(ot):
            print("script %d: token count changed %d -> %d" % (idx, len(ot), len(nt)))
            continue
        import bisect
        starts = [c[0] for c in changes]
        lens = [c[1] for c in changes]
        newlens = []
        for (ooff, op, oraw), (noff, nop, nraw) in zip(ot, nt):
            newlens.append(len(nb[noff:noff + (4 if nop in (I.MSG_OP, I.NAME_OP, I.CHOICE2_OP) else 5) + len(nraw)]) if nop not in (I.CLEAR_OP,) else 2)
        # simpler: cumulative positions of new tokens
        newpos = [noff for noff, _op, _raw in nt]
        prefix = []
        acc = 0
        for (ooff, ol), nl in zip(changes, newlens):
            prefix.append(acc)
            acc += nl - ol
        prefix.append(acc)

        def new_off(x):
            return x + prefix[bisect.bisect_left(starts, x)]

        for pos, size, opnd_off, operand, target in ojumps:
            total_jumps_checked += 1
            new_pos = new_off(pos)
            new_opnd = struct.unpack_from("<H", nb, new_pos + opnd_off)[0]
            new_target = new_pos + size + new_opnd
            if new_target >= len(nb):
                jump_mismatches.append((idx, pos, "OOB", new_target))
                continue
            old_byte = ob[target] if target < len(ob) else -1
            new_byte = nb[new_target]
            if old_byte != new_byte:
                jump_mismatches.append((idx, pos, hex(old_byte), hex(new_byte)))

    print("bad OBJ headers:", bad_obj)
    print("rel-jumps checked: %d, mismatches: %d" % (total_jumps_checked, len(jump_mismatches)))
    for m in jump_mismatches[:10]:
        print("   ", m)
    print("EN-looking message tokens:", en_lines)
    print("[name] markers preserved:", name_markers)

    # spot dump script_0001 from the new file
    d = off_n
    blob = new[d[1]:d[2]]
    print()
    print("=== script_0001 first lines (new) ===")
    count = 0
    for off, op, raw in I.scan_tokens(blob):
        txt = raw.decode("shift_jis", "replace").rstrip("\n")
        print("  %-6s %s" % (op.hex(), txt[:58].replace("\n", " | ")))
        count += 1
        if count >= 10:
            break


if __name__ == "__main__":
    main()
