#!/usr/bin/env python3
"""Pair JSON_EN (English, renamed files) with JSON_RAW (Japanese) by structure."""

import json
import os
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
R = os.path.join(ROOT, "JSON_RAW")
E = os.path.join(ROOT, "JSON_EN")


def struct_sig(path):
    d = json.load(open(path, encoding="utf-8-sig"))
    names = [r.get("name") for r in d]
    dollar = tuple(i for i, n in enumerate(names) if n == "$n")
    none = tuple(i for i, n in enumerate(names) if n is None)
    return (len(d), dollar, none)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw_index = {}
    for f in sorted(os.listdir(R)):
        if f.endswith(".json"):
            try:
                raw_index.setdefault(struct_sig(os.path.join(R, f)), []).append(f)
            except Exception:
                pass
    pairs = {}
    ambiguous = []
    unmatched = []
    for f in sorted(os.listdir(E)):
        if not f.endswith(".json"):
            continue
        s = struct_sig(os.path.join(E, f))
        if s not in raw_index:
            unmatched.append(f)
        elif len(raw_index[s]) == 1:
            pairs[f] = raw_index[s][0]
        else:
            ambiguous.append((f, raw_index[s]))
    print("unique pairs:", len(pairs), " ambiguous:", len(ambiguous), " unmatched:", len(unmatched))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis", "en_raw_pairs.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pairs, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print("wrote", out)
    if unmatched:
        print("unmatched:", unmatched[:20])
    for a in ambiguous[:10]:
        print("AMBIG:", a[0], "->", a[1][:5])


if __name__ == "__main__":
    main()
