"""For each UID, collect unique byte templates of the 24 bytes starting at each hit."""

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
OUT = Path("tmp/fm-spike/uid-templates.txt")


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
        h = p["height_cm"]
        # count layouts: 1 byte before uid + uid + 16 after
        templates = Counter()
        height_near = []
        abs_base = 0
        carry = b""
        overlap = 32
        total = 0
        for block in stream_blocks():
            data = carry + block
            start = 0
            while True:
                i = data.find(uid_b, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                if i >= 1 and i + 20 <= len(data):
                    total += 1
                    tmpl = data[i - 1 : i + 20]
                    templates[tmpl.hex(" ")] += 1
                    # height anywhere in uid..uid+16
                    after = data[i + 4 : i + 20]
                    if h in after:
                        height_near.append(
                            (
                                abs_off,
                                list(after).index(h),
                                data[i - 1 : i + 20].hex(" "),
                            )
                        )
                start = i + 1
            abs_base += len(block)
            carry = data[-overlap:]

        lines.append(
            f"\n======== {p['name']} uid={p['uid']} height={h} foot={p['foot']} ========"
        )
        lines.append(f"total uid hits scanned: {total}")
        lines.append(f"hits with height in next 16 bytes: {len(height_near)}")
        for off, idx, hx in height_near[:12]:
            lines.append(f"  height@+{4+idx} abs={off}  {hx}")
        lines.append("top templates (pre1 + uid + 16):")
        for hx, n in templates.most_common(12):
            lines.append(f"  n={n}  {hx}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
