"""Hunt DOB / height / preferred-foot encodings near known Unique IDs."""

from __future__ import annotations

import json
import struct
from datetime import date, datetime, timedelta
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike")
OUT.mkdir(parents=True, exist_ok=True)
FIXTURE = Path("data/fixtures/save-players.json")
PLAYERS = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))

# FM/community date heuristics
EPOCHS = {
    "unix": datetime(1970, 1, 1),
    "excel": datetime(1899, 12, 30),
    "y1900": datetime(1900, 1, 1),
    "y0001": datetime(1, 1, 1),
}


def date_patterns(dob_s: str) -> dict[str, bytes]:
    y, m, d = map(int, dob_s.split("-"))
    dt = datetime(y, m, d)
    out: dict[str, bytes] = {
        "ymd_u16_u8_u8": struct.pack("<HBB", y, m, d),
        "ymd_u16be_u8_u8": struct.pack(">HBB", y, m, d),
        "dmy_u8_u8_u16": struct.pack("<BBH", d, m, y),
        "ymd_u32_pack_yyyyMMdd": struct.pack("<I", y * 10000 + m * 100 + d),
        "ymd_bits_y9_m4_d5": struct.pack("<H", ((y - 1900) << 9) | (m << 5) | d),
    }
    for name, epoch in EPOCHS.items():
        days = (dt - epoch).days
        if 0 <= days <= 0xFFFFFFFF:
            out[f"days_{name}_u32le"] = struct.pack("<I", days)
            out[f"days_{name}_u16le"] = struct.pack("<H", days & 0xFFFF)
            if days <= 0x7FFFFFFF:
                out[f"days_{name}_i32le"] = struct.pack("<i", days)
        # seconds (unlikely but cheap)
        secs = int((dt - epoch).total_seconds())
        if 0 <= secs <= 0xFFFFFFFF:
            out[f"secs_{name}_u32le"] = struct.pack("<I", secs)
    # SI sometimes uses days from a football-specific base; keep year alone too
    out["year_u16le"] = struct.pack("<H", y)
    out["year_u16be"] = struct.pack(">H", y)
    return out


def stream_blocks(path: Path):
    with path.open("rb") as f:
        assert f.read(26)[2:6] == b"fmf."
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                yield block
        finally:
            reader.close()


def collect_uid_windows(uid: int, radius: int = 384, want: int = 8) -> list[tuple[int, bytes]]:
    pat = struct.pack("<I", uid & 0xFFFFFFFF)
    overlap = radius * 2
    carry = b""
    abs_base = 0
    found: list[tuple[int, bytes]] = []
    for block in stream_blocks(SAVE):
        data = carry + block
        start = 0
        while len(found) < want:
            i = data.find(pat, start)
            if i < 0:
                break
            abs_off = abs_base - len(carry) + i
            if found and found[-1][0] == abs_off:
                start = i + 1
                continue
            ws = max(0, i - radius)
            we = min(len(data), i + 4 + radius)
            found.append((abs_off, data[ws:we]))
            start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]
        if len(found) >= want:
            break
    return found


def score_window(win: bytes, uid_rel: int, p: dict) -> dict:
    hits: dict[str, list[int]] = {}
    for label, pat in date_patterns(p["dob"]).items():
        offs = []
        start = 0
        while True:
            i = win.find(pat, start)
            if i < 0:
                break
            offs.append(i - uid_rel)
            start = i + 1
        if offs:
            hits[f"dob:{label}"] = offs[:12]

    h = p["height_cm"]
    for label, pat in {
        "u8": bytes([h]),
        "u16le": struct.pack("<H", h),
        "u16be": struct.pack(">H", h),
        "u32le": struct.pack("<I", h),
    }.items():
        offs = []
        start = 0
        while True:
            i = win.find(pat, start)
            if i < 0:
                break
            offs.append(i - uid_rel)
            start = i + 1
        if offs:
            hits[f"height:{label}"] = offs[:20]

    # preferred foot enums commonly seen in FM tools
    foot = p["foot"]
    foot_map = {
        "Left": [1, 2],  # try both conventions
        "Right": [2, 1],
    }
    for val in foot_map[foot]:
        hits.setdefault(f"foot_u8_candidate_{val}", [])
        # only report if near height hit later; still count occurrences relative to uid
        for i, b in enumerate(win):
            if b == val:
                hits[f"foot_u8_candidate_{val}"].append(i - uid_rel)
        hits[f"foot_u8_candidate_{val}"] = hits[f"foot_u8_candidate_{val}"][:30]

    return hits


def main() -> None:
    lines: list[str] = []
    # Print date encodings for reference
    for p in PLAYERS:
        lines.append(f"\n==== encodings for {p['name']} dob={p['dob']} ====")
        for k, v in date_patterns(p["dob"]).items():
            lines.append(f"  {k}: {v.hex(' ')}")

    consensus: dict[str, list[int]] = {}

    for p in PLAYERS:
        lines.append(
            f"\n======== {p['name']} uid={p['uid']} height={p['height_cm']} foot={p['foot']} ========"
        )
        wins = collect_uid_windows(p["uid"], radius=384, want=10)
        lines.append(f"uid windows: {len(wins)}")
        per_player_hit_keys: dict[str, int] = {}
        for idx, (abs_off, win) in enumerate(wins):
            uid_rel = win.find(struct.pack("<I", p["uid"] & 0xFFFFFFFF))
            scored = score_window(win, uid_rel, p)
            # compact: only keep promising keys (dob days / ymd / height u8 near uid)
            interesting = {
                k: v
                for k, v in scored.items()
                if k.startswith("dob:")
                or k.startswith("height:u8")
                or k.startswith("height:u16")
            }
            if not interesting:
                continue
            lines.append(f"\n-- win[{idx}] uid@abs={abs_off} --")
            for k, v in sorted(interesting.items()):
                lines.append(f"  {k}: rel_offsets={v}")
                per_player_hit_keys[k] = per_player_hit_keys.get(k, 0) + 1
                # dump tiny context for first offset of best-looking keys
                if k.startswith("dob:days_") or k.startswith("dob:ymd_"):
                    rel = v[0]
                    at = uid_rel + rel
                    ctx = win[max(0, at - 8) : at + 12]
                    lines.append(f"    ctx@{rel}: {ctx.hex(' ')}")

            # height u8 contexts when present
            if "height:u8" in interesting:
                for rel in interesting["height:u8"][:5]:
                    at = uid_rel + rel
                    ctx = win[max(0, at - 6) : at + 10]
                    lines.append(f"  height_u8 ctx@{rel}: {ctx.hex(' ')}  asc={''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)}")

        lines.append(f"key frequency across windows: {per_player_hit_keys}")
        for k, n in per_player_hit_keys.items():
            consensus.setdefault(k, []).append(n)

    lines.append("\n======== CROSS-PLAYER CONSENSUS (key seen for how many players) ========")
    for k, vals in sorted(consensus.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"  {k}: players={len(vals)} window-hits={vals}")

    text = "\n".join(lines)
    (OUT / "dob-height-hunt.txt").write_text(text, encoding="utf-8")
    print(text)
    print("\nwrote", OUT / "dob-height-hunt.txt")


if __name__ == "__main__":
    main()
