#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dc1_translate_tool.py — Translation workflow utility for D.C.P.S. (PSP).

Features:
  1. init-lang: Initialize a new translation folder (e.g. 'id') from English.
  2. export-sheets: Export scenes into human-readable editable JSON files per scene.
     Includes Japanese original, English reference (FanTL + MangaGamer), and editable text.
  3. import-sheets: Recompile edited scene sheets back into transfer_<lang>.json with
     automatic English fallback for unedited/missing lines, Shift-JIS sanitization, and auto-wrapping.

Usage:
    python tools/dc1_translate_tool.py init-lang id
    python tools/dc1_translate_tool.py export-sheets id
    python tools/dc1_translate_tool.py import-sheets id
"""

import argparse
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATIONS_DIR = os.path.join(BASE_DIR, "translations")
ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis")

REPL = {
    "\uff5e": "~",
    "\u2015": "-",
    "\u2014": "-",
    "\u2013": "-",
    "\u2026": "...",
    "\u3000": " ",
    "\u201c": '"',
    "\u201d": '"',
    "\u2018": "'",
    "\u2019": "'",
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


def wrap(text, limit=60):
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


def clean_message(text, limit=60):
    t = normalize(text)
    t = " ".join(t.split())
    return wrap(t, limit)


def init_lang(target_lang: str):
    src_en = os.path.join(TRANSLATIONS_DIR, "en", "transfer_en.json")
    dst_dir = os.path.join(TRANSLATIONS_DIR, target_lang)
    dst_file = os.path.join(dst_dir, f"transfer_{target_lang}.json")

    if not os.path.exists(src_en):
        print(f"ERROR: Source English transfer not found at: {src_en}")
        sys.exit(1)

    os.makedirs(dst_dir, exist_ok=True)
    with open(src_en, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["source"] = f"D.C.P.S. {target_lang.upper()} Translation (Indonesian Priority + English Fallback)"
    with open(dst_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"Created/Updated: {dst_file}")

    sheets_dir = os.path.join(dst_dir, "sheets")
    os.makedirs(sheets_dir, exist_ok=True)
    print(f"Translation workspace ready for '{target_lang}' at: {dst_dir}")


def export_sheets(target_lang: str):
    src_en_path = os.path.join(TRANSLATIONS_DIR, "en", "transfer_en.json")
    trans_file = os.path.join(TRANSLATIONS_DIR, target_lang, f"transfer_{target_lang}.json")
    
    if not os.path.exists(src_en_path):
        print(f"ERROR: Source English transfer not found at: {src_en_path}")
        sys.exit(1)

    with open(src_en_path, "r", encoding="utf-8") as f:
        en_transfer = json.load(f)

    existing_id = {}
    if os.path.exists(trans_file):
        try:
            with open(trans_file, "r", encoding="utf-8") as f:
                existing_id = json.load(f).get("files", {})
        except Exception:
            existing_id = {}

    psp_script_path = os.path.join(ANALYSIS_DIR, "dc1_script.json")
    psp_index_path = os.path.join(ANALYSIS_DIR, "dc1_script.index.json")

    with open(psp_script_path, "r", encoding="utf-8") as f:
        psp_script = json.load(f)
    with open(psp_index_path, "r", encoding="utf-8") as f:
        psp_index = json.load(f)

    psp_lines = {f["file"]: f["lines"] for f in psp_script["files"]}
    idx_lines = {f["file"]: f["lines"] for f in psp_index["files"]}

    sheets_dir = os.path.join(TRANSLATIONS_DIR, target_lang, "sheets")
    os.makedirs(sheets_dir, exist_ok=True)

    en_files = en_transfer.get("files", {})
    exported_count = 0

    for blob_name, en_entry in sorted(en_files.items()):
        pl = psp_lines.get(blob_name, [])
        il = idx_lines.get(blob_name, [])
        
        en_msgs = en_entry.get("messages", {})
        en_choices = en_entry.get("choices", {})
        en_names = en_entry.get("names", {})
        
        id_entry = existing_id.get(blob_name, {})
        id_msgs = id_entry.get("messages", {})
        id_choices = id_entry.get("choices", {})
        id_names = id_entry.get("names", {})

        sheet = {
            "scene": blob_name,
            "dialogues": [],
            "choices": [],
            "names": id_names or en_names,
        }

        for i, idx_line in enumerate(il):
            mo = str(idx_line.get("message_offset"))
            no = str(idx_line.get("name_offset")) if idx_line.get("name_offset") is not None else None
            typ = idx_line.get("type")
            jp_item = pl[i] if i < len(pl) else {}

            if typ in ("choice", "navigation") and mo in en_choices:
                en_c = en_choices[mo]
                id_c = id_choices.get(mo, en_c)
                sheet["choices"].append({
                    "offset": int(mo),
                    "jp": jp_item.get("message", ""),
                    "en": en_c,
                    "text": id_c,
                })
            elif mo in en_msgs:
                en_m = en_msgs[mo]
                id_m = id_msgs.get(mo, en_m)
                speaker_en = (id_names or en_names).get(no, "") if no else ""
                sheet["dialogues"].append({
                    "offset": int(mo),
                    "speaker": speaker_en or jp_item.get("name", ""),
                    "speaker_jp": jp_item.get("name", ""),
                    "jp": jp_item.get("message", ""),
                    "en": en_m,
                    "text": id_m,
                })

        sheet_path = os.path.join(sheets_dir, blob_name.replace(".obj", ".json"))
        with open(sheet_path, "w", encoding="utf-8") as f:
            json.dump(sheet, f, ensure_ascii=False, indent=2)
        exported_count += 1

    print(f"Exported {exported_count} bilingual scene sheets to: {sheets_dir}")


def import_sheets(target_lang: str):
    src_en_path = os.path.join(TRANSLATIONS_DIR, "en", "transfer_en.json")
    sheets_dir = os.path.join(TRANSLATIONS_DIR, target_lang, "sheets")
    dst_file = os.path.join(TRANSLATIONS_DIR, target_lang, f"transfer_{target_lang}.json")

    if not os.path.exists(src_en_path):
        print(f"ERROR: Source English transfer not found at: {src_en_path}")
        sys.exit(1)

    with open(src_en_path, "r", encoding="utf-8") as f:
        en_transfer = json.load(f)

    # Start from English master as base so unedited scenes never break or revert to raw JP
    out_files = dict(en_transfer.get("files", {}))
    total_custom_id_lines = 0
    processed_sheets = 0

    if os.path.exists(sheets_dir):
        for fn in sorted(os.listdir(sheets_dir)):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(sheets_dir, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    sheet = json.load(f)
            except Exception:
                continue

            blob_name = sheet.get("scene", fn.replace(".json", ".obj"))
            en_base = out_files.get(blob_name, {})
            
            messages = dict(en_base.get("messages", {}))
            choices = dict(en_base.get("choices", {}))
            names = dict(sheet.get("names", en_base.get("names", {})))

            for d in sheet.get("dialogues", []):
                mo = str(d["offset"])
                txt = d.get("text") or d.get("en", "")
                if txt:
                    cleaned = clean_message(txt, limit=60)
                    cleaned = cleaned.replace("$n", "[name]")
                    messages[mo] = cleaned
                    if txt != d.get("en"):
                        total_custom_id_lines += 1

            for c in sheet.get("choices", []):
                mo = str(c["offset"])
                txt = c.get("text") or c.get("en", "")
                if txt:
                    cleaned = clean_message(txt, limit=60)
                    if not cleaned.startswith("○") and not cleaned.startswith("◯"):
                        cleaned = "○" + cleaned
                    choices[mo] = cleaned
                    if txt != c.get("en"):
                        total_custom_id_lines += 1

            out_files[blob_name] = {
                "messages": messages,
                "choices": choices,
                "names": names,
            }
            processed_sheets += 1

    doc = {
        "game": "D.C.P.S. - Da Capo 1 Plus Situation Portable (PSP, NPJH50731)",
        "source": f"D.C.P.S. {target_lang.upper()} Translation (Custom {total_custom_id_lines} lines + EN Fallback)",
        "encoding": "shift_jis",
        "width": 60,
        "files": out_files,
    }

    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
    with open(dst_file, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"Recompiled {len(out_files)} total scenes ({processed_sheets} sheets imported, {total_custom_id_lines} custom {target_lang.upper()} lines) into: {dst_file}")


def main():
    parser = argparse.ArgumentParser(description="Translation sheets exporter and compiler for D.C.P.S.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init-lang", help="Initialize a new translation workspace")
    p_init.add_argument("lang", help="Target language code, e.g. 'id'")

    p_exp = subparsers.add_parser("export-sheets", help="Export scenes into editable per-scene JSON sheets")
    p_exp.add_argument("lang", help="Language code to export, e.g. 'id'")

    p_imp = subparsers.add_parser("import-sheets", help="Recompile edited per-scene JSON sheets into transfer JSON")
    p_imp.add_argument("lang", help="Language code to import, e.g. 'id'")

    args = parser.parse_args()

    if args.command == "init-lang":
        init_lang(args.lang)
    elif args.command == "export-sheets":
        export_sheets(args.lang)
    elif args.command == "import-sheets":
        import_sheets(args.lang)


if __name__ == "__main__":
    main()
