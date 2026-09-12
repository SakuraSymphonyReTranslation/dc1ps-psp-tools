#!/usr/bin/env python3
"""Check PSP MC-speaker marking vs EN $n; count inline $n in EN messages."""

import glob
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

psp = json.load(open(r"F:\Games\PSP\dc1ps-psp-tools\analysis\dc1_script.json", encoding="utf-8"))
rows = {f["file"]: f["lines"] for f in psp["files"]}
print("=== PSP script_0001 first 8 lines ===")
for i, l in enumerate(rows["script_0001.obj"][:8]):
    print("[%d] name=%r  %s" % (i, l.get("name"), l.get("message", "")[:46].replace("\n", " ")))
print()
en = json.load(open(r"E:\Games\Da Capo Plus Communication\JSON_EN\0223a_e01.json", encoding="utf-8-sig"))
print("=== EN 0223a_e01 first 8 ===")
for i, r in enumerate(en[:8]):
    print("[%d] name=%-8r %s" % (i, r.get("name"), r.get("message", "")[:60].replace("\n", " ")))
print()
n_inline = 0
n_speaker = 0
for p in glob.glob(r"E:\Games\Da Capo Plus Communication\JSON_EN\*.json"):
    d = json.load(open(p, encoding="utf-8-sig"))
    for r in d:
        if "$n" in r.get("message", ""):
            n_inline += 1
        if r.get("name") == "$n":
            n_speaker += 1
print("EN messages with inline $n:", n_inline)
print("EN entries with $n speaker:", n_speaker)
