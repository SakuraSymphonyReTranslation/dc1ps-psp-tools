#!/usr/bin/env python3
"""Manual anchor hunt: EN 0223a_e01 scene in the PSP dump + survey of both corpora."""

import collections
import glob
import json
import re
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"


def load_psp():
    return json.load(open(r"F:\Games\PSP\dc1ps-psp-tools\analysis\dc1_script.json", encoding="utf-8"))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = load_psp()

    # 1) find the Kotori-intro scene: violin + chase
    print("=== PSP blobs containing バイオリン or ヴァイオリン ===")
    hits = collections.Counter()
    for f in d["files"]:
        for line in f["lines"]:
            m = line.get("message", "")
            if "バイオリン" in m or "ヴァイオリン" in m:
                hits[f["file"]] += 1
    for k, v in hits.most_common(15):
        print("%4d  %s" % (v, k))

    # 2) survey: line counts per blob, titles
    print()
    print("=== PSP scene titles (starting with ◆) sample ===")
    n_titles = 0
    for f in d["files"][:400]:
        for line in f["lines"]:
            m = line.get("message", "")
            if m.startswith("◆"):
                n_titles += 1
                if n_titles <= 20:
                    print("%s: %s" % (f["file"], m[:50]))
    print("total ◆-prefixed lines:", sum(
        1 for f in d["files"] for line in f["lines"] if line.get("message", "").startswith("◆")))

    # 3) EN titles
    print()
    print("=== JSON_EN ◆ / title-like lines ===")
    tcount = 0
    for p in sorted(glob.glob(r"%s\JSON_EN\*.json" % ROOT))[:60]:
        d2 = json.load(open(p, encoding="utf-8-sig"))
        for r in d2:
            m = r.get("message", "")
            if m.startswith("◆") or m.startswith("[") and "]" in m[:12]:
                tcount += 1
                if tcount <= 20:
                    print("%s: %r" % (p.split("\\")[-1], m[:50]))
    print("total EN title-ish in first 60 files:", tcount)

    # 4) Kanae hunt in PSP
    print()
    print("=== 佳苗 / カナエ / かなえ in PSP ===")
    c = 0
    for f in d["files"]:
        for line in f["lines"]:
            m = line.get("message", "") + line.get("name", "")
            if "佳苗" in m or "カナエ" in m or "かなえ" in m:
                c += 1
                if c <= 8:
                    print("%s [%s]: %s" % (f["file"], line.get("name", ""), m[:60]))
    print("total:", c)


if __name__ == "__main__":
    main()
