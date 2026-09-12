#!/usr/bin/env python3
"""Compare speaker rosters: JSON_RAW vs DC1 PSP dump."""

import collections
import glob
import json
import sys


def top_speakers(pattern, limit=45):
    names = collections.Counter()
    for p in glob.glob(pattern):
        try:
            d = json.load(open(p, encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict):
            rows = [r for f in d.get("files", []) for r in f.get("lines", [])]
        else:
            rows = d
        for r in rows:
            n = r.get("name")
            if n and n != "$n":
                names[n] += 1
    return names


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw = top_speakers(r"E:\Games\Da Capo Plus Communication\JSON_RAW\*.json")
    psp = top_speakers(r"F:\Games\PSP\dc1ps-psp-tools\analysis\dc1_script.json")
    print("=== JSON_RAW top speakers ===")
    for n, c in raw.most_common(40):
        print("%6d  %s" % (c, n))
    print()
    print("=== RAW vs PSP roster ===")
    pc_only = [n for n in psp if n in ("アリス", "環", "眞子", "佳苗", "香澄", "暦", "ななこ", "頼子", "和泉子")]
    for n in pc_only:
        print("%-8s RAW: %5d   PSP: %5d" % (n, raw.get(n, 0), psp.get(n, 0)))
    print()
    only_psp = [n for n, c in psp.most_common(60) if raw.get(n, 0) == 0]
    print("Top PSP speakers MISSING from RAW:", only_psp[:20])
    only_raw = [n for n, c in raw.most_common(60) if psp.get(n, 0) == 0]
    print("Top RAW speakers missing from PSP:", only_raw[:20])


if __name__ == "__main__":
    main()
