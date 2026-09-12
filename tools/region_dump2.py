#!/usr/bin/env python3
"""Dump PSP regions: every blob (title, lines, paired status) for problem ranges."""

import json
import sys

PAIRS = r"F:\Games\PSP\dc1ps-psp-tools\analysis\scene_pairs.json"
PSP_DUMP = r"F:\Games\PSP\dc1ps-psp-tools\analysis\dc1_script.json"

RANGES = [
    (40, 47), (146, 156), (209, 227), (285, 287), (350, 351),
    (499, 530), (544, 546), (556, 576), (718, 731), (740, 746),
    (770, 800), (840, 870), (605, 616), (686, 705),
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pairs = json.load(open(PAIRS, encoding="utf-8"))
    psp_to_en = {v["psp"]: (k, v) for k, v in pairs.items()}
    d = json.load(open(PSP_DUMP, encoding="utf-8"))
    rows = {int(f["file"][7:11]): f for f in d["files"]}
    for lo, hi in RANGES:
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
                print("  %s n=%3d  %-24s <- %s (en_n=%d, '%s')"
                      % (f["file"], len(lines), (title or "-")[:24],
                         pe[0], pe[1]["en_n"],
                         (pe[1].get("en_title") or "-")[:38]))
            else:
                print("  %s n=%3d  %-24s    UNPAIRED"
                      % (f["file"], len(lines), (title or "-")[:24]))
        print()


if __name__ == "__main__":
    main()
