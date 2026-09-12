#!/usr/bin/env python3
"""EN roster + names.dat + PSP voice-anchor scan."""

import collections
import glob
import json
import struct
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
PSP_BIN = r"F:\Games\PSP\dc1ps-psp-tools\work\extracted\script.bin"
SJIS = "shift_jis"


def en_roster():
    names = collections.Counter()
    for p in glob.glob(r"%s\JSON_EN\*.json" % ROOT):
        try:
            d = json.load(open(p, encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        for r in d:
            n = r.get("name")
            if n and n != "$n":
                names[n] += 1
    return names


def names_dat():
    p = r"%s\AdvData\DAT\names.dat" % ROOT
    data = open(p, "rb").read()
    print("names.dat size:", len(data))
    print("head hex:", data[:64].hex())
    # try SJIS strings
    s = data.decode(SJIS, "replace")
    import re
    toks = re.findall(r"[\u3040-\u30ff\u4e00-\u9fffA-Za-z0-9_\\.]{4,}", s)
    print("SJIS-ish tokens:", len(toks))
    for t in toks[:40]:
        print("   ", t[:60])
    # ASCII strings
    asc = re.findall(rb"[\x20-\x7e]{4,}", data)
    print("ASCII strings:", len(asc))
    for a in asc[:40]:
        print("   A:", a[:60])


def psp_scan():
    data = open(PSP_BIN, "rb").read()
    print("PSP script.bin size:", len(data))
    for pat in (b"VOICE", b".wav", b"voice", b"0223", b"bg\\", b"bst\\"):
        idx = data.find(pat)
        cnt = data.count(pat)
        print("%-8r count=%d first_off=%s" % (pat, cnt, hex(idx) if idx >= 0 else "-"))
    # dump some ASCII strings
    import re
    strs = re.findall(rb"[\x20-\x7e]{6,}", data)
    print("ASCII strings >=6 chars:", len(strs))
    for s in strs[:30]:
        print("   ", s[:70])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=== JSON_EN top speakers ===")
    for n, c in en_roster().most_common(35):
        print("%6d  %s" % (c, n))
    print()
    names_dat()
    print()
    psp_scan()


if __name__ == "__main__":
    main()
