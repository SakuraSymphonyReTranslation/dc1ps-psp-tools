#!/usr/bin/env python3
"""Survey DC1 PSP blobs: relative-jump families, choice structure, entry counts."""

import collections
import struct
import sys

sys.path.insert(0, r"F:\Games\PSP\dc1ps-psp-tools\tools")
import dc1_script as S  # noqa: E402


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = open(r"F:\Games\PSP\dc1ps-psp-tools\work\extracted\script.bin", "rb").read()
    ops = collections.Counter()
    files_lines = {}
    for index, blob in S.iter_scripts(data):
        n = 0
        i = 8
        while i < len(blob) - 1:
            op = blob[i:i + 2]
            ops[op.hex()] += 1
            i += 1
        lines = S.extract_blob(blob, index)
        files_lines[index] = len(lines)
    # interesting families
    print("byte-pair histogram (top 40):")
    for k, v in ops.most_common(40):
        print("  %s: %d" % (k, v))
    print()
    print("22-family:", {k: v for k, v in ops.items() if k.startswith("22")})
    print("46-family:", {k: v for k, v in ops.items() if k.startswith("46")})
    print("21-family:", {k: v for k, v in ops.items() if k.startswith("21")})
    print("43-family:", {k: v for k, v in ops.items() if k.startswith("43")})
    print("36-family:", {k: v for k, v in ops.items() if k.startswith("36")})
    print()
    print("script_0001 lines:", files_lines.get(1))
    print("script_0002 lines:", files_lines.get(2))
    print("script_0005 lines:", files_lines.get(5))
    print("script_0014 lines:", files_lines.get(14))


if __name__ == "__main__":
    main()
