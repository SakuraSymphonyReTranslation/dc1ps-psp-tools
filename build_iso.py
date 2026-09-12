#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_iso.py — One-click automated ISO builder for D.C.P.S. (PSP).

Supports building English (--lang en) or Indonesian (--lang id) ISOs.
Reproducible even if the output/ directory is completely cleared.

Usage:
    python build_iso.py [--lang en|id] [--base PATH] [--out PATH]
"""

import argparse
import hashlib
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
WORK_DIR = os.path.join(BASE_DIR, "work")
EXTRACTED_DIR = os.path.join(WORK_DIR, "extracted")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TRANSLATIONS_DIR = os.path.join(BASE_DIR, "translations")

DEFAULT_BASE_ISO = r"F:\Games\PSP\pkg2zip_32bit\D.C.P.S. [NPJH50731].iso"


def md5_file(filepath: str) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024 * 8):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="One-click ISO builder for D.C.P.S. PSP English/Indonesian translation.")
    parser.add_argument("--lang", choices=["en", "id"], default="en", help="Target language (default: en)")
    parser.add_argument("--base", default=DEFAULT_BASE_ISO, help="Path to original base ISO")
    parser.add_argument("--out", default=None, help="Custom output ISO path")
    args = parser.parse_args()

    lang = args.lang
    base_iso = os.path.abspath(args.base)
    out_iso = os.path.abspath(args.out) if args.out else os.path.join(OUTPUT_DIR, f"D.C.P.S. [NPJH50731]_{lang}.iso")

    clean_elf = os.path.join(EXTRACTED_DIR, "EBOOT_CLEAN.ELF")
    clean_script = os.path.join(EXTRACTED_DIR, "script.bin")
    font_file = os.path.join(EXTRACTED_DIR, "font_small.pgf")
    translation_json = os.path.join(TRANSLATIONS_DIR, lang, f"transfer_{lang}.json")

    target_elf = os.path.join(WORK_DIR, f"eboot_{lang}.elf")
    target_script = os.path.join(WORK_DIR, f"script_{lang}.bin")

    print("=" * 70)
    print(f" D.C.P.S. PSP BUILD PIPELINE [{lang.upper()}]")
    print("=" * 70)

    # 1. Validation
    if not os.path.exists(base_iso):
        print(f"ERROR: Base ISO not found at: {base_iso}")
        sys.exit(1)
    if not os.path.exists(clean_elf):
        print(f"ERROR: Decrypted clean ELF not found at: {clean_elf}")
        sys.exit(1)
    if not os.path.exists(clean_script):
        print(f"Extracting original script.bin from base ISO: {base_iso}...")
        os.makedirs(EXTRACTED_DIR, exist_ok=True)
        res_ext = subprocess.run([
            sys.executable,
            os.path.join(TOOLS_DIR, "dc1_iso.py"),
            "extract-file",
            base_iso,
            "PSP_GAME/USRDIR/data/script.bin",
            clean_script,
        ])
        if res_ext.returncode != 0 or not os.path.exists(clean_script):
            print(f"ERROR: Failed to extract script.bin from base ISO.")
            sys.exit(1)
    if not os.path.exists(font_file):
        print(f"ERROR: Shrunk font not found at: {font_file}")
        sys.exit(1)
    if not os.path.exists(translation_json):
        print(f"ERROR: Translation JSON not found at: {translation_json}")
        sys.exit(1)

    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 2. Patch EBOOT
    print(f"\n[1/4] Patching EBOOT ({lang.upper()})...")
    cmd_eboot = [
        sys.executable,
        os.path.join(TOOLS_DIR, "dc1_eboot_patch.py"),
        clean_elf,
        target_elf,
        "--lang",
        lang,
    ]
    res = subprocess.run(cmd_eboot)
    if res.returncode != 0:
        print("ERROR: EBOOT patching failed.")
        sys.exit(res.returncode)

    # 3. Rebuild script.bin
    print(f"\n[2/4] Rebuilding script.bin from {os.path.basename(translation_json)}...")
    cmd_import = [
        sys.executable,
        os.path.join(TOOLS_DIR, "dc1_import.py"),
        clean_script,
        translation_json,
        target_script,
    ]
    res = subprocess.run(cmd_import)
    if res.returncode != 0:
        print("ERROR: script.bin rebuilding failed.")
        sys.exit(res.returncode)

    # 4. Verify bytecode jumps
    print(f"\n[3/4] Verifying script integrity and jumps...")
    cmd_verify = [
        sys.executable,
        os.path.join(TOOLS_DIR, "verify_rebuild.py"),
        clean_script,
        target_script,
        translation_json,
    ]
    res = subprocess.run(cmd_verify)
    if res.returncode != 0:
        print("ERROR: script verification failed.")
        sys.exit(res.returncode)

    # 5. Patch ISO
    print(f"\n[4/4] Building patched ISO: {out_iso}...")
    cmd_iso = [
        sys.executable,
        os.path.join(TOOLS_DIR, "dc1_iso.py"),
        "patch",
        base_iso,
        out_iso,
        "--relocate",
        f"PSP_GAME/USRDIR/data/script.bin={target_script}",
        "--replace",
        f"PSP_GAME/USRDIR/data/font.pgf={font_file}",
        "--replace",
        f"PSP_GAME/SYSDIR/EBOOT.BIN={target_elf}",
    ]

    # Check for custom video replacements (e.g. Opening with custom lyrics)
    custom_dir = os.path.join(BASE_DIR, "custom")
    custom_video_dir = os.path.join(custom_dir, "video")
    custom_ui_dir = os.path.join(custom_dir, "ui")

    if os.path.exists(os.path.join(custom_video_dir, "dc1_op.pmf")):
        op_path = os.path.join(custom_video_dir, "dc1_op.pmf")
        print(f"  [CUSTOM ASSET] Injecting Custom Opening Video: {op_path}")
        cmd_iso.extend(["--relocate", f"PSP_GAME/USRDIR/data/dc1_op.pmf={op_path}"])

    if os.path.exists(os.path.join(custom_video_dir, "gend.pmf")):
        ed_path = os.path.join(custom_video_dir, "gend.pmf")
        print(f"  [CUSTOM ASSET] Injecting Custom Ending Video: {ed_path}")
        cmd_iso.extend(["--relocate", f"PSP_GAME/USRDIR/data/gend.pmf={ed_path}"])

    # Check for custom UI replacements (catfile.bin or loose PNGs)
    if os.path.exists(os.path.join(custom_ui_dir, "catfile.bin")):
        cat_path = os.path.join(custom_ui_dir, "catfile.bin")
        print(f"  [CUSTOM ASSET] Injecting Custom UI catfile.bin: {cat_path}")
        cmd_iso.extend(["--relocate", f"PSP_GAME/USRDIR/data/catfile.bin={cat_path}"])

    for png_name in ["sav_bg.png", "dc1_new.png", "sav_dc1.png", "sys_dc1.png"]:
        p_path = os.path.join(custom_ui_dir, png_name)
        if os.path.exists(p_path):
            print(f"  [CUSTOM ASSET] Injecting Custom UI PNG: {png_name}")
            cmd_iso.extend(["--replace", f"PSP_GAME/USRDIR/data/{png_name}={p_path}"])

    for xmb_png in ["ICON0.PNG", "PIC1.PNG"]:
        p_path = os.path.join(custom_ui_dir, xmb_png)
        if os.path.exists(p_path):
            print(f"  [CUSTOM ASSET] Injecting Custom XMB Graphic: {xmb_png}")
            cmd_iso.extend(["--replace", f"PSP_GAME/{xmb_png}={p_path}"])

    res = subprocess.run(cmd_iso)
    if res.returncode != 0:
        print("ERROR: ISO patching failed.")
        sys.exit(res.returncode)

    # 6. Verification
    print("\n" + "=" * 70)
    print(" BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    iso_size = os.path.getsize(out_iso)
    iso_hash = md5_file(out_iso)
    print(f"Output ISO : {out_iso}")
    print(f"File Size  : {iso_size:,} bytes")
    print(f"MD5 Hash   : {iso_hash}")
    print("Ready to play in PPSSPP or real PSP hardware!")


if __name__ == "__main__":
    main()
