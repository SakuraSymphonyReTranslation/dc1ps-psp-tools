import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with open('analysis/psp_titles.txt', 'r', encoding='utf-8') as f:
    psp_all = {}
    for line in f:
        p = line.strip().split('\t')
        if len(p) >= 3:
            psp_all[p[0]] = (p[1], int(p[2]))

with open('analysis/scene_pairs.json', 'r', encoding='utf-8') as f:
    ark_raw = json.load(f)
    ark_map = {v['psp']: k for k, v in ark_raw.items()}

with open('analysis/scene_pairs_mangagamer.json', 'r', encoding='utf-8') as f:
    mg_map = json.load(f)

# Heroine classification for all scenes in PSP
heroines = {
    'Nemu (朝倉 音夢)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Sakura (芳乃 さくら)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Kotori (白河 ことり)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Miharu (天枷 美春)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Moe (水越 萌)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Mako (水越 眞子)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Alice (月城 アリス)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Nanako (彩珠 ななこ)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Tamaki (胡ノ宮 環)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Izumiko (紫 和泉子)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Kanae (工藤 叶)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Yoriko (鷺澤 頼子)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'Kasumi (霧羽 香澄)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
    'etc (Common / Lain-lain)': {'psp_scenes': [], 'en_scenes': [], 'mg': 0, 'ark': 0},
}

for sc_id, (title, lines) in psp_all.items():
    pc_file = ark_map.get(sc_id) or mg_map.get(sc_id, '')
    base = pc_file.replace('.json', '')
    parts = base.split('_')
    c = parts[1][0] if len(parts) > 1 and parts[1] else ''

    h_name = None
    if c == 'n' or '音夢' in title: h_name = 'Nemu (朝倉 音夢)'
    elif c == 's' or 'さくら' in title: h_name = 'Sakura (芳乃 さくら)'
    elif c == 'k' or 'ことり' in title: h_name = 'Kotori (白河 ことり)'
    elif c == 'h' or '美春' in title: h_name = 'Miharu (天枷 美春)'
    elif c == 'm' or '萌' in title: h_name = 'Moe (水越 萌)'
    elif c == 'w' or '眞子' in title: h_name = 'Mako (水越 眞子)'
    elif c == 'a' or 'アリス' in title or '月城' in title: h_name = 'Alice (月城 アリス)'
    elif c == 'g' or 'ななこ' in title or '彩珠' in title: h_name = 'Nanako (彩珠 ななこ)'
    elif c == 't' or '環' in title or '胡ノ宮' in title: h_name = 'Tamaki (胡ノ宮 環)'
    elif c == 'i' or '和泉子' in title or '紫' in title: h_name = 'Izumiko (紫 和泉子)'
    elif c == 'd' or '叶' in title or '工藤' in title: h_name = 'Kanae (工藤 叶)'
    elif c == 'y' or '頼子' in title or '鷺澤' in title: h_name = 'Yoriko (鷺澤 頼子)'
    elif c == 'b' or '香澄' in title or '霧羽' in title: h_name = 'Kasumi (霧羽 香澄)'
    else: h_name = 'etc (Common / Lain-lain)'

    heroines[h_name]['psp_scenes'].append((sc_id, title, lines))
    if sc_id in ark_map:
        heroines[h_name]['en_scenes'].append(sc_id)
        heroines[h_name]['ark'] += 1
    elif sc_id in mg_map:
        heroines[h_name]['en_scenes'].append(sc_id)
        heroines[h_name]['mg'] += 1

print('=' * 95)
print('ANALISIS KELENGKAPAN RUTE HEROINE D.C.P.S. (PLUS SITUATION PORTABLE - NPJH50731)')
print('=' * 95)
print(f'{"Tab Heroine D.C.P.S.":25} | {"Total Scene All-Age":20} | {"Status Terjemah":16} | {"Status Rute"}')
print('-' * 95)

for h_name, d in heroines.items():
    total_psp = len(d['psp_scenes'])
    total_en = len(d['en_scenes'])
    pct = (total_en / total_psp * 100) if total_psp > 0 else 0
    status = ' [100% LENGKAP]' if total_en == total_psp else f' [Sisa {total_psp - total_en:2d} scene]'
    print(f'{h_name:25} | {total_psp:4d} scene            | {total_en:3d} ({pct:5.1f}%)     | {status}')

print('=' * 95)
total_all_psp = sum(len(d['psp_scenes']) for d in heroines.values())
total_all_en = sum(len(d['en_scenes']) for d in heroines.values())
print(f'TOTAL SELURUH SCENE ALL-AGE D.C.P.S. : {total_all_psp} scene')
print(f'TOTAL SCENE SIAP MAINKAN SAAT INI    : {total_all_en} scene ({total_all_en/total_all_psp*100:.1f}%)')
print(f'SCENE EKSKLUSIF KONSOL BELUM TERJEMAH: {total_all_psp - total_all_en} scene')
print('=' * 95)
