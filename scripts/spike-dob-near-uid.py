"""Find DOB (dmy/ymd) and height variants within a radius of each UID hit."""

from __future__ import annotations

import json
import struct
from collections import Counter
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/dob-near-uid.txt")
RADIUS = 256


def stream_blocks():
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            reader.close()


def main() -> None:
    lines = []
    for p in PLAYERS:
        uid_b = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        y, m, d = map(int, p["dob"].split("-"))
        pats = {
            "dmy": struct.pack("<BBH", d, m, y),
            "ymd": struct.pack("<HBB", y, m, d),
            "packed": struct.pack("<I", d | (m << 8) | (y << 16)),
            "h_u8": bytes([p["height_cm"]]),
            "h_minus100": bytes([p["height_cm"] - 100]),
            "h_u16le": struct.pack("<H", p["height_cm"]),
            "year_u16": struct.pack("<H", y),
        }
        rel_hits = {k: Counter() for k in pats}
        abs_base = 0
        carry = b""
        overlap = RADIUS * 2 + 16
        uid_n = 0
        for block in stream_blocks():
            data = carry + block
            start = 0
            while True:
                i = data.find(uid_b, start)
                if i < 0:
                    break
                uid_n += 1
                ws = max(0, i - RADIUS)
                we = min(len(data), i + 4 + RADIUS)
                window = data[ws:we]
                uid_rel = i - ws
                for name, pat in pats.items():
                    j = 0
                    while True:
                        k = window.find(pat, j)
                        if k < 0:
                            break
                        rel_hits[name][k - uid_rel] += 1
                        j = k + 1
                start = i + 1
            abs_base += len(block)
            carry = data[-overlap:]

        lines.append(
            f"\n======== {p['name']} dob={p['dob']} height={p['height_cm']} uid_hits={uid_n} ========"
        )
        for name, ctr in rel_hits.items():
            if not ctr:
                lines.append(f"  {name}: none")
                continue
            top = ctr.most_common(8)
            lines.append(f"  {name}: top rel_offsets={top}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
