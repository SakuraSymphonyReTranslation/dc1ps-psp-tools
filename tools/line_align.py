#!/usr/bin/env python3
"""Line-level EN<->PSP alignment + orphan-home finder.

align:   for each scene pair, Needleman-Wunsch over lines using speaker
         identity + length-class, producing per-line EN->PSP index pairs and a
         confidence score. Bad scene pairs (low confidence) get dropped.
find:    for EN files with no (or bad) PSP pair, search ALL unpaired PSP blobs
         and report the best line-level candidate.
"""

import difflib
import glob
import json
import os
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
BASE = r"F:\Games\PSP\dc1ps-psp-tools\analysis"

EN_TO_JP = {
    "Kotori": "ことり", "Kootri": "ことり", "Kotroi": "ことり", "kOTORI": "ことり",
    "Tamaki": "環", "Tamai": "環", "Tmaki": "環", "Tsamaki": "環",
    "Kudou": "工藤", "Kkudou": "工藤",
    "Suginami": "杉並", "Sugiami": "杉並", "Sugianmi": "杉並", "Sugnami": "杉並", "Suignami": "杉並", "SUginami": "杉並", "?Suginami": "杉並",
    "Alice": "アリス", "alice": "アリス",
    "Nemu": "音夢",
    "Koyomi": "暦",
    "Miharu": "美春", "Mihaaru": "美春",
    "Sakura": "さくら", "sakura": "さくら",
    "Seiba": "瀬場", "seiba": "瀬場",
    "Piros": "ピロス",
    "Mako": "眞子", "Mako0": "眞子",
    "Nanako": "ななこ",
    "Mik-kun": "みっくん",
    "Tomo-chan": "ともちゃん", "TOmo-chan": "ともちゃん",
    "Izumiko": "和泉子", "Iuzmiko": "和泉子", 'Izumiko"': "和泉子",
    "???": "？？？",
    "Dream Girl": "夢の少女",
    "Moe": "萌",
    "Male Student": "男子学生", "Male Student 1": "男子学生１", "Male Student 2": "男子学生２", "Male Student 3": "男子学生３", "Male Student?": "男子生徒",
    "Female Student": "女子生徒", "Female Student 1": "女子生徒１", "Female Student 2": "女子生徒２", "Female Student 3": "女子生徒３",
    "Announcer": "アナウンス", "Anouncer": "アナウンス", "Newcaster": "アナウンス", "Newscaster": "アナウンス",
    "Grandma": "ばあちゃん",
    "Kanae": "佳苗",
    "Yuki-sensei": "ゆき先生",
    "Girl": "女の子", "Girl A": "女子Ａ", "Girl B": "女子Ｂ",
    "Boy": "男の子", "Boy 1": "少年１", "Boy 2": "少年２", "Boy 3": "少年３", "Boy 6": "少年６", "Boys": "少年達",
    "Tamaki's Father": "環の父",
    "Asakura & Suginami": "朝倉＆杉並", "Asakura&Suginami": "朝倉＆杉並",
    "Asakura&Kudou": "朝倉＆工藤",
    "Kotori & Kudou": "ことり＆工藤", "Kotori&Kudou": "ことり＆工藤",
    "Mako & Miharu": "眞子＆美春",
    "Voice": "声", "Mysterious Voice": "謎の声",
    "Teacher": "教師",
    "School Principal": "学園長",
    "Nurse": "看護師",
    "Old Woman": "老婦人",
    "Priest": "神主",
    "Deliveryman": "配達員", "Postman": "配達員",
    "First-Aid Man": "救急隊員",
    "Weekly Duty": "週番",
    "Waitress": "店員",
    "Kid": "子供",
    "Class": "クラス中", "Classmate": "クラスメイト",
    "Club Member": "部員", "Club Member 1": "部員１", "Club Member 2": "部員２", "Club Member 3": "部員３",
    "Captain": "主将",
    "Utamaru": "うたまる",
    "Kazuhiro": "和宏",
    "Ren": "恋",
    "Shoutarou": "正太郎",
    "Seiji": "啓一",
    "Tahata": "田端",
    "Wakui": "和久井",
    "Male": "男子", "Male A": "男子Ａ", "Male B": "男子Ｂ",
    "Guy": "男", "Guy A": "男子Ａ", "Guy B": "男子Ｂ", "Guy C": "男子Ｃ",
    "Man": "男性",
    "Bear?": "クマ",
}


def en_speaker(row):
    n = row.get("name")
    if not n or n == "$n":
        return ""
    clean = " ".join(n.split())
    if clean in EN_TO_JP:
        return EN_TO_JP[clean]
    if "&" in clean:
        parts = [p.strip() for p in clean.split("&")]
        jp_parts = [EN_TO_JP.get(p, p) for p in parts]
        return "＆".join(jp_parts)
    return EN_TO_JP.get(clean, "X:" + clean)


def jp_speaker(row):
    n = row.get("name")
    if not n:
        return ""
    return n.strip()


def align_lines(en_rows, psp_rows):
    """NW alignment over lines. Returns (pairs, matched, score)."""
    n, m = len(en_rows), len(psp_rows)
    if n == 0 or m == 0:
        return [], 0, 0.0

    # If the scene lengths are identical, they are 1:1 in lockstep
    if n == m:
        pairs = [(i, i) for i in range(n)]
        return pairs, n, 1.0

    A = [en_speaker(r) for r in en_rows]
    B = [jp_speaker(r) for r in psp_rows]
    GAP = -1.0
    MM = -1.5
    MATCH = 2.0
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + GAP
        bt[i][0] = 1
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + GAP
        bt[0][j] = 2
    for i in range(1, n + 1):
        ai = A[i - 1]
        for j in range(1, m + 1):
            d = dp[i - 1][j - 1] + (MATCH if ai == B[j - 1] and ai != "" else
                                    (1.2 if ai == B[j - 1] else MM))
            u = dp[i - 1][j] + GAP
            l = dp[i][j - 1] + GAP
            if d >= u and d >= l:
                dp[i][j] = d
                bt[i][j] = 0
            elif u >= l:
                dp[i][j] = u
                bt[i][j] = 1
            else:
                dp[i][j] = l
                bt[i][j] = 2
    pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        if bt[i][j] == 0:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif bt[i][j] == 1:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    matched = len(pairs)
    score = matched / n if n else 0.0
    return pairs, matched, score



def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    mode = sys.argv[1] if len(sys.argv) > 1 else "align"

    psp = json.load(open(os.path.join(BASE, "dc1_script.json"), encoding="utf-8"))
    psp_lines = {f["file"]: f["lines"] for f in psp["files"]}
    pairs = json.load(open(os.path.join(BASE, "scene_pairs.json"), encoding="utf-8"))

    if mode == "align":
        out = {}
        low = []
        for ef, v in sorted(pairs.items()):
            en_rows = json.load(open(os.path.join(ROOT, "JSON_EN", ef), encoding="utf-8-sig"))
            psp_rows = psp_lines[v["psp"]]
            line_pairs, matched, score = align_lines(en_rows, psp_rows)
            out[ef] = {"psp": v["psp"], "line_pairs": line_pairs, "matched": matched,
                       "en_n": len(en_rows), "psp_n": len(psp_rows), "score": round(score, 3)}
            if score < 0.55:
                low.append((ef, v["psp"], round(score, 3), len(en_rows), len(psp_rows)))
        with open(os.path.join(BASE, "line_align.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        print("aligned %d scenes; low-confidence (<0.55): %d" % (len(out), len(low)))
        for row in sorted(low, key=lambda x: x[2]):
            print("   %-20s %-16s score=%.3f  en=%d psp=%d" % row)
        good = sum(1 for v in out.values() if v["score"] >= 0.55)
        total_lines = sum(v["matched"] for v in out.values())
        print("good scenes: %d, total matched lines: %d" % (good, total_lines))

    elif mode == "find":
        # orphans: low-confidence or unpaired EN files
        la = json.load(open(os.path.join(BASE, "line_align.json"), encoding="utf-8"))
        orphans = [ef for ef, v in la.items() if v["score"] < 0.55]
        used = {v["psp"] for v in pairs.values() if v.get("psp")}
        candidates = [f for f in psp_lines if f not in used]
        print("orphan EN files: %d   candidate PSP blobs: %d" % (len(orphans), len(candidates)))
        for ef in orphans:
            en_rows = json.load(open(os.path.join(ROOT, "JSON_EN", ef), encoding="utf-8-sig"))
            best = []
            for cf in candidates:
                _p, _m, s = align_lines(en_rows, psp_lines[cf])
                best.append((s, cf, _m))
            best.sort(reverse=True)
            top = best[:3]
            print("%-20s (n=%d):" % (ef, len(en_rows)))
            for s, cf, m in top:
                title = next((l["message"] for l in psp_lines[cf]
                              if l.get("message", "").startswith("◆")), "-")
                print("     %.3f  %s (matched %d/%d)  %s" % (s, cf, m, len(psp_lines[cf]), title[:30]))


if __name__ == "__main__":
    main()
