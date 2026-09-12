#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dc1_eboot_patch.py — Patch protagonist default name and system UI strings
in the decrypted EBOOT.BIN (ELF) of D.C.P.S. (NPJH50731 / ULJM05718).

Supports English (--lang en) and Indonesian (--lang id).

Usage:
    python tools/dc1_eboot_patch.py [input_elf] [output_elf] [--lang en|id]
"""

import sys
import os
import argparse

PATCHES_EN = {
    # 1. Protagonist Default Name
    0x099B70: ("純一", "Junichi"),
    0x099B78: ("朝倉", "Asakura"),
    0x09A2E0: ("純一", "Junichi"),
    0x097CB4: ("名前を『純一』に戻します。", "Reset name to Junichi."),

    # 2. Name Screen Prompts & Explanations
    0x097C40: ("文字の種類を選択してください。", "Select character type."),
    0x097C60: ("主人公の名前を決定します。", "Confirm protagonist name."),
    0x097C7C: ("漢字の頭文字を選んでください。", "Select initial kanji."),
    0x097C9C: ("文字を選んでください。", "Select character."),
    0x097CD0: ("一文字分空白をあけます。", "Insert a space."),
    0x097CEC: ("一文字消去します。", "Delete character."),
    0x097D00: ("入力する位置を左に移動します。", "Move cursor left."),
    0x097D20: ("入力する位置を右に移動します。", "Move cursor right."),
    0x099B80: (" 名前を変更して\nよろしいですか？", "Confirm this name?\nAre you sure?"),
    0x099BA4: ("名前を変更しないで\n\u3000終了しますか？", "Exit without changing\nyour name?"),

    # 3. System UI Buttons & Confirmations
    0x097124: ("はい", "Yes"),
    0x09712C: ("いいえ", "No"),
    0x097258: ("標準に戻しますか？", "Reset to default?"),
    0x09726C: ("設定を反映させますか？", "Apply settings?"),
    0x097284: ("設定を保存しますか？", "Save settings?"),

    # 4. System Configuration Screen Descriptions
    0x097318: ("音声のボリュームを設定します", "Adjust voice volume."),
    0x097338: ("音楽のボリュームを設定します", "Adjust music volume."),
    0x097358: ("効果音ボリュームを設定します", "Adjust SFX volume."),
    0x097378: ("ウィンドウの透明度を変更します", "Change window transparency."),
    0x097398: ("画面表示の速度を変更します", "Change display speed."),
    0x0973B4: ("あらすじモードをＯＦＦにします", "Turn synopsis mode OFF."),
    0x0973D4: ("あらすじモードをＯＮにします", "Turn synopsis mode ON."),
    0x0973F4: ("文字を表示する速度を変更します", "Change text display speed."),
    0x097414: ("画面効果をＯＦＦにします", "Turn screen effects OFF."),
    0x097430: ("画面効果をＯＮにします", "Turn screen effects ON."),
    0x097448: ("スキップの設定を変更します", "Change skip settings."),
    0x097464: ("本編中の操作設定を変更します", "Change control settings."),
    0x097484: ("システム音声の担当を変更します", "Change system voice character."),
    0x0974A4: ("全ての設定を初期設定にします", "Reset all settings to default."),
    0x0974C4: ("ボイスコンフィグ画面へ移ります", "Open voice settings screen."),
    0x0974E4: ("全てをＯＮにします", "Turn all ON."),
    0x0974F8: ("全てをＯＦＦにします", "Turn all OFF."),
    0x097510: ("システムコンフィグ画面に戻ります", "Return to system config."),
    0x097534: ("○ボタンでＯＮにします", "Press ○ to turn ON."),
    0x09754C: ("○ボタンでＯＦＦにします", "Press ○ to turn OFF."),

    # 5. CG / Scenario Gallery & Navigation
    0x0976A0: ("ＣＧを選んでください", "Select CG."),
    0x0976B8: ("キャラクターを選んでください", "Select character."),
    0x097710: ("見てないＣＧは選べません", "CG not yet unlocked."),
    0x09772C: ("次のページへ移動します", "Go to next page."),
    0x097744: ("前のページへ移動します", "Go to previous page."),
    0x097C20: ("：再生\u3000左右：モード切り替え", ":Play  Left/Right:Mode"),
    0x099D00: ("シナリオを選んでください", "Select scenario."),
    0x099D1C: ("キャラクターを選んでください", "Select character."),
    0x099D3C: ("？？？", "???"),
    0x099ED0: ("回想を終了しますか？", "End scene replay?"),
    0x099EE8: ("タイトルに戻ります", "Return to title."),
    0x099F2C: ("クイックセーブします", "Quick Save."),
    0x099F44: ("クイックロードします", "Quick Load."),

    # 6. Save Confirmation Prompts
    0x099D68: ("プレイデータは保存されません\n\u3000\u3000\u3000よろしいですか？", "Game data will not be saved.\nContinue?"),
    0x099D9C: ("クリアデータは保存されません\n\u3000\u3000\u3000よろしいですか？", "Clear data will not be saved.\nContinue?"),
    0x099DD0: ("プレイデータを保存しますか？", "Save game data?"),
    0x099DF0: ("クリアデータを保存しますか？", "Save clear data?"),
    0x099EFC: ("※ 保存していないデータは\n\u3000 失われてしまいます", "* Unsaved progress will be lost."),
}

PATCHES_ID = {
    # 1. Protagonist Default Name
    0x099B70: ("純一", "Junichi"),
    0x099B78: ("朝倉", "Asakura"),
    0x09A2E0: ("純一", "Junichi"),
    0x097CB4: ("名前を『純一』に戻します。", "Kembalikan ke Junichi."),

    # 2. Name Screen Prompts & Explanations
    0x097C40: ("文字の種類を選択してください。", "Pilih jenis huruf."),
    0x097C60: ("主人公の名前を決定します。", "Konfirmasi nama protagonis."),
    0x097C7C: ("漢字の頭文字を選んでください。", "Pilih huruf depan kanji."),
    0x097C9C: ("文字を選んでください。", "Pilih karakter huruf."),
    0x097CD0: ("一文字分空白をあけます。", "Beri satu spasi."),
    0x097CEC: ("一文字消去します。", "Hapus 1 karakter."),
    0x097D00: ("入力する位置を左に移動します。", "Geser posisi kursor ke kiri."),
    0x097D20: ("入力する位置を右に移動します。", "Geser kursor ke kanan."),
    0x099B80: (" 名前を変更して\nよろしいですか？", "Ubah nama ini?\nAnda yakin?"),
    0x099BA4: ("名前を変更しないで\n\u3000終了しますか？", "Keluar tanpa mengubah\nnama?"),

    # 3. System UI Buttons & Confirmations
    0x097124: ("はい", "Ya"),
    0x09712C: ("いいえ", "Tidak"),
    0x097258: ("標準に戻しますか？", "Kembalikan ke awal?"),
    0x09726C: ("設定を反映させますか？", "Terapkan setelan?"),
    0x097284: ("設定を保存しますか？", "Simpan setelan?"),

    # 4. System Configuration Screen Descriptions
    0x097318: ("音声のボリュームを設定します", "Atur volume suara/vokal."),
    0x097338: ("音楽のボリュームを設定します", "Atur volume musik BGM."),
    0x097358: ("効果音ボリュームを設定します", "Atur volume efek suara SFX."),
    0x097378: ("ウィンドウの透明度を変更します", "Ubah transparansi jendela."),
    0x097398: ("画面表示の速度を変更します", "Ubah kecepatan tampilan."),
    0x0973B4: ("あらすじモードをＯＦＦにします", "Matikan mode sinopsis (OFF)."),
    0x0973D4: ("あらすじモードをＯＮにします", "Nyalakan sinopsis (ON)."),
    0x0973F4: ("文字を表示する速度を変更します", "Ubah kecepatan teks."),
    0x097414: ("画面効果をＯＦＦにします", "Matikan efek layar (OFF)."),
    0x097430: ("画面効果をＯＮにします", "Efek layar aktif (ON)."),
    0x097448: ("スキップの設定を変更します", "Ubah setelan lewati (skip)."),
    0x097464: ("本編中の操作設定を変更します", "Ubah setelan kontrol game."),
    0x097484: ("システム音声の担当を変更します", "Ubah pengisi suara sistem."),
    0x0974A4: ("全ての設定を初期設定にします", "Reset semua setelan ke awal."),
    0x0974C4: ("ボイスコンフィグ画面へ移ります", "Buka menu setelan suara."),
    0x0974E4: ("全てをＯＮにします", "Semua aktif (ON)."),
    0x0974F8: ("全てをＯＦＦにします", "Semua nonaktif (OFF)."),
    0x097510: ("システムコンフィグ画面に戻ります", "Kembali ke menu konfigurasi."),
    0x097534: ("○ボタンでＯＮにします", "Tekan ○ utk aktifkan."),
    0x09754C: ("○ボタンでＯＦＦにします", "Tekan ○ utk matikan."),

    # 5. CG / Scenario Gallery & Navigation
    0x0976A0: ("ＣＧを選んでください", "Pilih gambar CG."),
    0x0976B8: ("キャラクターを選んでください", "Pilih karakter."),
    0x097710: ("見てないＣＧは選べません", "CG belum terbuka."),
    0x09772C: ("次のページへ移動します", "Ke halaman berikutnya."),
    0x097744: ("前のページへ移動します", "Ke halaman sebelumnya."),
    0x097C20: ("：再生\u3000左右：モード切り替え", ":Putar  Kiri/Kanan:Mode"),
    0x099D00: ("シナリオを選んでください", "Pilih skenario."),
    0x099D1C: ("キャラクターを選んでください", "Pilih karakter."),
    0x099D3C: ("？？？", "???"),
    0x099ED0: ("回想を終了しますか？", "Selesai putar adegan?"),
    0x099EE8: ("タイトルに戻ります", "Kembali ke judul."),
    0x099F2C: ("クイックセーブします", "Simpan Cepat."),
    0x099F44: ("クイックロードします", "Muat Cepat."),

    # 6. Save Confirmation Prompts
    0x099D68: ("プレイデータは保存されません\n\u3000\u3000\u3000よろしいですか？", "Data permainan tak disimpan.\nLanjut?"),
    0x099D9C: ("クリアデータは保存されません\n\u3000\u3000\u3000よろしいですか？", "Data tamat tidak disimpan.\nLanjut?"),
    0x099DD0: ("プレイデータを保存しますか？", "Simpan data permainan?"),
    0x099DF0: ("クリアデータを保存しますか？", "Simpan data tamat?"),
    0x099EFC: ("※ 保存していないデータは\n\u3000 失われてしまいます", "* Data belum tersimpan akan\n  hilang."),
}


def patch_eboot(data: bytearray, patches: dict):
    errors = []
    applied = []

    for foff, (orig_txt, new_txt) in sorted(patches.items()):
        orig_sjis = orig_txt.encode("shift_jis")
        new_sjis = new_txt.encode("shift_jis")

        end = data.find(b"\x00", foff)
        if end < 0:
            errors.append(f"0x{foff:06X}: no null terminator found")
            continue

        actual_orig = bytes(data[foff:end])
        slot_len = end - foff

        null_slack = 0
        p = end
        while p < len(data) and data[p] == 0:
            null_slack += 1
            p += 1

        total_slot = slot_len + null_slack

        if actual_orig != orig_sjis:
            try:
                dec = actual_orig.decode("shift_jis")
            except:
                dec = repr(actual_orig)
            errors.append(f"0x{foff:06X}: mismatch! Expected {repr(orig_txt)}, found {repr(dec)}")
            continue

        needed = len(new_sjis) + 1
        if needed > total_slot:
            errors.append(f"0x{foff:06X}: '{new_txt}' ({needed} B) does not fit in {total_slot} B slot")
            continue

        padding = b"\x00" * (total_slot - len(new_sjis))
        patched_bytes = new_sjis + padding
        data[foff : foff + total_slot] = patched_bytes
        applied.append((foff, orig_txt, new_txt, total_slot))

    return data, errors, applied


def main():
    parser = argparse.ArgumentParser(description="Patch protagonist default name and system UI strings in D.C.P.S. ELF.")
    parser.add_argument("src", help="Path to decrypted clean EBOOT.BIN / ELF")
    parser.add_argument("dst", help="Path to output patched ELF")
    parser.add_argument("--lang", choices=["en", "id"], default="en", help="Target language (en or id)")
    args = parser.parse_args()

    patches = PATCHES_ID if args.lang == "id" else PATCHES_EN

    with open(args.src, "rb") as f:
        data = bytearray(f.read())

    print(f"Reading input ELF: {args.src} ({len(data)} bytes) [Target language: {args.lang.upper()}]")
    if data[:4] != b"\x7fELF":
        print("ERROR: input file is not a valid ELF executable (magic != \\x7fELF)")
        sys.exit(1)

    out_data, errors, applied = patch_eboot(data, patches)

    if errors:
        print(f"\nFound {len(errors)} error(s):")
        for e in errors:
            print("  ERROR:", e.encode("ascii", "backslashreplace").decode())
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.dst)), exist_ok=True)
    with open(args.dst, "wb") as f:
        f.write(out_data)

    print(f"\nSuccessfully patched {len(applied)} strings into {args.dst}")
    for foff, orig, new, slot in applied:
        clean_orig = orig.encode("ascii", "backslashreplace").decode()
        clean_new = new.encode("ascii", "backslashreplace").decode()
        print(f"  0x{foff:06X} [{slot:2d}B]: {repr(clean_orig)} -> {repr(clean_new)}")


if __name__ == "__main__":
    main()
