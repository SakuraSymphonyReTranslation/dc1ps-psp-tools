#!/usr/bin/env python3
"""Show PSP blobs (title, lines, paired?) for given index ranges."""

import json
import sys

PAIRS = r"F:\Games\PSP\dc1ps-psp-tools\analysis\scene_pairs.json"
PSP_DUMP = r"F:\Games\PSP\dc1ps-psp-tools\analysis\dc1_script.json"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pairs = json.load(open(PAIRS, encoding="utf-8"))
    psp_to_en = {v["psp"]: (k, v) for k, v in pairs.items()}
    d = json.load(open(PSP_DUMP, encoding="utf-8"))
    rows = {int(f["file"][7:11]): f for f in d["files"]}

    ranges = [(145, 160), (595, 620), (690, 705)]
    for lo, hi in ranges:
        print("===== PSP %04d..%04d =====" % (lo, hi))
        for n in range(lo, hi + 1):
            f = rows.get(n)
            if not f:
                continue
            lines = f["lines"]
            title = next((l["message"] for l in lines
                          if l.get("message", "").startswith("◆")), None)
            pe = psp_to_en.get(f["file"])
            if pe:
                print("%s lines=%3d  %-22s <- %s (en_n=%d, score=%.2f)"
                      % (f["file"], len(lines), (title or "-")[:22],
                         pe[0], pe[1]["en_n"], pe[1]["score"]))
            else:
                print("%s lines=%3d  %-22s    UNPAIRED"
                      % (f["file"], len(lines), (title or "-")[:22]))
        print()


if __name__ == "__main__":
    main()
