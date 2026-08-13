#!/usr/bin/env python3
"""
Find DOB encodings anywhere in the decomp head, then require the player's
UniqueID within ±radius — lock shared (encoding→UID) relative gaps.
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-backlink-hunt.txt"
PERSON_HEAD = 512 * 1024 * 1024
RADIUS = 4096
MAX_HITS = 80


def encodings(dob: date, age: int, game: date = date(2039, 7, 1)) -> dict[str, bytes]:
    yday0 = dob.timetuple().tm_yday - 1
    yday1 = dob.timetuple().tm_yday
    days1900 = (dob - date(1900, 1, 1)).days
    age_days = (game - dob).days
    leap = int(
        dob.year % 4 == 0 and (dob.year % 100 != 0 or dob.year % 400 == 0)
    )
    return {
        "tcm_d0_y": struct.pack("<hh", yday0, dob.year),
        "tcm_d1_y": struct.pack("<hh", yday1, dob.year),
        "tcm_y_d0": struct.pack("<hh", dob.year, yday0),
        "dmy": struct.pack("<BBH", dob.day, dob.month, dob.year),
        "ymd": struct.pack("<HBB", dob.year, dob.month, dob.day),
        "days1900_u32": struct.pack("<I", days1900),
        "age_days_u16": struct.pack("<H", age_days),
        "age_days_u32": struct.pack("<I", age_days),
        "age_u8": bytes([age]),
        "packed_dmy": struct.pack("<I", dob.day | (dob.month << 8) | (dob.year << 16)),
    }


def find_hits(mm: mmap.mmap, pat: bytes, limit: int = MAX_HITS) -> list[int]:
    hits: list[int] = []
    end = min(len(mm), PERSON_HEAD)
    # age_u8 is too common — skip bulk scan
    if len(pat) < 2:
        return []
    j = 0
    while len(hits) < limit:
        j = mm.find(pat, j, end)
        if j < 0:
            break
        hits.append(j)
        j += 1
    return hits


def nearest_uid(mm: mmap.mmap, pos: int, uid: int, radius: int = RADIUS) -> list[tuple[int, str]]:
    """Return (delta, kind) for UID occurrences near pos."""
    out: list[tuple[int, str]] = []
    lo = max(0, pos - radius)
    hi = min(len(mm), pos + radius + 4)
    win = bytes(mm[lo:hi])
    rel0 = pos - lo
    single = struct.pack("<I", uid)
    double = struct.pack("<II", uid, uid)
    start = 0
    while True:
        i = win.find(double, start)
        if i < 0:
            break
        out.append((i - rel0, "double"))
        start = i + 1
    start = 0
    while True:
        i = win.find(single, start)
        if i < 0:
            break
        # skip those that are part of double already counted roughly
        out.append((i - rel0, "single"))
        start = i + 1
    # dedupe keep best kinds
    return out


def main() -> None:
    lines: list[str] = [f"radius=±{RADIUS}", f"players={len(PLAYERS)}", ""]
    # encoding -> gap(uid-dob) -> count players
    gap_players: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                y, m, d = map(int, p["dob"].split("-"))
                dob = date(y, m, d)
                age = int(p["age"])
                uid = int(p["uid"])
                name = p["name"]
                lines.append(f"## {name} uid={uid} dob={dob} age={age}")
                for enc_name, pat in encodings(dob, age).items():
                    if enc_name == "age_u8":
                        continue  # useless alone
                    hits = find_hits(mm, pat)
                    linked = 0
                    for h in hits:
                        near = nearest_uid(mm, h, uid)
                        if not near:
                            continue
                        linked += 1
                        for delta, kind in near[:6]:
                            # gap = uid_pos - dob_pos
                            gap_players[f"{enc_name}|{kind}"][delta].add(name)
                    lines.append(
                        f"  {enc_name}: abs_hits={len(hits)} uid_linked={linked}"
                    )

            lines.append("\n## LOCK candidates: same UID←DOB gap across many players")
            for key, gaps in sorted(gap_players.items()):
                ranked = sorted(
                    ((gap, names) for gap, names in gaps.items()),
                    key=lambda t: (-len(t[1]), t[0]),
                )
                top = ranked[:8]
                best_n = len(top[0][1]) if top else 0
                if best_n < 5:
                    continue
                lines.append(f"### {key} best_players={best_n}")
                for gap, names in top:
                    if len(names) < 5:
                        break
                    lines.append(
                        f"  gap={gap:+6d} players={len(names)} "
                        f"eg={sorted(names)[:6]}"
                    )
        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # print lock section
    try:
        idx = next(i for i, ln in enumerate(lines) if ln.startswith("## LOCK"))
        print("\n".join(lines[idx:]))
    except StopIteration:
        print("no lock section")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
