#!/usr/bin/env python3
"""Explore: what do EN and RAW MES files actually look like inside?"""

import collections
import os
import struct
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
SJIS = "shift_jis"


def parse_mes(path):
    data = open(path, "rb").read()
    (count,) = struct.unpack_from("<I", data, 0)
    bytecode = 4 + count * 4
    (version,) = struct.unpack_from("<H", data, bytecode)
    labels = list(struct.unpack_from("<%dI" % count, data, 4))
    pos = bytecode + 2
    tokens = []  # (op, kind, payload)
    n = len(data)
    while pos < n:
        op = data[pos]
        if op == 0x00:
            size = 1
            tokens.append((op, "ctl", None))
        elif op <= 0x2C:
            size = 3
            tokens.append((op, "ctl", data[pos + 1:pos + 3]))
        elif op <= 0x49:
            end = data.find(b"\x00", pos + 1)
            if end < 0:
                break
            tokens.append((op, "str", data[pos + 1:end]))
            size = end - pos + 1
        elif op <= 0x4D:
            end = data.find(b"\x00", pos + 1)
            if end < 0:
                break
            tokens.append((op, "enc", bytes(b ^ 0xFF for b in data[pos + 1:end])))
            size = end - pos + 1
        else:
            size = 9
            tokens.append((op, "u16x4", data[pos + 1:pos + 9]))
        if pos + size > n:
            break
        pos += size
    return {"labels": labels, "tokens": tokens, "size": len(data, ) if False else len(data)}


def show(path, name):
    m = parse_mes(path)
    print("=" * 70)
    print(name, " labels:", len(m["labels"]), " size:", m["size"])
    print("  labels[:12]:", m["labels"][:12])
    kinds = collections.Counter(t[1] for t in m["tokens"])
    print("  token kinds:", dict(kinds))
    enc = [t for t in m["tokens"] if t[1] == "enc"]
    strs = [t for t in m["tokens"] if t[1] == "str"]
    print("  --- first 10 plain strings ---")
    for t in strs[:10]:
        print("     op=%02x %r" % (t[0], t[2][:60]))
    print("  --- first 12 encrypted (dialogue) ---")
    for t in enc[:12]:
        print("     op=%02x %r" % (t[0], t[2][:80]))
    # asset references
    assets = [t[2].decode(SJIS, "replace") for t in strs
              if t[2][:1].isalpha() and (b"\\" in t[2] or t[2][:3] in (b"bg\\", b"voi"))]
    print("  --- asset refs (first 15) ---")
    for a in assets[:15]:
        print("     ", a)
    return m


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    en = show(os.path.join(ROOT, "MES_EN", "0223a_e01.mes"), "EN 0223a_e01.mes")
    raw = show(os.path.join(ROOT, "MES_RAW", "0223b_f02.mes"), "RAW 0223b_f02.mes")

    # find RAW files with identical label count as the EN file
    target = len(en["labels"])
    hits = []
    for f in sorted(os.listdir(os.path.join(ROOT, "MES_RAW"))):
        if not f.endswith(".mes"):
            continue
        data = open(os.path.join(ROOT, "MES_RAW", f), "rb").read()
        (count,) = struct.unpack_from("<I", data, 0)
        if count == target:
            hits.append(f)
    print("=" * 70)
    print("RAW files with label_count == %d: %d" % (target, len(hits)))
    print(hits[:20])


if __name__ == "__main__":
    main()
