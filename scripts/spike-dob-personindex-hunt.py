#!/usr/bin/env python3
"""Hunt DOB near personIndex-tagged 6c07 records; validate gameDate days_y1900."""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-personindex-hunt.txt"
MARK = bytes.fromhex("01006c07")
EPOCH = date(1900, 1, 1)
GAME = date(2039, 7, 1)
PERSON_HEAD = 512 * 1024 * 1024


def doubles(mm: mmap.mmap, uid: int) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(mm), PERSON_HEAD)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 12:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def best_double(mm: mmap.mmap, uid: int) -> int | None:
    ds = doubles(mm, uid)
    if not ds:
        return None

    def score(dab: int) -> int:
        blob = bytes(mm[dab : dab + 160])
        s = 0
        if b"\x01\x01\x01" in blob[8:120]:
            s += 5
        if MARK in blob:
            s += 3
        if len(blob) >= 35:
            pi = struct.unpack_from("<I", blob, 31)[0]
            if 0 < pi < 200_000:
                s += 4
        return s

    return sorted(ds, key=lambda d: (-score(d), d))[0]


def person_index_from_double(mm: mmap.mmap, dab: int) -> int | None:
    blob = bytes(mm[dab : dab + 64])
    if len(blob) < 35:
        return None
    pi = struct.unpack_from("<I", blob, 31)[0]
    if 0 < pi < 200_000:
        return pi
    return None


def main() -> None:
    lines: list[str] = []
    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # --- gameDate: score early days candidates ---
            lines.append("## gameDate candidates in first 8MB")
            early_n = min(len(mm), 8 * 1024 * 1024)
            game_days = (GAME - EPOCH).days
            pat = struct.pack("<I", game_days)
            hits = []
            j = mm.find(pat, 0, early_n)
            while j >= 0:
                hits.append(j)
                j = mm.find(pat, j + 1, early_n)
            lines.append(f"  2039-07-01 days_y1900={game_days} early_hits={len(hits)}")
            for h in hits[:12]:
                ctx = bytes(mm[max(0, h - 24) : h + 32])
                twin = (
                    h + 4 + 4 <= len(mm)
                    and struct.unpack_from("<I", mm, h + 4)[0]
                    == struct.unpack_from("<I", mm, h + 8)[0]
                    if False
                    else False
                )
                # twin after days?
                twin_after = False
                if h + 12 <= len(mm):
                    a = struct.unpack_from("<I", mm, h + 4)[0]
                    b = struct.unpack_from("<I", mm, h + 8)[0]
                    twin_after = a == b and a != 0
                mark_near = MARK in bytes(mm[max(0, h - 64) : h + 64])
                lines.append(
                    f"  @{h} twin_after={twin_after} mark_near={mark_near} "
                    f"ctx={ctx.hex(' ')}"
                )

            # Broader: all days_u32 in early that decode to 2024-2045
            cand: Counter[str] = Counter()
            for off in range(0, early_n - 4, 1):
                # too slow — sample every occurrence of plausible high days via sliding sparse
                pass
            # denser: scan u32 alignment only
            for off in range(0, early_n - 4, 4):
                val = struct.unpack_from("<I", mm, off)[0]
                if not (45000 <= val <= 53000):
                    continue
                try:
                    dt = EPOCH + timedelta(days=val)
                except Exception:
                    continue
                if 2024 <= dt.year <= 2045:
                    cand[dt.isoformat()] += 1
            lines.append("  plausible career dates (aligned u32, 45k-53k days):")
            for d, n in cand.most_common(15):
                lines.append(f"    {d}: {n}")

            # --- DOB near mark+personIndex ---
            lines.append("\n## DOB days near mark+personIndex records")
            ok_rel: Counter[int] = Counter()
            players_ok = 0
            for p in PLAYERS:
                uid = int(p["uid"])
                dob = date(*map(int, p["dob"].split("-")))
                days = (dob - EPOCH).days
                dab = best_double(mm, uid)
                if dab is None:
                    lines.append(f"  {p['name']}: no double")
                    continue
                pi = person_index_from_double(mm, dab)
                if pi is None:
                    lines.append(f"  {p['name']}: no personIndex @+31")
                    continue
                needle = MARK + struct.pack("<I", pi)
                # collect mark+pi hits (cap)
                locs: list[int] = []
                j = mm.find(needle, 0, min(len(mm), PERSON_HEAD))
                while j >= 0 and len(locs) < 40:
                    locs.append(j)
                    j = mm.find(needle, j + 1, min(len(mm), PERSON_HEAD))
                dob_pat = struct.pack("<I", days)
                found_rel: list[tuple[int, int]] = []  # (mark_abs, rel)
                for loc in locs:
                    lo = max(0, loc - 128)
                    hi = min(len(mm), loc + 256)
                    win = bytes(mm[lo:hi])
                    rel0 = loc - lo
                    start = 0
                    while True:
                        i = win.find(dob_pat, start)
                        if i < 0:
                            break
                        found_rel.append((loc, i - rel0))
                        start = i + 1
                if found_rel:
                    players_ok += 1
                    for loc, rel in found_rel[:6]:
                        ok_rel[rel] += 1
                    lines.append(
                        f"  {p['name']} pi={pi} days={days} "
                        f"mark+pi_hits={len(locs)} dob_near={found_rel[:6]}"
                    )
                else:
                    # nearest days anywhere to any mark+pi
                    all_days: list[int] = []
                    j = mm.find(dob_pat)
                    while j >= 0 and len(all_days) < 300:
                        all_days.append(j)
                        j = mm.find(dob_pat, j + 1)
                    best_pair = None
                    for loc in locs:
                        for dabs in all_days:
                            dist = abs(dabs - loc)
                            if best_pair is None or dist < best_pair[0]:
                                best_pair = (dist, dabs - loc, loc, dabs)
                    lines.append(
                        f"  {p['name']} pi={pi} days={days} mark+pi={len(locs)} "
                        f"NO dob within ±128/256 nearest={best_pair}"
                    )

            lines.append(f"\nplayers with dob near mark+pi: {players_ok}/{len(PLAYERS)}")
            lines.append("shared rel to mark+pi (dob days_u32):")
            for rel, n in ok_rel.most_common(20):
                lines.append(f"  rel={rel:+d}: {n}")

            # --- DOB days nearest to best double ---
            lines.append("\n## nearest days_y1900 to best double")
            for p in PLAYERS:
                uid = int(p["uid"])
                dob = date(*map(int, p["dob"].split("-")))
                days = (dob - EPOCH).days
                dab = best_double(mm, uid)
                if dab is None:
                    continue
                pat = struct.pack("<I", days)
                hits: list[int] = []
                j = mm.find(pat)
                while j >= 0 and len(hits) < 400:
                    hits.append(j)
                    j = mm.find(pat, j + 1)
                if not hits:
                    lines.append(f"  {p['name']}: no days hits")
                    continue
                hits.sort(key=lambda h: abs(h - dab))
                h = hits[0]
                ctx = bytes(mm[max(0, h - 12) : h + 20])
                lines.append(
                    f"  {p['name']}: delta={h - dab:+d} absdelta={abs(h - dab)} "
                    f"ctx={ctx.hex(' ')}"
                )

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
