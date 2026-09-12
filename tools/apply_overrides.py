#!/usr/bin/env python3
"""Apply manual scene overrides + spot-check flagged pairs by first-line content."""

import json
import os
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
BASE = r"F:\Games\PSP\dc1ps-psp-tools\analysis"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pairs = json.load(open(os.path.join(BASE, "scene_pairs.json"), encoding="utf-8"))
    ov = json.load(open(os.path.join(BASE, "scene_overrides.json"), encoding="utf-8"))
    psp = json.load(open(os.path.join(BASE, "dc1_script.json"), encoding="utf-8"))
    psp_lines = {f["file"]: f["lines"] for f in psp["files"]}

    # apply overrides
    n_fix = n_drop = 0
    for ef, blob in ov["overrides"].items():
        if blob is None:
            pairs.pop(ef, None)
            n_drop += 1
        else:
            if ef in pairs:
                pairs[ef]["psp"] = blob
            else:
                pairs[ef] = {"psp": blob, "score": 0.0}
            n_fix += 1
    # recompute en_n stays, psp_n refresh
    for ef, v in pairs.items():
        lines = psp_lines.get(v["psp"])
        v["psp_n"] = len(lines) if lines else 0
    # uniqueness check
    seen = {}
    dups = []
    for ef, v in pairs.items():
        if v["psp"] in seen:
            dups.append((ef, seen[v["psp"]], v["psp"]))
        seen[v["psp"]] = ef
    print("fixed: %d, dropped: %d, total pairs: %d" % (n_fix, n_drop, len(pairs)))
    print("duplicate blob assignments:", dups if dups else "none")

    with open(os.path.join(BASE, "scene_pairs.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=1, sort_keys=True)

    # spot-check flagged pairs: print first 3 lines of each side
    print()
    for ef in ov["verify_at_line_level"]:
        v = pairs.get(ef)
        if not v:
            print("---- %s: UNPAIRED" % ef)
            continue
        en = json.load(open(os.path.join(ROOT, "JSON_EN", ef), encoding="utf-8-sig"))
        pl = psp_lines[v["psp"]]
        print("---- %s -> %s (en %d / psp %d)" % (ef, v["psp"], len(en), len(pl)))
        for i in range(min(3, len(en), len(pl))):
            ename = en[i].get("name", "")
            etxt = en[i].get("message", "")[:60]
            pname = pl[i].get("name", "")
            ptxt = pl[i].get("message", "")[:36]
            print("   EN[%d] %-10s %s" % (i, ename, etxt))
            print("   JP[%d] %-10s %s" % (i, pname, ptxt))


if __name__ == "__main__":
    main()
