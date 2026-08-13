#!/usr/bin/env python3
"""Calibrate CA snapshotU16 timeline against Robert Müller Progress Report."""

from __future__ import annotations

import json
import mmap
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
VERIFY = ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json"
OUT = ROOT / "tmp" / "fm-spike" / "ca-u16-timeline-muller.txt"
ATTR_LOOKBACK = 20_000
UID = 2002266341

MENTAL = [
    "aggression",
    "anticipation",
    "bravery",
    "vision",
    "decisions",
    "determination",
    "flair",
    "leadership",
    "offTheBall",
    "positioning",
    "teamwork",
    "workRate",
    "composure",
    "concentration",
]
PHYS = [
    "acceleration",
    "agility",
    "balance",
    "pace",
    "stamina",
    "strength",
    "jumpingReach",
    "naturalFitness",
]


def disp(b: bytes) -> list[int]:
    return [round(x / 5) for x in b]


def is_attrish(buf: bytes, i: int) -> bool:
    if i + 69 > len(buf):
        return False
    if buf[i + 34] or buf[i + 35] or buf[i + 43] != 0x01:
        return False
    return sum(1 for x in buf[i : i + 22] if 25 <= x <= 105) >= 12


def main() -> None:
    verify = json.loads(VERIFY.read_text(encoding="utf-8-sig"))
    pl = next(p for p in verify["players"] if p.get("uid") == UID)
    dab = int(pl["doubleUidAbs"])
    lines = [
        f"uid={UID} double={dab}",
        f"decomp={DECOMP.name} size={DECOMP.stat().st_size}",
        "Progress Report range (user shot): 27 Feb 35 .. 28 Jul; Det=16 Lea=17 now",
        "",
    ]

    with DECOMP.open("r+b") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            if dab >= len(mm):
                lines.append("ERROR: double beyond decomp length — decomp is stale vs verify extract")
                OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
                print(OUT)
                return
            lo = max(0, dab - ATTR_LOOKBACK)
            window = bytes(mm[lo:dab])
        finally:
            mm.close()

    cards = []
    start = 0
    while True:
        z = window.find(b"\x00\x00", start)
        if z < 0 or z + 35 > len(window):
            break
        i = z - 34
        if i >= 0 and z == i + 34 and is_attrish(window, i):
            cards.append((i, window[i : i + 69]))
            start = z + 69
        else:
            start = z + 1

    lines.append(f"cards_in_lookback={len(cards)}")

    # Collapse to unique (u16, det, lea, decisions, pac...) keeping nearest gap + max b23
    by_key: dict[tuple, list] = defaultdict(list)
    for off, rec in cards:
        gap = len(window) - off
        u16 = struct.unpack_from("<H", rec, 36)[0]
        ment = dict(zip(MENTAL, disp(rec[0:14])))
        phys = dict(zip(PHYS, disp(rec[14:22])))
        key = (
            u16,
            ment["determination"],
            ment["leadership"],
            ment["decisions"],
            ment["anticipation"],
            phys["acceleration"],
            phys["pace"],
        )
        by_key[key].append((gap, rec[23], ment, phys))

    # Prefer representative = min gap (nearest) among duplicates
    reps = []
    for key, group in by_key.items():
        group.sort(key=lambda t: (t[0], -t[1]))  # nearer, then higher b23
        gap, b23, ment, phys = group[0]
        reps.append((key[0], gap, b23, ment, phys, len(group)))

    reps.sort(key=lambda t: -t[0])  # high u16 first
    u16s = sorted({r[0] for r in reps})
    deltas = [b - a for a, b in zip(u16s, u16s[1:])]
    lines.append(f"unique_u16={u16s}")
    lines.append(f"u16_deltas={deltas}")
    lines.append(f"delta_mode_220={sum(1 for d in deltas if d == 220)}/{len(deltas)}")
    lines.append("")
    lines.append(
        "u16   gap   b23  n  Det Lea Dec Ant Acc Pac  (unique attr signatures)"
    )
    for u16, gap, b23, ment, phys, n in sorted(reps, key=lambda t: t[0]):
        lines.append(
            f"{u16:5d} {gap:5d} {b23:3d} {n:2d}  "
            f"{ment['determination']:3d} {ment['leadership']:3d} "
            f"{ment['decisions']:3d} {ment['anticipation']:3d} "
            f"{phys['acceleration']:3d} {phys['pace']:3d}"
        )

    # Hypothesis: tick = u16/220; map ticks to weeks ending at report end
    if u16s:
        lines.append("")
        lines.append("Hypothesis: u16 increases by 220 each weekly (or match) tick")
        ticks = [u // 220 for u in u16s]
        lines.append(f"tick_index={ticks}")
        lines.append(f"tick_span={ticks[-1] - ticks[0] if len(ticks) > 1 else 0}")
        # If Progress Report ~151 days Feb27-Jul28 ≈ 21.6 weeks
        lines.append("Progress Report ~151 days ≈ 21.6 weeks — compare to tick_span")

    # Also dump ordered by gap (far→near) unique u16 first-seen
    lines.append("")
    lines.append("far→near first-seen u16 with Det/Lea:")
    seen = set()
    ordered = []
    for off, rec in sorted(cards, key=lambda t: t[0]):  # low offset = far
        gap = len(window) - off
        u16 = struct.unpack_from("<H", rec, 36)[0]
        if u16 in seen:
            continue
        seen.add(u16)
        ment = dict(zip(MENTAL, disp(rec[0:14])))
        ordered.append((gap, u16, ment["determination"], ment["leadership"]))
    for gap, u16, det, lea in ordered:
        lines.append(f"  gap={gap:5d} u16={u16:5d} Det={det} Lea={lea}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT))
    print(f"cards={len(cards)} unique_sigs={len(reps)} u16s={u16s}")


if __name__ == "__main__":
    main()
