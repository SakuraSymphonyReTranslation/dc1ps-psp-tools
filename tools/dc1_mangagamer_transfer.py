#!/usr/bin/env python3
"""dc1_mangagamer_transfer.py: Extract MangaGamer English translations and merge
non-destructive into PSP transfer_en.json (FanTL remains strictly locked).
"""

import collections
import json
import os
import re
import sys

BASE = r"F:\Games\PSP\dc1ps-psp-tools\analysis"
MG_DIR = r"C:\Users\adamb\Downloads\v264_eng_DL\v264_eng_DC Da Capo\data01000_json"
FANTL_TRANSFER = r"F:\Games\PSP\dc1ps-psp-tools\translations\en\transfer_en.json"
OUT_TRANSFER = r"F:\Games\PSP\dc1ps-psp-tools\translations\en\transfer_en.json"
OUT_TRANSFER_BACKUP = r"F:\Games\PSP\dc1ps-psp-tools\translations\en\transfer_en_fantl_only_backup.json"

FALLBACK_JP_TO_EN = {
    "朝倉＆杉並": "Asakura & Suginami",
    "杉並＆美春": "Suginami & Miharu",
    "朝倉＆ことり": "Asakura & Kotori",
    "ことり＆美春": "Kotori & Miharu",
    "朝倉＆さくら": "Asakura & Sakura",
    "さくら＆ことり": "Sakura & Kotori",
    "純一＆音夢": "Junichi & Nemu",
    "音夢＆さくら": "Nemu & Sakura",
    "ことり＆音夢": "Kotori & Nemu",
    "音夢": "Nemu",
    "さくら": "Sakura",
    "ことり": "Kotori",
    "美春": "Miharu",
    "眞子": "Mako",
    "萌": "Moe",
    "頼子": "Yoriko",
    "美咲": "Misaki",
    "杉並": "Suginami",
    "環": "Tamaki",
    "アリス": "Alice",
    "工藤": "Kudou",
    "佳苗": "Kanae",
    "暦": "Koyomi",
    "白河": "Shirakawa",
    "朝倉": "Asakura",
    "水越": "Mizukoshi",
    "天枷": "Amakase",
    "鷺澤": "Sagisawa",
    "芳乃": "Yoshino",
    "沢井": "Sawai",
    "瀬場": "Seiba",
    "ピロス": "Piros",
    "ななこ": "Nanako",
    "みっくん": "Mik-kun",
    "ともちゃん": "Tomo-chan",
    "和泉子": "Izumiko",
    "？？？": "???",
    "夢の少女": "Dream Girl",
    "男子学生": "Male Student",
    "女子学生": "Female Student",
    "アナウンス": "Announcer",
    "ばあちゃん": "Grandma",
    "ゆき先生": "Yuki-sensei",
    "女の子": "Girl",
    "男の子": "Boy",
    "先生": "Teacher",
    "うたまる": "Utamaru",
}

EN_TO_JP = {
    "Junichi": "M", "$n": "M", "": "N", None: "N",
    "Kotori": "ことり", "Tamaki": "環", "Kudou": "工藤", "Suginami": "杉並",
    "Alice": "アリス", "Nemu": "音夢", "Koyomi": "暦", "Miharu": "美春",
    "Sakura": "さくら", "Seiba": "瀬場", "ピロス": "ピロス", "Mako": "眞子",
    "Nanako": "ななこ", "Mik-kun": "みっくん", "Tomo-chan": "ともちゃん",
    "Izumiko": "和泉子", "???": "？？？", "Moe": "萌",
    "Yoriko": "頼子", "Misaki": "美咲", "Kanako": "かなこ", "Tomoe": "ともえ",
    "Male Student": "男子学生", "Female Student": "女子学生", "Teacher": "先生",
    "Announcer": "アナウンス", "Grandma": "ばあちゃん", "Kanae": "佳苗",
}

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


def canon_en(name):
    if not name or name in ("Junichi", "$n"):
        return "M"
    return EN_TO_JP.get(name, "X")


def canon_jp(name):
    if not name or name == "$n":
        return "M"
    return name


def align_dialogue(mg_diag, psp_diag):
    n = len(mg_diag)
    m = len(psp_diag)
    if n == m:
        return [(i, i) for i in range(n)]
    
    GAP = -0.5
    dp = [[float("-inf")] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            cur = dp[i][j]
            if i > 0 and dp[i-1][j] + GAP > cur:
                cur = dp[i-1][j] + GAP
                bt[i][j] = 1
            if j > 0 and dp[i][j-1] + GAP > cur:
                cur = dp[i][j-1] + GAP
                bt[i][j] = 2
            if i > 0 and j > 0:
                mg_spk = canon_en(mg_diag[i-1][0])
                psp_spk = canon_jp(psp_diag[j-1].get("name"))
                if mg_spk == psp_spk:
                    s = 1.0
                elif mg_spk == "M" and not psp_diag[j-1].get("name"):
                    s = 0.8
                elif not mg_diag[i-1][0] and not psp_diag[j-1].get("name"):
                    s = 0.8
                else:
                    s = -0.2
                if dp[i-1][j-1] + s > cur:
                    cur = dp[i-1][j-1] + s
                    bt[i][j] = 0
            dp[i][j] = cur
            
    i, j = n, m
    pairs = []
    while i > 0 or j > 0:
        step = bt[i][j]
        if step == 0:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif step == 1:
            i -= 1
        elif step == 2:
            j -= 1
    pairs.reverse()
    return pairs


def extract_mg_scene(m_data, psp_lines):
    raw_title = m_data[0].get("name") or m_data[0].get("message") or ""
    clean_title = re.sub(r'["\s@]+$', '', raw_title)
    clean_title = re.sub(r'^["\s@]+', '', clean_title).strip()
    
    t_indices = [i for i, ln in enumerate(psp_lines) if ln.get("message", "").startswith("◆")]
    t_idx = t_indices[0] if t_indices else len(psp_lines)
    p_syn_cnt = len(psp_lines) - 1 - t_idx if t_indices else 0
    
    mg_has_prompt = len(m_data) > 3 and "story line?" in m_data[1].get("name", "")
    if mg_has_prompt:
        syn_start = 4
        syn_end = syn_start + p_syn_cnt
        diag_start = syn_end
    else:
        syn_start = 1
        syn_end = 1 + p_syn_cnt
        diag_start = syn_end
        
    syn_lines = []
    for item in m_data[syn_start:syn_end]:
        txt = item.get("message") or item.get("name") or ""
        syn_lines.append(txt)
        
    diag_lines = []
    for item in m_data[diag_start:]:
        spk = item.get("name") if "message" in item else None
        txt = item.get("message") or item.get("name") or ""
        diag_lines.append((spk, txt))
        
    return clean_title, syn_lines, diag_lines, t_idx


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        
    print("Loading databases and indices...")
    pairs = json.load(open(os.path.join(BASE, "scene_pairs_mangagamer.json"), encoding="utf-8"))
    psp = json.load(open(os.path.join(BASE, "dc1_script.json"), encoding="utf-8"))
    idx = json.load(open(os.path.join(BASE, "dc1_script.index.json"), encoding="utf-8"))
    
    psp_lines = {f["file"]: f["lines"] for f in psp["files"]}
    idx_lines = {f["file"]: f["lines"] for f in idx["files"]}
    
    # Load FanTL transfer map to lock existing FanTL translations
    print(f"Loading FanTL translations from {FANTL_TRANSFER}...")
    fantl_data = json.load(open(FANTL_TRANSFER, encoding="utf-8"))
    fantl_files = set(fantl_data["files"].keys())
    print(f"FanTL translations contains {len(fantl_files)} files (LOCKED, WILL NOT BE TOUCHED).")
    
    # Backup FanTL transfer file if backup doesn't exist
    if not os.path.exists(OUT_TRANSFER_BACKUP):
        with open(OUT_TRANSFER_BACKUP, "w", encoding="utf-8") as bf:
            json.dump(fantl_data, bf, ensure_ascii=False, indent=1)
        print(f"Created FanTL backup at {OUT_TRANSFER_BACKUP}")
        
    mg_transfer = {}
    total_mg_lines = 0
    
    for blob, mg_name in pairs.items():
        # STRICT CONSTRAINT: If file already translated in FanTL, SKIP!
        if blob in fantl_files:
            continue
            
        mg_path = os.path.join(MG_DIR, mg_name)
        if not os.path.exists(mg_path):
            continue
            
        m_data = json.load(open(mg_path, encoding="utf-8"))
        plines = psp_lines[blob]
        ilines = idx_lines[blob]
        
        clean_title, syn_lines, diag_lines, t_idx = extract_mg_scene(m_data, plines)
        
        p_diag = plines[:t_idx]
        aligned_pairs = align_dialogue(diag_lines, p_diag)
        
        messages = {}
        choices = {}
        names = {}
        
        # 1. Transfer in-game dialogue
        for mi, pi in aligned_pairs:
            mg_spk, mg_txt = diag_lines[mi]
            jp = plines[pi]
            il = ilines[pi]
            mo = str(il.get("message_offset"))
            
            msg = clean_message(mg_txt)
            msg = msg.replace("$n", "[name]")
            
            # Detect Indonesian words if any slipped in and filter out
            lower_words = set(msg.lower().split())
            if lower_words.intersection({"yang", "tidak", "dengan", "adalah"}):
                continue
                
            is_choice = il.get("type") in ("choice", "navigation")
            if is_choice:
                jp_msg = jp.get("message", "")
                if jp_msg[:1] in ("○", "〇") and msg[:1] not in ("○", "〇"):
                    msg = jp_msg[0] + msg
                choices[mo] = msg
            else:
                messages[mo] = msg
            total_mg_lines += 1
            
            # Speaker name
            no = il.get("name_offset")
            jp_name = jp.get("name")
            if no is not None and jp_name:
                final_name = None
                if mg_spk and mg_spk not in ("Junichi", "$n"):
                    final_name = clean_message(mg_spk)
                elif jp_name in FALLBACK_JP_TO_EN:
                    final_name = FALLBACK_JP_TO_EN[jp_name]
                if final_name:
                    names[str(no)] = final_name
                    
        # 2. Transfer Chapter Title
        if t_idx < len(plines) and clean_title:
            il = ilines[t_idx]
            mo = str(il.get("message_offset"))
            title_str = f"◆{clean_title}◆"
            messages[mo] = title_str
            total_mg_lines += 1
            
        # 3. Transfer Synopsis lines
        for s_i, syn_txt in enumerate(syn_lines):
            pi = t_idx + 1 + s_i
            if pi < len(plines):
                il = ilines[pi]
                mo = str(il.get("message_offset"))
                messages[mo] = clean_message(syn_txt)
                total_mg_lines += 1
                
        entry = {}
        if messages:
            entry["messages"] = messages
        if choices:
            entry["choices"] = choices
        if names:
            entry["names"] = names
            
        if entry:
            mg_transfer[blob] = entry

    print(f"Extracted MangaGamer translations for {len(mg_transfer)} previously RAW scenes ({total_mg_lines} lines).")
    
    # Non-destructive Merge into FanTL
    merged_files = dict(fantl_data["files"])
    added_count = 0
    for blob, entry in mg_transfer.items():
        if blob not in merged_files:
            merged_files[blob] = entry
            added_count += 1
            
    fantl_data["files"] = merged_files
    fantl_data["source"] = "FanTL (Kotori/Alice/Kanae/Tamaki) + MangaGamer Official (Nemu/Sakura/Miharu/Mako/Moe/Misaki/Yoriko)"
    
    with open(OUT_TRANSFER, "w", encoding="utf-8") as out_f:
        json.dump(fantl_data, out_f, ensure_ascii=False, indent=1)
        
    out_dir_path = r"F:\Games\PSP\dc1ps-psp-tools\output\transfer.json"
    with open(out_dir_path, "w", encoding="utf-8") as out_f:
        json.dump(fantl_data, out_f, ensure_ascii=False, indent=1)
        
    print(f"Successfully merged! Total files in transfer map: {len(merged_files)} (added {added_count} MangaGamer files).")
    print(f"Saved to {OUT_TRANSFER} and {out_dir_path}")


if __name__ == "__main__":
    main()
