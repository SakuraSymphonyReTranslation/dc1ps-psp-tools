#!/usr/bin/env python3
"""Global scene alignment: JSON_EN files (342) -> DC1 PSP blobs (1046).

Signals:
  * speaker-pattern similarity (EN names canonicalized to JP via roster map;
    unknown names collapse to a generic X class; consecutive runs collapsed)
  * entry-count ratio plausibility
  * title presence (EN files essentially always carry a ◆…◆ title)
  * global monotonicity (both sequences follow the game's scene order)

Output: analysis/scene_pairs.json  {en_file: {psp: script_NNNN.obj, score, ...}}
"""

import difflib
import glob
import json
import math
import os
import sys

ROOT = r"E:\Games\Da Capo Plus Communication"
PSP_DUMP = r"F:\Games\PSP\dc1ps-psp-tools\analysis\dc1_script.json"
OUT = r"F:\Games\PSP\dc1ps-psp-tools\analysis\scene_pairs.json"

EN_TO_JP = {
    "Kotori": "ことり", "Tamaki": "環", "Kudou": "工藤", "Suginami": "杉並",
    "Alice": "アリス", "Nemu": "音夢", "Koyomi": "暦", "Miharu": "美春",
    "Sakura": "さくら", "Seiba": "瀬場", "Piros": "ピロス", "Mako": "眞子",
    "Nanako": "ななこ", "Mik-kun": "みっくん", "Tomo-chan": "ともちゃん",
    "Izumiko": "和泉子", "???": "？？？", "Dream Girl": "夢の少女", "Moe": "萌",
    "Male Student": "男子学生", "Announcer": "アナウンス", "Grandma": "ばあちゃん",
    "Kanae": "佳苗", "Yuki-sensei": "ゆき先生", "Girl": "女の子", "Boy": "男の子",
    "Tamaki's Father": "環の父",
}

GAP = -0.9


def canon_jp(name):
    if not name:
        return "N"
    if name == "$n":
        return "M"
    return name


def canon_en(name):
    if not name:
        return "N"
    if name == "$n":
        return "M"
    return EN_TO_JP.get(name, "X")


def collapse(seq):
    out = []
    for t in seq:
        if not out or out[-1] != t:
            out.append(t)
    return out


_score_cache = {}


def pair_score(en, psp):
    key = (en["file"], psp["file"])
    if key in _score_cache:
        return _score_cache[key]
    r = (en["n"] + 1.0) / (psp["n"] + 1.0)
    lr = abs(math.log(r))
    if lr > 0.55:
        s = -1.0
    elif en["title"] and not psp["title"]:
        s = -1.0
    else:
        sm = difflib.SequenceMatcher(None, en["cpat"], psp["cpat"], autojunk=False)
        s = sm.ratio() - min(0.5, lr)
        if en["title"] and psp["title"]:
            s += 0.15
    _score_cache[key] = s
    return s


def load_en():
    files = []
    for p in sorted(glob.glob(r"%s\JSON_EN\*.json" % ROOT)):
        try:
            d = json.load(open(p, encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, list) or not d:
            continue
        pat = [canon_en(r.get("name")) for r in d]
        title = next((r["message"] for r in d
                      if r.get("message", "").startswith("◆")), None)
        files.append({
            "file": os.path.basename(p),
            "n": len(d),
            "pat": pat,
            "cpat": collapse(pat),
            "title": title,
        })
    return files


def load_psp():
    d = json.load(open(PSP_DUMP, encoding="utf-8"))
    files = []
    for f in d["files"]:
        lines = f["lines"]
        pat = []
        title = None
        for ln in lines:
            pat.append(canon_jp(ln.get("name")))
            m = ln.get("message", "")
            if title is None and m.startswith("◆"):
                title = m
        files.append({
            "file": f["file"],
            "n": len(lines),
            "pat": pat,
            "cpat": collapse(pat),
            "title": title,
        })
    return files


def nw_align(A, B, score_fn, gap=GAP):
    """Monotonic global alignment. Returns list of (i, j) index pairs."""
    n, m = len(A), len(B)
    sm = [[score_fn(A[i], B[j]) for j in range(m)] for i in range(n)]
    NEG = float("-inf")
    dp = [[NEG] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]  # 0=diag 1=up 2=left
    dp[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            cur = dp[i][j]
            if cur == NEG:
                continue
            if i < n and j < m:
                v = cur + sm[i][j]
                if v > dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = v
                    bt[i + 1][j + 1] = 0
            if i < n:
                v = cur + gap
                if v > dp[i + 1][j]:
                    dp[i + 1][j] = v
                    bt[i + 1][j] = 1
            if j < m:
                v = cur + gap
                if v > dp[i][j + 1]:
                    dp[i][j + 1] = v
                    bt[i][j + 1] = 2
    pairs = []
    i, j = n, m
    while i > 0 or j > 0:
        d = bt[i][j]
        if i > 0 and j > 0 and d == 0:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and d == 1:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs, dp[n][m]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    en = load_en()
    psp = load_psp()
    print("EN files:", len(en), " PSP blobs:", len(psp))

    no_title = [e["file"] for e in en if not e["title"]]
    print("EN files without ◆ title:", len(no_title), no_title[:10])

    pairs, total = nw_align(en, psp, pair_score)
    out = {}
    weak = []
    for i, j in pairs:
        s = pair_score(en[i], psp[j])
        out[en[i]["file"]] = {
            "psp": psp[j]["file"], "score": round(s, 3),
            "en_n": en[i]["n"], "psp_n": psp[j]["n"],
            "en_title": en[i]["title"], "psp_title": psp[j]["title"],
        }
        if s < 0.35:
            weak.append((en[i]["file"], psp[j]["file"], round(s, 3),
                         en[i]["title"], psp[j]["title"]))
    print("aligned pairs:", len(out), " total score: %.1f" % total)
    print("weak pairs (score<0.35):", len(weak))
    for w in weak[:25]:
        print("   ", w)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("wrote", OUT)

    anchors = {
        "0223a_e01.json": "script_0001.obj",
        "0223a_f01.json": "script_0002.obj",
        "0223a_f02.json": "script_0003.obj",
        "0223a_f03.json": "script_0004.obj",
        "0223a_n01.json": "script_0005.obj",
        "0223a_t01.json": "script_0006.obj",
        "0223b_e01.json": "script_0007.obj",
        "0223b_f01.json": "script_0008.obj",
        "0223b_f03.json": "script_0010.obj",
        "0223c_f01.json": "script_0012.obj",
        "0223d_f01.json": "script_0013.obj",
        "0224a_a01.json": "script_0014.obj",
        "0224a_e01.json": "script_0015.obj",
        "0224a_f00.json": "script_0016.obj",
        "0224a_f01.json": "script_0017.obj",
        "0224a_f03.json": "script_0019.obj",
        "0224a_f04.json": "script_0020.obj",
    }
    print()
    print("=== anchor validation ===")
    ok = 0
    for ef, want in anchors.items():
        got = out.get(ef, {}).get("psp")
        mark = "OK " if got == want else "MISMATCH"
        if got == want:
            ok += 1
        else:
            print("%s %s -> %s (want %s)  %r / %r"
                  % (mark, ef, got, want,
                     out.get(ef, {}).get("psp_title"), out.get(ef, {}).get("en_title")))
    print("anchors OK: %d/%d" % (ok, len(anchors)))


if __name__ == "__main__":
    main()
