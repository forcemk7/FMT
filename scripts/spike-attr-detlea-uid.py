"""Verify det/00/lea/7f/02/uid (and close variants) for all three players."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/attr-detlea-uid.txt")


def main() -> None:
    patterns = {}
    for p in PLAYERS:
        det, lea = p["det"], p["lea"]
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        n = p["name"]
        for mid in (0x7F, 0xFF, 0x00, 0x80, 0x3F):
            patterns[f"{n}|det_00_lea_{mid:02x}_02_uid"] = (
                bytes([det, 0, lea, mid, 2]) + uid
            )
            patterns[f"{n}|det_lea_{mid:02x}_02_uid"] = bytes([det, lea, mid, 2]) + uid
        patterns[f"{n}|det_00_lea_02_uid"] = bytes([det, 0, lea, 2]) + uid
        # after uid
        for mid in (0x7F, 0x80, 0x00):
            patterns[f"{n}|02_uid_det_00_lea_{mid:02x}"] = (
                b"\x02" + uid + bytes([det, 0, lea, mid])
            )
            patterns[f"{n}|02_uid_det_lea_{mid:02x}"] = b"\x02" + uid + bytes(
                [det, lea, mid]
            )

    hits = {k: [] for k in patterns}
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        overlap = 64
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                for name, pat in patterns.items():
                    if len(hits[name]) >= 8:
                        continue
                    start = 0
                    while len(hits[name]) < 8:
                        i = data.find(pat, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        if hits[name] and hits[name][-1] == abs_off:
                            start = i + 1
                            continue
                        ctx = data[max(0, i - 32) : i + len(pat) + 48]
                        hits[name].append((abs_off, ctx.hex(" ")))
                        start = i + 1
                abs_base += len(block)
                carry = data[-overlap:]
        finally:
            reader.close()

    lines = []
    for p in PLAYERS:
        lines.append(f"\n======== {p['name']} det={p['det']} lea={p['lea']} ========")
        any_hit = False
        for k in sorted(hits):
            if not k.startswith(p["name"] + "|"):
                continue
            rows = hits[k]
            if not rows:
                continue
            any_hit = True
            lines.append(f"  {k.split('|',1)[1]}: {len(rows)}")
            for off, ctx in rows[:5]:
                lines.append(f"    @{off}")
                lines.append(f"      {ctx}")
        if not any_hit:
            lines.append("  (no patterned hits)")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
