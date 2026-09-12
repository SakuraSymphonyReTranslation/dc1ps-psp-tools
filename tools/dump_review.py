#!/usr/bin/env python3
"""Dump the full scene-pair review table (PSP order) for human verification."""

import json
import sys

PAIRS = r"F:\Games\PSP\dc1ps-psp-tools\analysis\scene_pairs.json"
OUT = r"F:\Games\PSP\dc1ps-psp-tools\analysis\scene_review.txt"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pairs = json.load(open(PAIRS, encoding="utf-8"))
    rows = sorted(pairs.items(), key=lambda kv: int(kv[1]["psp"][7:11]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("%-18s %-16s %6s %5s %5s  %s\n"
                % ("EN_FILE", "PSP_BLOB", "SCORE", "EN_N", "PSP_N", "JP_TITLE | EN_TITLE"))
        for ef, v in rows:
            flag = "!" if v["score"] < 0.35 else " "
            f.write("%s%-17s %-16s %6.2f %5d %5d  %s | %s\n"
                    % (flag, ef, v["psp"], v["score"], v["en_n"], v["psp_n"],
                       (v.get("psp_title") or "-----"), (v.get("en_title") or "-----")))
    print("wrote", OUT, "with", len(rows), "rows")


if __name__ == "__main__":
    main()
