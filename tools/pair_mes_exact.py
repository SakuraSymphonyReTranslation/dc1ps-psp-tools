#!/usr/bin/env python3
"""Correct DCPC MES parser + opcode-fingerprint pairing (MES_EN <-> MES_RAW).

MES format (Circus DCPC, version 0x2163):
  u32 label_count
  u32 labels[label_count]          offsets into bytecode (relative to first token)
  u16 version (0x2163)
  tokens:
    0x00              -> 1 byte
    0x01..0x2C        -> [op][a][b]            3 bytes
    0x2D..0x49        -> [op][string\\0]
    0x4A..0x4D        -> [op][encstring\\0]    text XOR 0xFF
    0x4E..0xFF        -> [op][4 x u16]         9 bytes
The importer rebuilds tokens in order, so opcode sequences survive translation.
"""

import collections
import json
import os
import struct
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
SJIS = "shift_jis"


def parse_mes(path):
    data = open(path, "rb").read()
    if len(data) < 10:
        return None
    (count,) = struct.unpack_from("<I", data, 0)
    if count < 0 or count > (len(data) - 4) // 4:
        return None
    bytecode = 4 + count * 4
    if bytecode + 2 > len(data):
        return None
    (version,) = struct.unpack_from("<H", data, bytecode)
    if version != 0x2163:
        return None
    labels = list(struct.unpack_from("<%dI" % count, data, 4))
    pos = bytecode + 2
    ops = []
    texts = []
    n = len(data)
    while pos < n:
        op = data[pos]
        if op == 0x00:
            size = 1
        elif op <= 0x2C:
            size = 3
        elif op <= 0x49:
            end = data.find(b"\x00", pos + 1)
            if end < 0:
                break
            texts.append((op, data[pos + 1:end]))
            size = end - pos + 1
        elif op <= 0x4D:
            end = data.find(b"\x00", pos + 1)
            if end < 0:
                break
            raw = data[pos + 1:end]
            texts.append((op, bytes(b ^ 0xFF for b in raw)))
            size = end - pos + 1
        else:
            size = 9
        if pos + size > n:
            break
        ops.append(op)
        pos += size
    return {"labels": labels, "ops": ops, "texts": texts, "size": len(data)}


def fingerprint(m):
    return (tuple(m["ops"]), tuple(m["labels"]))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # 0) sanity: what's in the AlphaPatch EN-named files? EN or JP?
    ap = os.path.join(ROOT, "DCPCAlphaPatch_1.1", "AdvData", "mes", "0223a_e01.mes")
    m = parse_mes(ap)
    if m:
        samples = [t.decode(SJIS, "replace") for op, t in m["texts"][:6]]
        print("AlphaPatch 0223a_e01.mes text sample:")
        for s in samples:
            print("   ", s[:90])

    raw_dir = os.path.join(ROOT, "MES_RAW")
    en_dir = os.path.join(ROOT, "MES_EN")
    raw = {}
    for f in sorted(os.listdir(raw_dir)):
        if f.endswith(".mes"):
            m = parse_mes(os.path.join(raw_dir, f))
            if m:
                raw[f] = m
    en = {}
    for f in sorted(os.listdir(en_dir)):
        if f.endswith(".mes"):
            m = parse_mes(os.path.join(en_dir, f))
            if m:
                en[f] = m
    print("parsed raw:", len(raw), " en:", len(en))

    # 1) exact fingerprint match
    index = collections.defaultdict(list)
    for f, m in raw.items():
        index[fingerprint(m)].append(f)
    pairs = {}
    ambiguous = []
    for f, m in en.items():
        hits = index.get(fingerprint(m), [])
        if len(hits) == 1:
            pairs[f] = hits[0]
        elif len(hits) > 1:
            ambiguous.append((f, hits))
    print("EXACT opcode+label pairs:", len(pairs), " ambiguous:", len(ambiguous))

    # 2) fallback: opcode-sequence only
    op_index = collections.defaultdict(list)
    for f, m in raw.items():
        if fingerprint(m) not in index or True:
            op_index[tuple(m["ops"])].append(f)
    used = set(pairs.values())
    for f, m in en.items():
        if f in pairs:
            continue
        hits = [h for h in op_index.get(tuple(m["ops"]), []) if h not in used]
        if len(hits) == 1:
            pairs[f] = hits[0]
            used.add(hits[0])
    print("after opcode-only fallback:", len(pairs))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis", "mes_pairs_exact.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pairs, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print("wrote", out)

    # 3) verify: align pairs with equal entry counts, harvest JP->EN names
    name_votes = collections.defaultdict(collections.Counter)
    aligned = 0
    rj_dir = os.path.join(ROOT, "JSON_RAW")
    ej_dir = os.path.join(ROOT, "JSON_EN")
    for ef, rf in pairs.items():
        ejp = os.path.join(ej_dir, ef.replace(".mes", ".json"))
        rjp = os.path.join(rj_dir, rf.replace(".mes", ".json"))
        if not (os.path.exists(ejp) and os.path.exists(rjp)):
            continue
        try:
            ej = json.load(open(ejp, encoding="utf-8-sig"))
            rj = json.load(open(rjp, encoding="utf-8-sig"))
        except ValueError:
            continue
        if len(ej) != len(rj):
            continue
        aligned += 1
        for r, e in zip(rj, ej):
            rn, en_ = r.get("name"), e.get("name")
            if rn and en_ and rn != "$n" and en_ != "$n":
                name_votes[rn][en_] += 1
    print("equal-entry aligned pairs:", aligned)
    consistent = {k: v.most_common(1)[0][0] for k, v in name_votes.items() if len(v) == 1 and v.most_common(1)[0][1] >= 2}
    print("consistent JP->EN speaker names: %d" % len(consistent))
    for k in sorted(consistent):
        print("  ", k, "->", consistent[k])
    conflicted = {k: dict(v) for k, v in name_votes.items() if len(v) > 1}
    if conflicted:
        print("CONFLICTED:", json.dumps(conflicted, ensure_ascii=False)[:800])


if __name__ == "__main__":
    main()
