"""Find Seimen double-UID records and dump following attribute-like regions."""

from __future__ import annotations

import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/seimen-double-uid.txt")

UID = struct.pack("<I", 2000175080)
DOUBLE = UID + UID
# common headers seen before attr packs
MARKERS = [
    bytes.fromhex("058c0c"),
    bytes.fromhex("050c1a058c0c"),
    bytes.fromhex("058c1a058c0c"),
    bytes.fromhex("05cc1b058c0c"),
    bytes.fromhex("1401010101010101010101010101"),  # Seimen scale dump style
]


def main() -> None:
    lines = []
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        overlap = 512
        hits = []
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                start = 0
                while len(hits) < 20:
                    i = data.find(DOUBLE, start)
                    if i < 0:
                        break
                    abs_off = abs_base - len(carry) + i
                    after = data[i : i + 256]
                    # marker search in following 200 bytes
                    marks = {}
                    for m in MARKERS:
                        j = after.find(m)
                        marks[m.hex()] = j
                    hits.append((abs_off, after.hex(" "), marks, list(after[:120])))
                    start = i + 1
                abs_base += len(block)
                carry = data[-overlap:]
                if len(hits) >= 20:
                    break
        finally:
            reader.close()

    lines.append(f"double-UID hits: {len(hits)}")
    for abs_off, hx, marks, lst in hits:
        lines.append(f"\nabs={abs_off}")
        lines.append(f"  markers: {marks}")
        lines.append(f"  first120: {lst}")
        lines.append(f"  hex: {hx[:300]}")

    # Also: single UID followed within 64 bytes by 05 8c 0c
    lines.append("\n\n==== UID then 05 8c 0c within 96 bytes ====")
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        found = []
        marker = bytes.fromhex("058c0c")
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                start = 0
                while len(found) < 15:
                    i = data.find(UID, start)
                    if i < 0:
                        break
                    abs_off = abs_base - len(carry) + i
                    window = data[i : i + 128]
                    j = window.find(marker)
                    if j >= 0:
                        found.append((abs_off, j, list(window[j : j + 80])))
                    start = i + 1
                abs_base += len(block)
                carry = data[-160:]
                if len(found) >= 15:
                    break
        finally:
            reader.close()
    lines.append(f"hits: {len(found)}")
    for abs_off, rel, attrs in found:
        lines.append(f"  uid@abs={abs_off} marker_rel=+{rel} following={attrs}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
