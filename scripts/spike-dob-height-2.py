"""Targeted DOB/height/foot hunt using person-record region + exact patterns."""

from __future__ import annotations

import json
import struct
from datetime import datetime
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike")
FIXTURE = Path("data/fixtures/save-players.json")
PLAYERS = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))


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


def find_all(patterns: dict[str, bytes], max_per: int = 20):
    overlap = max(len(p) for p in patterns.values()) - 1
    carry = b""
    abs_base = 0
    hits = {k: [] for k in patterns}
    for block in stream_blocks():
        data = carry + block
        for name, pat in patterns.items():
            if len(hits[name]) >= max_per:
                continue
            start = 0
            while len(hits[name]) < max_per:
                i = data.find(pat, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                if hits[name] and hits[name][-1] == abs_off:
                    start = i + 1
                    continue
                # context
                ws = max(0, i - 24)
                we = min(len(data), i + len(pat) + 32)
                hits[name].append((abs_off, data[ws:we].hex(" ")))
                start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]
        if all(len(hits[k]) >= max_per for k in hits):
            break
    return hits


def main() -> None:
    patterns: dict[str, bytes] = {}
    for p in PLAYERS:
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        h = p["height_cm"]
        # height table candidates
        patterns[f"{p['name']}|02_uid_00_height"] = b"\x02" + uid + b"\x00" + bytes([h])
        patterns[f"{p['name']}|02_uid_height"] = b"\x02" + uid + bytes([h])
        patterns[f"{p['name']}|uid_00_height"] = uid + b"\x00" + bytes([h])
        patterns[f"{p['name']}|uid_height_u16"] = uid + struct.pack("<H", h)

        y, m, d = map(int, p["dob"].split("-"))
        dt = datetime(y, m, d)
        # FM-ish packed date variants near uid
        dmy = struct.pack("<BBH", d, m, y)
        ymd = struct.pack("<HBB", y, m, d)
        packed = struct.pack("<I", d | (m << 8) | (y << 16))
        patterns[f"{p['name']}|uid_then_dmy"] = uid + dmy
        patterns[f"{p['name']}|uid_00_dmy"] = uid + b"\x00" + dmy
        patterns[f"{p['name']}|dmy"] = dmy
        patterns[f"{p['name']}|ymd"] = ymd
        patterns[f"{p['name']}|packed_dmy_u32"] = packed
        patterns[f"{p['name']}|uid_packed"] = uid + packed

        for ename, epoch in {
            "unix": datetime(1970, 1, 1),
            "excel": datetime(1899, 12, 30),
            "y1900": datetime(1900, 1, 1),
            "y0001": datetime(1, 1, 1),
        }.items():
            days = (dt - epoch).days
            patterns[f"{p['name']}|uid_days_{ename}"] = uid + struct.pack("<I", days)
            patterns[f"{p['name']}|days_{ename}"] = struct.pack("<I", days)

        # From previous person-record dumps: 4 bytes immediately after one uid copy
        # Seimen 00 23 da 3e / Bandeira 60 6a 23 3f / Muller 00 c5 46 3f
        # verify whether those sequences exist after uid in this save
        # (search uid + that blob once we know - below we just search floating mystery later)

        # preferred foot near height: Left vs Right try 1/2 and 0/1
        if p["foot"] == "Left":
            for footv in (1, 2, 0):
                patterns[f"{p['name']}|02_uid_00_h_foot{footv}"] = (
                    b"\x02" + uid + b"\x00" + bytes([h, footv])
                )
        else:
            for footv in (2, 1, 0):
                patterns[f"{p['name']}|02_uid_00_h_foot{footv}"] = (
                    b"\x02" + uid + b"\x00" + bytes([h, footv])
                )

    print("patterns", len(patterns))
    hits = find_all(patterns, max_per=8)
    lines = []
    for k in sorted(hits):
        if not hits[k]:
            continue
        lines.append(f"\n### {k}  n={len(hits[k])}")
        for off, ctx in hits[k][:5]:
            lines.append(f"  @{off}\n    {ctx}")

    # summary matrix
    lines.append("\n\n=== SUMMARY (hit counts) ===")
    for p in PLAYERS:
        lines.append(f"\n{p['name']}:")
        for k, v in sorted(hits.items()):
            if k.startswith(p["name"] + "|") and v:
                lines.append(f"  {k.split('|',1)[1]}: {len(v)} first={v[0][0]}")

    # Also dump relative layout in known person co-located style:
    # search name lp32 and show ~20 bytes before/after uid field after first name block
    lines.append("\n\n=== PERSON TRAIL BYTES (name-colocated) ===")
    for p in PLAYERS:
        name_b = p["name"].encode("utf-8")
        needle = struct.pack("<I", len(name_b)) + name_b
        uid_b = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        # find first late hit (>1e9)
        found = None
        abs_base = 0
        carry = b""
        for block in stream_blocks():
            data = carry + block
            start = 0
            while True:
                i = data.find(needle, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                behind = data[max(0, i - 120) : i]
                if uid_b in behind and abs_off > 1_000_000_000:
                    ws = max(0, i - 80)
                    we = min(len(data), i + len(needle) + 64)
                    found = (abs_off, data[ws:we])
                    break
                start = i + 1
            abs_base += len(block)
            carry = data[-200:]
            if found:
                break
        if not found:
            lines.append(f"{p['name']}: not found")
            continue
        off, win = found
        uid_at = win.find(uid_b)
        # find ALL uid occurrences in window and bytes immediately after each
        lines.append(f"\n{p['name']} name@abs={off}")
        pos = 0
        while True:
            j = win.find(uid_b, pos)
            if j < 0:
                break
            after = win[j + 4 : j + 20]
            lines.append(f"  uid_rel={j} after={after.hex(' ')}")
            # mark height if present in after
            if p["height_cm"] in after:
                lines.append(f"    ** height {p['height_cm']} at after[{list(after).index(p['height_cm'])}]")
            pos = j + 1
        lines.append("  window ascii: " + "".join(chr(b) if 32 <= b < 127 else "." for b in win))

    text = "\n".join(lines)
    (OUT / "dob-height-targeted.txt").write_text(text, encoding="utf-8")
    print(text[-12000:])
    print("wrote", OUT / "dob-height-targeted.txt")


if __name__ == "__main__":
    main()
