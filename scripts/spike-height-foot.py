"""Height/foot-only pass (no early exit from noisy date patterns)."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike")
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)


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
    patterns: dict[str, bytes] = {}
    for p in PLAYERS:
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        h = p["height_cm"]
        patterns[f"{p['name']}|02_uid_00_h"] = b"\x02" + uid + b"\x00" + bytes([h])
        for footv in range(0, 4):
            patterns[f"{p['name']}|02_uid_00_h_f{footv}"] = (
                b"\x02" + uid + b"\x00" + bytes([h, footv])
            )
        # also wider: uid then height within next 8 bytes (scan via marker)
        patterns[f"{p['name']}|02_uid"] = b"\x02" + uid

    # mystery floats after person uid@rel44
    mystery = {
        "Seimen_f": bytes.fromhex("0023da3e"),
        "Bandeira_f": bytes.fromhex("606a233f"),
        "Muller_f": bytes.fromhex("00c5463f"),
    }
    for k, v in mystery.items():
        print(k, "u32", struct.unpack("<I", v)[0], "f32", struct.unpack("<f", v)[0])

    overlap = 64
    carry = b""
    abs_base = 0
    hits = {k: [] for k in patterns}

    for block in stream_blocks():
        data = carry + block
        for name, pat in patterns.items():
            if len(hits[name]) >= 6:
                continue
            start = 0
            while len(hits[name]) < 6:
                i = data.find(pat, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                if hits[name] and hits[name][-1] == abs_off:
                    start = i + 1
                    continue
                ctx = data[i : min(len(data), i + 48)]
                hits[name].append((abs_off, ctx.hex(" ")))
                start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]

    lines = ["=== HEIGHT / FOOT ==="]
    for p in PLAYERS:
        lines.append(
            f"\n{p['name']} height={p['height_cm']} foot={p['foot']} uid={p['uid']}"
        )
        for suffix in (
            "02_uid_00_h",
            "02_uid_00_h_f0",
            "02_uid_00_h_f1",
            "02_uid_00_h_f2",
            "02_uid_00_h_f3",
        ):
            key = f"{p['name']}|{suffix}"
            rows = hits.get(key, [])
            lines.append(f"  {suffix}: {len(rows)}")
            for off, ctx in rows[:3]:
                lines.append(f"    @{off}  {ctx}")

        # From generic 02_uid hits, find ones where byte at +5 equals height
        uid_hits = hits.get(f"{p['name']}|02_uid", [])
        height_matches = []
        for off, ctx in uid_hits:
            raw = bytes.fromhex(ctx.replace(" ", ""))
            # 02 uid(4) ?? → inspect bytes 5..12
            if len(raw) >= 7 and raw[5] == p["height_cm"]:
                height_matches.append((off, ctx, list(raw[5:12])))
            elif len(raw) >= 8 and raw[6] == p["height_cm"]:
                height_matches.append((off, ctx, list(raw[5:12])))
        lines.append(f"  02_uid with nearby height: {len(height_matches)}")
        for off, ctx, around in height_matches[:5]:
            lines.append(f"    @{off} around={around}  {ctx}")

    text = "\n".join(lines)
    (OUT / "height-foot-only.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
