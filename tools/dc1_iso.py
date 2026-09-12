#!/usr/bin/env python3
"""ISO9660 inspection/extraction/patching for the DC1 PSP ISO.

patch mode (ported from the proven dc2_iso.py):
  SRC.iso DST.iso --replace PATH=FILE [--relocate PATH=FILE]

  --replace   write new bytes at the file's existing extent, zero-pad the
              rest. Must fit before the next file's sector.
  --relocate  append the new bytes at the END of the image (sector-aligned)
              and repoint the directory record (both-endian, every volume
              descriptor). Used when a file grows beyond its old extent.
"""

import argparse
import os
import shutil
import struct
import sys

SECTOR = 2048


def read_at(f, offset, size):
    f.seek(offset)
    return f.read(size)


def parse_dir_records(data, base_offset):
    records = []
    off = 0
    while off < len(data):
        length = data[off]
        if length == 0:
            off += 1
            continue
        if off + length > len(data) or length < 34:
            break
        rec = data[off:off + length]
        name_len = rec[32]
        name = rec[33:33 + name_len].decode("ascii", "replace").split(";")[0]
        records.append({
            "name": name,
            "extent": struct.unpack_from("<I", rec, 2)[0],
            "size": struct.unpack_from("<I", rec, 10)[0],
            "flags": rec[25],
            "record_offset": base_offset + off,
        })
        off += length
    return records


def descriptors(f):
    out = []
    for sector in range(16, 64):
        hdr = read_at(f, sector * SECTOR, 7)
        if len(hdr) < 7 or hdr[1:6] != b"CD001":
            break
        if hdr[0] == 255:
            break
        if hdr[0] in (1, 2):
            rec = read_at(f, sector * SECTOR + 156, 34)
            out.append((sector, struct.unpack_from("<I", rec, 2)[0], struct.unpack_from("<I", rec, 10)[0]))
    return out


def find_path(f, path, root_extent, root_size):
    current_extent, current_size = root_extent, root_size
    parts = [p for p in path.replace("\\", "/").strip("/").split("/") if p]
    if not parts:
        return None
    for index, part in enumerate(parts):
        raw = read_at(f, current_extent * SECTOR, current_size)
        candidates = [r for r in parse_dir_records(raw, current_extent * SECTOR) if r["name"].lower() == part.lower()]
        if not candidates:
            return None
        record = candidates[0]
        if index == len(parts) - 1:
            return record
        if not record["flags"] & 0x02:
            return None
        current_extent, current_size = record["extent"], record["size"]
    return None


def walk_files(f, extent, size, prefix=""):
    raw = read_at(f, extent * SECTOR, size)
    for record in parse_dir_records(raw, extent * SECTOR):
        name = record["name"]
        if name in ("", "\x00", "\x01"):
            continue
        rel = (prefix + "/" + name).strip("/")
        yield rel, record
        if record["flags"] & 0x02:
            yield from walk_files(f, record["extent"], record["size"], rel)


def collect_all_extents(f, extent, size):
    seen = set()
    extents = []
    stack = [(extent, size)]
    while stack:
        ext, sz = stack.pop()
        if (ext, sz) in seen:
            continue
        seen.add((ext, sz))
        raw = read_at(f, ext * SECTOR, sz)
        for record in parse_dir_records(raw, ext * SECTOR):
            extents.append((record["extent"], record["size"], record["name"]))
            if record["flags"] & 0x02:
                stack.append((record["extent"], record["size"]))
    return extents


def patch_file_in_image(f, entry, new_bytes, usable):
    if len(new_bytes) > usable:
        raise ValueError("replacement %d B does not fit %s (max %d B)"
                         % (len(new_bytes), entry["name"], usable))
    start = entry["extent"] * SECTOR
    f.seek(start)
    f.write(b"\x00" * usable)
    f.seek(start)
    f.write(new_bytes)
    f.seek(entry["record_offset"] + 10)
    f.write(struct.pack("<I", len(new_bytes)))
    f.seek(entry["record_offset"] + 14)
    f.write(struct.pack(">I", len(new_bytes)))


def relocate_file_in_image(f, entry, new_bytes):
    f.seek(0, 2)
    end = f.tell()
    new_ext = (end + SECTOR - 1) // SECTOR
    pad = (len(new_bytes) + SECTOR - 1) // SECTOR * SECTOR
    f.seek(new_ext * SECTOR)
    f.write(b"\x00" * pad)
    f.seek(new_ext * SECTOR)
    f.write(new_bytes)
    f.seek(entry["record_offset"] + 2)
    f.write(struct.pack("<I", new_ext))
    f.seek(entry["record_offset"] + 6)
    f.write(struct.pack(">I", new_ext))
    f.seek(entry["record_offset"] + 10)
    f.write(struct.pack("<I", len(new_bytes)))
    f.seek(entry["record_offset"] + 14)
    f.write(struct.pack(">I", len(new_bytes)))
    return new_ext


def command_patch(src_iso, dst_iso, repls, relocs):
    shutil.copyfile(src_iso, dst_iso)
    changed = 0
    with open(dst_iso, "r+b") as f:
        desc = descriptors(f)
        if not desc:
            raise ValueError("no ISO9660 volume descriptor")
        print("volume descriptors: %d" % len(desc))
        root_extent, root_size = desc[0][1], desc[0][2]
        all_extents = collect_all_extents(f, root_extent, root_size)
        starts = sorted(e[0] for e in all_extents)

        for iso_path, local in repls:
            parts = [p for p in iso_path.replace("\\", "/").strip("/").split("/") if p]
            with open(local, "rb") as lf:
                new_bytes = lf.read()
            found = False
            for _sector, r_ext, r_size in desc:
                entry = find_path(f, "/".join(parts), r_ext, r_size)
                if entry is None:
                    continue
                nxt = [s for s in starts if s > entry["extent"]]
                usable = ((nxt[0] - entry["extent"]) * SECTOR if nxt
                          else (entry["size"] + SECTOR - 1) // SECTOR * SECTOR)
                print("  replace %-42s ext=%d size=%d -> %d bytes"
                      % (iso_path, entry["extent"], entry["size"], len(new_bytes)))
                patch_file_in_image(f, entry, new_bytes, usable)
                found = True
                changed += 1
            if not found:
                raise ValueError("ISO path not found: " + iso_path)

        for iso_path, local in relocs:
            parts = [p for p in iso_path.replace("\\", "/").strip("/").split("/") if p]
            with open(local, "rb") as lf:
                new_bytes = lf.read()
            found = False
            for _sector, r_ext, r_size in desc:
                entry = find_path(f, "/".join(parts), r_ext, r_size)
                if entry is None:
                    continue
                print("  relocate %-41s ext=%d size=%d -> %d bytes"
                      % (iso_path, entry["extent"], entry["size"], len(new_bytes)))
                relocate_file_in_image(f, entry, new_bytes)
                found = True
                changed += 1
            if not found:
                raise ValueError("ISO path not found: " + iso_path)
    print("patched %d record(s) -> %s" % (changed, dst_iso))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("info", "list"):
        p = sub.add_parser(name)
        p.add_argument("iso")
    p = sub.add_parser("extract-file")
    p.add_argument("iso")
    p.add_argument("iso_path")
    p.add_argument("output")
    p = sub.add_parser("patch")
    p.add_argument("src_iso")
    p.add_argument("dst_iso")
    p.add_argument("--replace", action="append", metavar="PATH=FILE")
    p.add_argument("--relocate", action="append", metavar="PATH=FILE")
    args = parser.parse_args(argv)

    def split_specs(specs):
        out = []
        for spec in specs or []:
            if "=" not in spec:
                raise ValueError("needs PATH=FILE: " + spec)
            iso_path, local = spec.split("=", 1)
            out.append((iso_path, local))
        return out

    try:
        if args.command == "patch":
            command_patch(args.src_iso, args.dst_iso,
                          split_specs(args.replace), split_specs(args.relocate))
            return 0
        with open(args.iso, "rb") as f:
            desc = descriptors(f)
            if not desc:
                raise ValueError("no ISO9660 volume descriptor")
            sector, root_extent, root_size = desc[0]
            if args.command == "info":
                print("iso:", args.iso)
                print("size:", os.path.getsize(args.iso))
                print("volume_descriptors:", desc)
                print("root_extent:", root_extent, "root_size:", root_size)
                target = "PSP_GAME/USRDIR/data/script.bin"
                record = find_path(f, target, root_extent, root_size)
                print(target + ":", record)
            elif args.command == "list":
                for path, record in walk_files(f, root_extent, root_size):
                    print("%10d %s" % (record["size"], path))
            else:
                record = find_path(f, args.iso_path, root_extent, root_size)
                if record is None:
                    raise ValueError("ISO path not found: " + args.iso_path)
                os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
                f.seek(record["extent"] * SECTOR)
                remaining = record["size"]
                with open(args.output, "wb") as out:
                    while remaining:
                        chunk = f.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError("unexpected end of ISO file data")
                        out.write(chunk)
                        remaining -= len(chunk)
                print("extracted", args.iso_path, "->", args.output, "(%d bytes)" % record["size"])
    except (OSError, ValueError, struct.error) as exc:
        print("error:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

