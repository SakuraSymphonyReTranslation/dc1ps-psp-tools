#!/usr/bin/env python3
"""Pair MES_EN with MES_RAW via MES bytecode structure (labels + opcode histogram)."""

import collections
import json
import os
import struct
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
RAW_DIR = os.path.join(ROOT, "MES_RAW")
EN_DIR = os.path.join(ROOT, "MES_EN")


def parse_mes_deep(path):
    data = open(path, "rb").read()
    if len(data) < 6:
        return None
    label_count = struct.unpack_from("<I", data, 0)[0]
    bytecode = 4 + label_count * 4
    if bytecode + 2 > len(data):
        return None
    version = struct.unpack_from("<H", data, bytecode)[0]
    counts = collections.Counter()
    pos = bytecode + 2
    text_ops = []
    while pos < len(data):
        op = data[pos]
        if 0x00 <= op <= 0x2C:
            size = 1 if op == 0 else 3
        elif 0x2D <= op <= 0x4D:
            end = data.find(b"\x00", pos + 1)
            if end < 0:
                break
            size = end - pos + 1
            text_ops.append((op, data[pos + 1:end]))
        elif op >= 0x4E:
            size = 9
        else:
            size = 1
        if pos + size > len(data):
            break
        counts[op] += 1
        pos += size
    return {
        "labels": label_count,
        "version": version,
        "opcounts": dict(counts),
        "text_ops": text_ops,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw = {}
    for f in sorted(os.listdir(RAW_DIR)):
        if f.endswith(".mes"):
            raw[f] = parse_mes_deep(os.path.join(RAW_DIR, f))
    en = {}
    for f in sorted(os.listdir(EN_DIR)):
        if f.endswith(".mes"):
            en[f] = parse_mes_deep(os.path.join(EN_DIR, f))
    print("raw:", len(raw), "en:", len(en))

    # index raw by (labels, version, frozenset of opcode counts ignoring text ops)
    def key(m):
        ops = tuple(sorted((k, v) for k, v in m["opcounts"].items()))
        return (m["labels"], m["version"], ops)

    raw_by_key = collections.defaultdict(list)
    for f, m in raw.items():
        if m:
            raw_by_key[key(m)].append(f)

    exact = {}
    near = {}
    for f, m in en.items():
        if not m:
            continue
        k = key(m)
        if k in raw_by_key and len(raw_by_key[k]) == 1:
            exact[f] = raw_by_key[k][0]
        else:
            # near match: same labels+version, minimize opcode histogram distance
            best = None
            best_d = None
            for rf, rm in raw.items():
                if not rm or rm["labels"] != m["labels"] or rm["version"] != m["version"]:
                    continue
                keys = set(m["opcounts"]) | set(rm["opcounts"])
                d = sum(abs(m["opcounts"].get(x, 0) - rm["opcounts"].get(x, 0)) for x in keys)
                if best_d is None or d < best_d:
                    best_d = d
                    best = rf
            if best is not None:
                near[f] = (best, best_d)
    print("exact structural pairs:", len(exact))
    print("near pairs:", len(near))
    good_near = {f: v[0] for f, v in near.items() if v[1] <= 3}
    print("near pairs (dist<=3):", len(good_near))
    print("near pair distance histogram:", collections.Counter(v[1] for v in near.values()))

    pairs = dict(exact)
    pairs.update(good_near)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis", "en_raw_mes_pairs.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pairs, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print("wrote", out, "with", len(pairs), "pairs")

    # sanity: verify name-consistency via a JP->EN name map built from pairs
    name_map = collections.defaultdict(collections.Counter)
    for ef, rf in pairs.items():
        ej = json.load(open(os.path.join(ROOT, "JSON_EN", ef.replace(".mes", ".json")), encoding="utf-8-sig"))
        rj = json.load(open(os.path.join(ROOT, "JSON_RAW", rf.replace(".mes", ".json")), encoding="utf-8-sig"))
        if len(ej) != len(rj):
            continue
        for re_, ee in zip(rj, ej):
            rn = re_.get("name")
            en_ = ee.get("name")
            if rn and en_ and rn != "$n":
                name_map[rn][en_] += 1
    consistent = sum(1 for k, v in name_map.items() if len(v) == 1 and v.most_common(1)[0][1] >= 1)
    total = len(name_map)
    print("JP names seen: %d, consistently mapped: %d" % (total, consistent))
    for k in list(name_map)[:15]:
        print("  ", k, "->", name_map[k].most_common(2))


if __name__ == "__main__":
    main()
