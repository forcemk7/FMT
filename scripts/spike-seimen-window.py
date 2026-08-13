"""Sliding-window search for Seimen's unique attribute multiset."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
SEIMEN = next(
    p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
    if p["uid"] == 2000175080
)
OUT = Path("tmp/fm-spike/seimen-window-score.txt")

UID = struct.pack("<I", 2000175080)
IID = struct.pack("<I", 0x0001BB6D)

# Use unique-ish mental+tech fingerprint values
# multiset of mental in UI order — require ALL present in window (as multiset)
MENTAL = list(SEIMEN["attributes"]["mental"].values())
GK = list(SEIMEN["attributes"]["goalkeeping"].values())
PHYS = list(SEIMEN["attributes"]["physical"].values())
TECH = list(SEIMEN["attributes"]["technical"].values())

# Distinctive required keys
REQUIRED = [
    SEIMEN["attributes"]["mental"]["determination"],  # 18
    SEIMEN["attributes"]["mental"]["leadership"],  # 16
    SEIMEN["attributes"]["mental"]["flair"],  # 8
    SEIMEN["attributes"]["mental"]["offTheBall"],  # 1
    SEIMEN["attributes"]["technical"]["freeKickTaking"],  # 3
]


def covers(window: bytes, needed: list[int]) -> bool:
    """True if window contains needed values as a multiset (with multiplicity)."""
    from collections import Counter

    have = Counter(window)
    need = Counter(needed)
    return all(have[v] >= c for v, c in need.items())


def main() -> None:
    W = 48  # compact window — attrs likely packed tightly if present
    lines = []
    hits = []

    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        overlap = W + 64
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                # step through; for speed, only start at positions where we see det=18
                # and required flair nearby
                i = 0
                limit = len(data) - W
                while i < limit:
                    if data[i] != 18:  # determination
                        i += 1
                        continue
                    win = data[i : i + W]
                    if 8 not in win or 1 not in win or 16 not in win or 3 not in win:
                        i += 1
                        continue
                    if covers(win, MENTAL):
                        abs_off = abs_base - len(carry) + i
                        # expand context for uid/iid
                        ctx_s = max(0, i - 128)
                        ctx_e = min(len(data), i + W + 128)
                        ctx = data[ctx_s:ctx_e]
                        rel = i - ctx_s
                        hits.append(
                            {
                                "abs": abs_off,
                                "uid_rel": (
                                    ctx.find(UID) - rel if UID in ctx else None
                                ),
                                "iid_rel": (
                                    ctx.find(IID) - rel if IID in ctx else None
                                ),
                                "win": list(win),
                                "gk_cover": covers(win, GK),
                                "phys_cover": covers(win, PHYS),
                                "tech_cover": covers(win, TECH),
                                "ctx": ctx[max(0, rel - 32) : rel + W + 32].hex(" "),
                            }
                        )
                        if len(hits) >= 30:
                            break
                    i += 1
                if len(hits) >= 30:
                    break
                abs_base += len(block)
                carry = data[-overlap:]
        finally:
            reader.close()

    lines.append(f"windows covering full mental ({W}B, start at det=18): {len(hits)}")
    for h in hits[:20]:
        lines.append(
            f"\nabs={h['abs']} uid_rel={h['uid_rel']} iid_rel={h['iid_rel']} "
            f"gk={h['gk_cover']} phys={h['phys_cover']} tech={h['tech_cover']}"
        )
        lines.append(f"  win: {h['win']}")
        lines.append(f"  ctx: {h['ctx']}")

    # Also try W=64 covering mental+phys
    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
