#!/usr/bin/env python3
"""Inspect alignment neighborhoods around suspicious pairs."""

import json
import sys

PAIRS = r"F:\Games\PSP\dc1ps-psp-tools\analysis\scene_pairs.json"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pairs = json.load(open(PAIRS, encoding="utf-8"))
    # order by psp script index
    rows = sorted(pairs.items(), key=lambda kv: int(kv[1]["psp"][7:11]))
    targets = ["script_000", "script_001", "script_002"]
    for ef, v in rows:
        n = int(v["psp"][7:11])
        if n <= 30 or 595 <= n <= 620 or 690 <= n <= 705 or 145 <= n <= 160:
            print("%-18s -> %-16s score=%6.3f  en_n=%3d psp_n=%3d  %s | %s"
                  % (ef, v["psp"], v["score"], v["en_n"], v["psp_n"],
                     (v.get("psp_title") or "-")[:24], (v.get("en_title") or "-")[:40]))


if __name__ == "__main__":
    main()
