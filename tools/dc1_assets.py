#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dc1_assets.py — Extract & prepare custom video (PMF) and UI textures for D.C.P.S.

Features:
  1. extract-video: Extract opening (dc1_op.pmf) & ending (gend.pmf) from base ISO to custom/video/
  2. extract-ui: Extract UI PNGs & unpack catfile.bin (815 MIG textures) to custom/ui/
  3. repack-catfile: Repack modified .mig textures from custom/ui/catfile_extracted/ into custom/ui/catfile.bin

Usage:
    python tools/dc1_assets.py extract-video
    python tools/dc1_assets.py extract-ui
    python tools/dc1_assets.py repack-catfile
"""

import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
CUSTOM_DIR = os.path.join(BASE_DIR, "custom")
DEFAULT_BASE_ISO = r"F:\Games\PSP\pkg2zip_32bit\D.C.P.S. [NPJH50731].iso"


def extract_video(base_iso: str):
    out_dir = os.path.join(CUSTOM_DIR, "video")
    os.makedirs(out_dir, exist_ok=True)
    
    videos = [
        ("PSP_GAME/USRDIR/data/dc1_op.pmf", "dc1_op.pmf", "Opening Movie"),
        ("PSP_GAME/USRDIR/data/gend.pmf", "gend.pmf", "Grand Ending Movie"),
    ]
    
    print(f"Extracting video files from base ISO to: {out_dir}...")
    for iso_path, local_name, desc in videos:
        dst = os.path.join(out_dir, local_name)
        cmd = [
            sys.executable,
            os.path.join(TOOLS_DIR, "dc1_iso.py"),
            "extract-file",
            base_iso,
            iso_path,
            dst,
        ]
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print(f"  [OK] Extracted {desc}: {dst} ({os.path.getsize(dst):,} bytes)")
        else:
            print(f"  [FAIL] Failed to extract {desc}")
            
    print("\n[INFO] Kamu sekarang bisa mengedit video (misal menambah lirik subtitle).")
    print("Format yang didukung PSP: PMF (PlayStation Movie Format, AVC video 480x272 + ATRAC3plus audio).")
    print(f"Jika ada file '{out_dir}/dc1_op.pmf', sistem build akan otomatis memasukkannya ke ISO baru!")


def extract_ui(base_iso: str):
    out_dir = os.path.join(CUSTOM_DIR, "ui")
    os.makedirs(out_dir, exist_ok=True)
    
    pngs = [
        ("PSP_GAME/USRDIR/data/sav_bg.png", "sav_bg.png", "Save/Load Screen Background"),
        ("PSP_GAME/USRDIR/data/dc1_new.png", "dc1_new.png", "'NEW' Save Slot Label"),
        ("PSP_GAME/USRDIR/data/sav_dc1.png", "sav_dc1.png", "Save File Icon"),
        ("PSP_GAME/USRDIR/data/sys_dc1.png", "sys_dc1.png", "System File Icon"),
        ("PSP_GAME/ICON0.PNG", "ICON0.PNG", "XMB Game Icon"),
        ("PSP_GAME/PIC1.PNG", "PIC1.PNG", "XMB Background Wallpaper"),
    ]
    
    print(f"Extracting loose UI PNGs from base ISO to: {out_dir}...")
    for iso_path, local_name, desc in pngs:
        dst = os.path.join(out_dir, local_name)
        cmd = [
            sys.executable,
            os.path.join(TOOLS_DIR, "dc1_iso.py"),
            "extract-file",
            base_iso,
            iso_path,
            dst,
        ]
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print(f"  [OK] Extracted {desc}: {dst}")
            
    # Extract catfile.bin
    catfile_bin = os.path.join(out_dir, "catfile.bin")
    cmd = [
        sys.executable,
        os.path.join(TOOLS_DIR, "dc1_iso.py"),
        "extract-file",
        base_iso,
        "PSP_GAME/USRDIR/data/catfile.bin",
        catfile_bin,
    ]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"  [OK] Extracted catfile.bin container ({os.path.getsize(catfile_bin):,} bytes)")
        # Unpack .mig files
        mig_dir = os.path.join(out_dir, "catfile_extracted")
        cmd_unpack = [
            sys.executable,
            os.path.join(TOOLS_DIR, "dc1_catfile.py"),
            "extract",
            catfile_bin,
            mig_dir,
        ]
        subprocess.run(cmd_unpack)
        
    print(f"\n[INFO] Seluruh grafis UI dan tekstur telah diekstrak ke: {out_dir}")


def repack_ui():
    mig_dir = os.path.join(CUSTOM_DIR, "ui", "catfile_extracted")
    catfile_bin = os.path.join(CUSTOM_DIR, "ui", "catfile.bin")
    if not os.path.exists(mig_dir):
        print(f"ERROR: {mig_dir} tidak ditemukan. Jalankan 'extract-ui' terlebih dahulu.")
        sys.exit(1)
        
    cmd = [
        sys.executable,
        os.path.join(TOOLS_DIR, "dc1_catfile.py"),
        "repack",
        mig_dir,
        catfile_bin,
    ]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"[SUCCESS] Berhasil repacking {catfile_bin}")
        print("File ini akan otomatis diinjeksi ke ISO saat build dijalankan!")


def main():
    parser = argparse.ArgumentParser(description="Asset extraction and management tool for D.C.P.S.")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    
    p_v = subparsers.add_parser("extract-video", help="Extract opening & ending video from ISO")
    p_v.add_argument("--base", default=DEFAULT_BASE_ISO, help="Base ISO path")
    
    p_u = subparsers.add_parser("extract-ui", help="Extract UI PNGs & catfile.bin")
    p_u.add_argument("--base", default=DEFAULT_BASE_ISO, help="Base ISO path")
    
    p_r = subparsers.add_parser("repack-catfile", help="Repack catfile_extracted into catfile.bin")
    
    args = parser.parse_args()
    if args.cmd == "extract-video":
        extract_video(args.base)
    elif args.cmd == "extract-ui":
        extract_ui(args.base)
    elif args.cmd == "repack-catfile":
        repack_ui()


if __name__ == "__main__":
    main()
