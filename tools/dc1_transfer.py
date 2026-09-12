#!/usr/bin/env python3
"""Build the EN->PSP transfer map from scene pairs + line alignment.

Inputs (analysis/):
  scene_pairs.json   EN file -> PSP blob (verified)
  line_align.json    per-scene line index pairs
  dc1_script.json    PSP public dump (message/name, in order)
  dc1_script.index.json  sidecar: type/name_offset/message_offset per line

Output (output/transfer.json):
  { "files": { "script_NNNN.obj": {
      "messages": {"<offset>": "text"},   # keyed by message_offset
      "names":    {"<offset>": "text"},   # keyed by name_offset
      "choices":  {"<offset>": "text"},   # choice/nav tokens
  } } }

Text handling: rejoin the PC's hard wraps, normalize unicode to SJIS-safe,
re-wrap at `--width` halfwidth units (default 60, matching the DC2 shrunk-font
textbox).
"""

import argparse
import collections
import json
import os
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
BASE = r"F:\Games\PSP\dc1ps-psp-tools\analysis"
OUT_DEFAULT = r"F:\Games\PSP\dc1ps-psp-tools\output\transfer.json"

REPL = {
    "\uff5e": "~",        # fullwidth tilde (not in strict shift_jis)
    "\u2015": "-",        # horizontal bar
    "\u2014": "-",        # em dash
    "\u2013": "-",        # en dash
    "\u2026": "...",      # ellipsis
    "\u3000": " ",        # ideographic space
}


def normalize(text):
    for k, v in REPL.items():
        text = text.replace(k, v)
    return text


def width(s):
    w = 0
    for ch in s:
        w += 1 if (0x20 <= ord(ch) <= 0x7E or ch == "\n") else 2
    return w


def wrap(text, limit):
    """Greedy word wrap on spaces; existing newlines are kept as hard breaks."""
    out_lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            if not line:
                line = w
            elif width(line) + 1 + width(w) <= limit:
                line += " " + w
            else:
                out_lines.append(line)
                line = w
        out_lines.append(line)
    return "\n".join(out_lines)


def clean_message(text, limit):
    text = normalize(text).replace("\r", "")
    text = text.replace("\n", " ")           # rejoin PC wrap
    text = " ".join(text.split())            # collapse whitespace
    text = text.strip()
    return wrap(text, limit)


FALLBACK_JP_TO_EN = {
    "ことり": "Kotori", "環": "Tamaki", "工藤": "Kudou", "杉並": "Suginami",
    "アリス": "Alice", "音夢": "Nemu", "暦": "Koyomi", "美春": "Miharu",
    "さくら": "Sakura", "瀬場": "Seiba", "ピロス": "Piros", "眞子": "Mako",
    "ななこ": "Nanako", "みっくん": "Mik-kun", "ともちゃん": "Tomo-chan",
    "和泉子": "Izumiko", "？？？": "???", "夢の少女": "Dream Girl", "萌": "Moe",
    "男子学生": "Male Student", "男子学生１": "Male Student 1", "男子学生２": "Male Student 2",
    "男子生徒": "Male Student", "女子生徒": "Female Student", "アナウンス": "Announcer",
    "ばあちゃん": "Grandma", "佳苗": "Kanae", "ゆき先生": "Yuki-sensei", "女の子": "Girl",
    "男の子": "Boy", "環の父": "Tamaki's Father", "朝倉＆杉並": "Asakura & Suginami",
    "朝倉＆工藤": "Asakura & Kudou", "ことり＆工藤": "Kotori & Kudou",
    "眞子＆美春": "Mako & Miharu", "声": "Voice", "謎の声": "Mysterious Voice",
    "教師": "Teacher", "学園長": "School Principal", "看護師": "Nurse", "老婦人": "Old Woman",
    "神主": "Priest", "配達員": "Deliveryman", "救急隊員": "First-Aid Man", "週番": "Weekly Duty",
    "店員": "Waitress", "子供": "Kid", "クラス中": "Class", "クラスメイト": "Classmate",
    "部員": "Club Member", "主将": "Captain", "うたまる": "Utamaru", "和宏": "Kazuhiro",
    "恋": "Ren", "正太郎": "Shoutarou", "啓一": "Seiji", "田端": "Tahata", "和久井": "Wakui",
}


def looks_like_choice(text):
    """Heuristic: PSP choice/nav tokens may only receive short label-ish text."""
    if not text or len(text) > 120:
        return False
    if "◆" in text:
        return False                     # a scene title, never a choice
    return True


def clean_name(text):
    text = normalize(text).strip()
    text = " ".join(text.split())
    if "&" in text:
        parts = [p.strip() for p in text.split("&")]
        return " & ".join(parts)
    return text


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--width", type=int, default=60)
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    pairs = json.load(open(os.path.join(BASE, "scene_pairs.json"), encoding="utf-8"))
    la = json.load(open(os.path.join(BASE, "line_align.json"), encoding="utf-8"))
    psp = json.load(open(os.path.join(BASE, "dc1_script.json"), encoding="utf-8"))
    idx = json.load(open(os.path.join(BASE, "dc1_script.index.json"), encoding="utf-8"))
    psp_lines = {f["file"]: f["lines"] for f in psp["files"]}
    idx_lines = {f["file"]: f["lines"] for f in idx["files"]}

    out_files = {}
    stats = collections.Counter()
    name_map_votes = collections.defaultdict(collections.Counter)
    skipped_name_marker = []

    for ef, v in pairs.items():
        blob = v["psp"]
        align = la[ef]
        en_rows = json.load(open(os.path.join(ROOT, "JSON_EN", ef), encoding="utf-8-sig"))
        plines = psp_lines[blob]
        ilines = idx_lines[blob]
        assert len(plines) == len(ilines), "index order mismatch in " + blob
        messages = {}
        names = {}
        choices = {}
        for ei, pi in align["line_pairs"]:
            en = en_rows[ei]
            jp = plines[pi]
            il = ilines[pi]
            mo = str(il.get("message_offset"))
            raw_en = en.get("message", "")
            if raw_en.startswith("@"):
                stats["filtered_control"] += 1
                continue  # fan-TL branch labels (@A: keidai etc.)
            msg = clean_message(raw_en, args.width)
            # the PC dump marks the runtime MC name as '$n' inline; the PSP
            # engine uses the '[name]' placeholder for the same thing.
            msg = msg.replace("$n", "[name]")
            if not msg:
                continue
            is_choiceish = il.get("type") in ("choice", "navigation")
            if is_choiceish:
                if not looks_like_choice(raw_en):
                    stats["filtered_bad_choice"] += 1
                    continue
                # preserve the original bullet on 46 01 choice options
                jp_msg = jp.get("message", "")
                if jp_msg[:1] in ("\u25cb", "\u3007") and msg[:1] not in ("\u25cb", "\u3007"):
                    msg = jp_msg[0] + msg
            if is_choiceish:
                choices[mo] = msg
            else:
                messages[mo] = msg
            stats["lines"] += 1
            # name translation
            no = il.get("name_offset")
            en_name = en.get("name")
            jp_name = jp.get("name")
            if no is not None and jp_name:
                final_name = None
                if en_name and en_name != "$n":
                    final_name = clean_name(en_name)
                    name_map_votes[jp_name][final_name] += 1
                elif jp_name in FALLBACK_JP_TO_EN:
                    final_name = FALLBACK_JP_TO_EN[jp_name]
                if final_name:
                    names[str(no)] = final_name
        entry = {}
        if messages:
            entry["messages"] = messages
        if choices:
            entry["choices"] = choices
        if names:
            entry["names"] = names
        if entry:
            out_files[blob] = entry

    # a name token should never be '$n' on PSP (MC has no tag); drop any
    for blob, entry in out_files.items():
        for k in list(entry.get("names", {})):
            if entry["names"][k] == "$n":
                del entry["names"][k]

    doc = {
        "game": "D.C.P.S. - Da Capo 1 Plus Situation Portable (PSP, NPJH50731)",
        "source": "D.C. Plus Communication fan EN (Kotori/Alice/Kanae/Tamaki routes)",
        "encoding": "shift_jis",
        "width": args.width,
        "files": out_files,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("wrote %s: %d files, %d line replacements" % (args.out, len(out_files), stats["lines"]))
    if stats["filtered_control"]:
        print("filtered control entries: %d" % stats["filtered_control"])
    if stats["filtered_bad_choice"]:
        print("filtered implausible choice matches: %d" % stats["filtered_bad_choice"])

    # global name map for reference
    name_map = {k: v.most_common(1)[0][0] for k, v in name_map_votes.items() if len(v) == 1}
    mixed = {k: dict(v) for k, v in name_map_votes.items() if len(v) > 1}
    with open(os.path.join(BASE, "name_map.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(name_map, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("name map: %d consistent, %d mixed" % (len(name_map), len(mixed)))
    if mixed:
        print("MIXED:", json.dumps(mixed, ensure_ascii=False)[:500])
    if skipped_name_marker:
        print("skipped [name] lines: %d (kept JP)" % len(skipped_name_marker))
        for row in skipped_name_marker[:5]:
            print("   ", row)


if __name__ == "__main__":
    main()
