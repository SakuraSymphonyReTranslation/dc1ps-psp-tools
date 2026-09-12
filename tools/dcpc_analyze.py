#!/usr/bin/env python3
"""Inventory Plus Communication MES/JSON and compare text with DC1 dump."""

import argparse
import collections
import json
import os
import struct
import sys

SJIS = "shift_jis"


def normalized(text):
    return "".join(text.replace("\r", "").replace("\n", "").split()).replace("「", "").replace("」", "")


def parse_mes(path):
    data = open(path, "rb").read()
    if len(data) < 6:
        raise ValueError("MES too small")
    label_count = struct.unpack_from("<I", data, 0)[0]
    bytecode = 4 + label_count * 4
    if bytecode + 2 > len(data):
        raise ValueError("invalid MES label table")
    version = struct.unpack_from("<H", data, bytecode)[0]
    counts = collections.Counter()
    pos = bytecode + 2
    while pos < len(data):
        op = data[pos]
        if 0x00 <= op <= 0x2C:
            size = 1 if op == 0 else 3
        elif 0x2D <= op <= 0x49 or 0x4A <= op <= 0x4D:
            end = data.find(b"\x00", pos + 1)
            if end < 0:
                break
            size = end - pos + 1
        elif op >= 0x4E:
            size = 9
        else:
            size = 1
        if pos + size > len(data):
            break
        counts["%02X" % op] += 1
        pos += size
    return {"size": len(data), "label_count": label_count, "bytecode_offset": bytecode, "version": "0x%04X" % version, "opcode_counts": dict(counts)}


def load_json_dir(path):
    result = []
    for name in sorted(os.listdir(path)):
        if not name.lower().endswith(".json"):
            continue
        full = os.path.join(path, name)
        try:
            data = json.load(open(full, encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, list):
            for index, row in enumerate(data):
                if isinstance(row, dict) and row.get("message"):
                    result.append({"file": name, "index": index, "name": row.get("name"), "message": row["message"]})
    return result


def load_dc1(path):
    data = json.load(open(path, encoding="utf-8"))
    rows = []
    for file_row in data.get("files", []):
        for index, row in enumerate(file_row.get("lines", [])):
            rows.append({"file": file_row.get("file"), "index": index, "name": row.get("name"), "message": row.get("message", "")})
    return rows


def inventory(root, dc1_json=None):
    report = {"source": root, "mes": {}, "json": {}, "mapping": {}}
    for kind in ("MES_RAW", "MES_EN"):
        directory = os.path.join(root, kind)
        rows = []
        if os.path.isdir(directory):
            for name in sorted(os.listdir(directory)):
                if name.lower().endswith(".mes"):
                    try:
                        row = parse_mes(os.path.join(directory, name))
                        row["file"] = name
                        rows.append(row)
                    except ValueError as exc:
                        rows.append({"file": name, "error": str(exc)})
        report["mes"][kind] = {"files": len(rows), "versions": dict(collections.Counter(r.get("version") for r in rows if "version" in r)), "samples": rows[:5]}
    raw_rows = load_json_dir(os.path.join(root, "JSON_RAW"))
    en_rows = load_json_dir(os.path.join(root, "JSON_EN"))
    report["json"]["JSON_RAW"] = {"files": len(set(r["file"] for r in raw_rows)), "entries": len(raw_rows), "speaker_markers": sum(r.get("name") == "$n" for r in raw_rows)}
    report["json"]["JSON_EN"] = {"files": len(set(r["file"] for r in en_rows)), "entries": len(en_rows), "speaker_markers": sum(r.get("name") == "$n" for r in en_rows)}
    report["json"]["same_basename_files"] = len(set(r["file"] for r in raw_rows) & set(r["file"] for r in en_rows))
    if dc1_json:
        dc1_rows = load_dc1(dc1_json)
        raw_index = collections.defaultdict(list)
        for row in raw_rows:
            raw_index[normalized(row["message"])].append(row)
        matched = 0
        placeholder_messages = []
        examples = []
        for row in dc1_rows:
            if "[name]" in row["message"]:
                placeholder_messages.append({"file": row["file"], "index": row["index"], "message": row["message"]})
            hits = raw_index.get(normalized(row["message"]), [])
            if hits:
                matched += 1
                if len(examples) < 30:
                    examples.append({"dc1": row, "plus_communication": hits[0]})
        report["mapping"] = {"dc1_entries": len(dc1_rows), "json_raw_entries": len(raw_rows), "exact_normalized_message_matches": matched, "match_ratio": matched / len(dc1_rows) if dc1_rows else 0, "dc1_custom_name_messages": len(placeholder_messages), "examples": examples, "placeholder_samples": placeholder_messages[:30]}
    return report


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inventory"])
    parser.add_argument("source")
    parser.add_argument("--dc1-json")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        report = inventory(args.source, args.dc1_json)
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                f.write(text + "\n")
            print("wrote", args.out)
        else:
            print(text)
    except (OSError, ValueError, struct.error) as exc:
        print("error:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
