#!/usr/bin/env python3
"""dc1_catfile.py: Extract and repack Circus D.C.P.S. catfile.bin container.

catfile.bin contains 815 compressed MIG.00.1PSP image assets (UI, sprites, backgrounds).
Header:
  0x00: 'CAT\x00' (4 bytes)
  0x04: file_count (uint32 LE)
  0x08: 0 (uint32)
  0x0C: 0 (uint32)
  0x10..: file_count offsets (uint32 LE)
Each entry:
  0x00: uncompressed_size (uint32 LE)
  0x04..: zlib compressed stream
"""

import argparse
import glob
import os
import struct
import sys
import zlib


def extract_catfile(cat_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(cat_path, "rb") as f:
        head = f.read(16)
        magic, count = struct.unpack("<4sI8x", head)
        if magic != b"CAT\x00":
            raise ValueError(f"Invalid CAT magic: {magic}")
            
        print(f"Extracting {count} files from {cat_path} to {out_dir}...")
        offsets = [struct.unpack("<I", f.read(4))[0] for _ in range(count)]
        f.seek(0, 2)
        total_size = f.tell()
        
        for i in range(count):
            start = offsets[i]
            end = offsets[i+1] if i + 1 < count else total_size
            f.seek(start)
            raw = f.read(end - start)
            if len(raw) < 4:
                continue
            uncomp_sz = int.from_bytes(raw[:4], "little")
            comp_data = raw[4:]
            try:
                dec = zlib.decompress(comp_data)
            except Exception as e:
                print(f"  Warning: entry {i:04d} decompression failed ({e}), saving raw")
                dec = raw
            out_file = os.path.join(out_dir, f"{i:04d}.mig")
            with open(out_file, "wb") as out_f:
                out_f.write(dec)
                
    print(f"Successfully extracted {count} files to {out_dir}")


def repack_catfile(in_dir, out_path):
    mig_files = sorted(glob.glob(os.path.join(in_dir, "*.mig")))
    if not mig_files:
        raise ValueError(f"No .mig files found in {in_dir}")
        
    count = len(mig_files)
    print(f"Repacking {count} files from {in_dir} to {out_path}...")
    
    header_size = 16 + (count * 4)
    # Align to 16 bytes
    header_pad = (16 - (header_size % 16)) % 16
    first_offset = header_size + header_pad
    
    offsets = []
    blobs = []
    cur_offset = first_offset
    
    for mf in mig_files:
        offsets.append(cur_offset)
        with open(mf, "rb") as f:
            uncomp_data = f.read()
        uncomp_sz = len(uncomp_data)
        comp_stream = zlib.compress(uncomp_data, level=9)
        payload = struct.pack("<I", uncomp_sz) + comp_stream
        blobs.append(payload)
        cur_offset += len(payload)
        
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as out:
        out.write(b"CAT\x00")
        out.write(struct.pack("<I", count))
        out.write(b"\x00" * 8)
        for off in offsets:
            out.write(struct.pack("<I", off))
        if header_pad:
            out.write(b"\x00" * header_pad)
        for b in blobs:
            out.write(b)
            
    print(f"Successfully repacked {count} files into {out_path} ({cur_offset} bytes)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    p_ext = sub.add_parser("extract", help="Extract catfile.bin into .mig files")
    p_ext.add_argument("catfile", help="Path to catfile.bin")
    p_ext.add_argument("outdir", help="Output directory")
    
    p_rep = sub.add_parser("repack", help="Repack .mig files into catfile.bin")
    p_rep.add_argument("indir", help="Directory with .mig files")
    p_rep.add_argument("outcat", help="Path to output catfile.bin")
    
    args = parser.parse_args()
    if args.cmd == "extract":
        extract_catfile(args.catfile, args.outdir)
    elif args.cmd == "repack":
        repack_catfile(args.indir, args.outcat)


if __name__ == "__main__":
    main()
