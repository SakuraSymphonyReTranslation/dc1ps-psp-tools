#!/usr/bin/env python3
"""Pair JSON_RAW (Japanese) files with JSON_EN files via speaker-pattern sequences.

Pattern alphabet per entry:
  N = narration (no name)
  M = MC line   (name == '$n')
  X = named speaker line

The N/M/X sequence is language-independent: the same scene produces the same
speaker pattern in the Japanese dump and in the (re-flowed) translation.
Similarity = 2*LCS/(lenA+lenB). One-to-one greedy assignment.
"""

import collections
import json
import os
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
RAW = os.path.join(ROOT, "JSON_RAW")
EN = os.path.join(ROOT, "JSON_EN")


def load(dirname):
    out = {}
    for f in sorted(os.listdir(dirname)):
        if not f.endswith(".json"):
            continue
        try:
            data = json.load(open(os.path.join(dirname, f), encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, list):
            continue
        pat = []
        for row in data:
            name = row.get("name")
            if name is None or name == "":
                pat.append("N")
            elif name == "$n":
                pat.append("M")
            else:
                pat.append("X")
        out[f] = {"pattern": pat, "entries": data}
    return out


def lcs_len(a, b):
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            if x == y:
                cur.append(prev[j - 1] + 1)
            else:
                cur.append(max(prev[j], cur[-1]))
        prev = cur
    return prev[-1]


def sim(a, b):
    if not a or not b:
        return 0.0
    return 2.0 * lcs_len(a, b) / (len(a) + len(b))


def collapse(seq):
    """Collapse consecutive identical tokens: re-flow merges/splits narration runs."""
    out = []
    for t in seq:
        if not out or out[-1] != t:
            out.append(t)
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw = load(RAW)
    en = load(EN)
    print("raw files:", len(raw), " en files:", len(en))

    # Precompute collapsed patterns
    for d in (raw, en):
        for v in d.values():
            v["collapsed"] = collapse(v["pattern"])

    # Score every EN file against every RAW file (342*547 = ~187k LCS runs; fine)
    raw_items = list(raw.items())
    scores = []
    for ef, ev in en.items():
        best = []
        for rf, rv in raw_items:
            s = sim(ev["collapsed"], rv["collapsed"])
            # light bonus for same numeric prefix
            if ef[:4] == rf[:4]:
                s += 0.05
            best.append((s, rf))
        best.sort(reverse=True)
        scores.append((ef, best[0], best[1] if len(best) > 1 else (0.0, "")))

    # Greedy one-to-one: process by best score descending
    taken = set()
    pairs = {}
    pending = sorted(scores, key=lambda x: -x[1][0])
    for ef, (s1, rf1), (s2, _) in pending:
        if s1 < 0.35:
            continue
        if rf1 in taken:
            continue
        taken.add(rf1)
        pairs[ef] = {"raw": rf1, "score": round(s1, 4), "runner_up": round(s2, 4), "margin": round(s1 - s2, 4)}

    print("paired:", len(pairs), "/", len(en))
    margins = collections.Counter()
    for v in pairs.values():
        margins["margin>0.10" if v["margin"] > 0.10 else ("margin>0.05" if v["margin"] > 0.05 else "tight")] += 1
    print(dict(margins))

    # Harvest the JP->EN name map from confidently paired files with equal entry counts
    name_votes = collections.defaultdict(collections.Counter)
    exact_align = 0
    for ef, v in pairs.items():
        if v["score"] < 0.55 or v["margin"] < 0.08:
            continue
        ee = en[ef]["entries"]
        re_ = raw[v["raw"]]["entries"]
        if len(ee) != len(re_):
            continue
        exact_align += 1
        for r, e in zip(re_, ee):
            rn, en_ = r.get("name"), e.get("name")
            if rn and en_ and rn != "$n" and en_ != "$n":
                name_votes[rn][en_] += 1
    print("equal-length aligned pairs (high conf):", exact_align)
    print("JP names harvested:", len(name_votes))
    consistent = {k: v.most_common(1)[0][0] for k, v in name_votes.items() if len(v) == 1}
    print("consistent JP->EN names:", len(consistent))
    for k in sorted(consistent):
        print("  ", k, "->", consistent[k])
    conflicted = {k: dict(v) for k, v in name_votes.items() if len(v) > 1}
    if conflicted:
        print("CONFLICTED:", json.dumps(conflicted, ensure_ascii=False))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis", "raw_en_pairs.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pairs, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
