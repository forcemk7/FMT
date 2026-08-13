#!/usr/bin/env python3
"""
Lock DOB as days_y1900 immediately after 01 00 6c 07, then link to players.
Also finalize gameDate heuristic (twin-after / consecutive days).
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-mark-days-lock.txt"
MARK = bytes.fromhex("01006c07")
EPOCH = date(1900, 1, 1)
GAME = date(2039, 7, 1)
PERSON_HEAD = 512 * 1024 * 1024


def doubles(mm: mmap.mmap, uid: int) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(mm), PERSON_HEAD)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 16:
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


def main() -> None:
    lines: list[str] = []
    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # Index: for each known DOB days, find mark+(optional repeat)+days layouts
            layouts = {
                "mark4_days": lambda trail, days_le: trail[0:4] == days_le,
                "mark8_days": lambda trail, days_le: trail[0:4] == MARK
                and trail[4:8] == days_le,  # after double mark (trail starts after first)
                "mark4_days_ffff": lambda trail, days_le: trail[0:4] == days_le
                and trail[4:8] == b"\xff\xff\xff\xff",
            }

            lines.append("## mark→days layout match for known DOBs")
            for layout_name, prefix_extra in (
                ("mark+days", b""),
                ("mark+days+ffff", b"\xff\xff\xff\xff"),
                ("mark+mark+days", MARK),  # first mark consumed by find
            ):
                ok = 0
                for p in PLAYERS:
                    days = (date(*map(int, p["dob"].split("-"))) - EPOCH).days
                    days_le = struct.pack("<I", days)
                    if layout_name == "mark+mark+days":
                        needle = MARK + MARK + days_le
                    else:
                        needle = MARK + days_le + prefix_extra
                    if mm.find(needle) >= 0:
                        ok += 1
                lines.append(f"  {layout_name}: {ok}/{len(PLAYERS)}")

            # Better: find all mark+days_ffff sites for each DOB, measure distance to uid double
            lines.append("\n## mark+days(+ffff) sites vs best double")
            rel_hist: Counter[int] = Counter()
            linked = 0
            for p in PLAYERS:
                dob = date(*map(int, p["dob"].split("-")))
                days = (dob - EPOCH).days
                days_le = struct.pack("<I", days)
                uid = int(p["uid"])
                dab = best_double(mm, uid)
                if dab is None:
                    lines.append(f"  {p['name']}: no double")
                    continue
                # Prefer mark + days + ffff
                needle = MARK + days_le + b"\xff\xff\xff\xff"
                sites: list[int] = []
                j = mm.find(needle)
                while j >= 0 and len(sites) < 50:
                    sites.append(j)
                    j = mm.find(needle, j + 1)
                if not sites:
                    # fallback mark + days (no ffff)
                    needle2 = MARK + days_le
                    j = mm.find(needle2)
                    while j >= 0 and len(sites) < 50:
                        sites.append(j)
                        j = mm.find(needle2, j + 1)
                if not sites:
                    lines.append(f"  {p['name']}: no mark+days sites")
                    continue
                sites.sort(key=lambda s: abs(s - dab))
                best = sites[0]
                delta = best - dab
                linked += 1
                # also check uid within ±2KB of this mark site
                uid_pat = struct.pack("<I", uid)
                near_uid = False
                lo = max(0, best - 2048)
                hi = min(len(mm), best + 2048)
                if uid_pat in bytes(mm[lo:hi]):
                    near_uid = True
                pi = None
                if len(bytes(mm[dab : dab + 35])) >= 35:
                    pi = struct.unpack_from("<I", mm, dab + 31)[0]
                near_pi = False
                if pi and 0 < pi < 200_000:
                    if struct.pack("<I", pi) in bytes(mm[lo:hi]):
                        near_pi = True
                lines.append(
                    f"  {p['name']}: sites={len(sites)} nearest_delta={delta:+d} "
                    f"near_uid={near_uid} near_pi={near_pi} "
                    f"ctx={bytes(mm[best : best + 20]).hex(' ')}"
                )
                if abs(delta) <= 65536:
                    rel_hist[delta] += 1

            lines.append(f"\nlinked={linked}/{len(PLAYERS)}")
            lines.append("shared nearest deltas within 64k:")
            for d, n in rel_hist.most_common(20):
                lines.append(f"  {d:+d}: {n}")

            # Link strategy: dob mark site that also contains uid nearby
            lines.append("\n## prefer mark+days site with uid in ±2KB")
            ok_uid_link = 0
            for p in PLAYERS:
                dob = date(*map(int, p["dob"].split("-")))
                days = (dob - EPOCH).days
                days_le = struct.pack("<I", days)
                uid = int(p["uid"])
                uid_pat = struct.pack("<I", uid)
                needle = MARK + days_le
                sites: list[int] = []
                j = mm.find(needle)
                while j >= 0 and len(sites) < 80:
                    sites.append(j)
                    j = mm.find(needle, j + 1)
                hits = []
                for s in sites:
                    lo = max(0, s - 2048)
                    hi = min(len(mm), s + 2048)
                    win = bytes(mm[lo:hi])
                    if uid_pat in win:
                        # relative position of uid to mark
                        uoff = win.find(uid_pat)
                        hits.append((s, uoff - (s - lo)))
                if hits:
                    ok_uid_link += 1
                    lines.append(f"  {p['name']}: uid_linked_sites={len(hits)} sample={hits[:4]}")
                else:
                    lines.append(f"  {p['name']}: NO uid-linked mark+days (sites={len(sites)})")
            lines.append(f"uid-linked: {ok_uid_link}/{len(PLAYERS)}")

            # gameDate finalize — aligned scan (much faster)
            lines.append("\n## gameDate twin-after heuristic in first 16MB (aligned)")
            early = min(len(mm), 16 * 1024 * 1024)
            by_date: dict[str, int] = defaultdict(int)
            for off in range(0, early - 12, 4):
                days = struct.unpack_from("<I", mm, off)[0]
                if not (45000 <= days <= 56000):
                    continue
                try:
                    dt = EPOCH + timedelta(days=days)
                except Exception:
                    continue
                if not (2024 <= dt.year <= 2045):
                    continue
                a = struct.unpack_from("<I", mm, off + 4)[0]
                b = struct.unpack_from("<I", mm, off + 8)[0]
                twin = a == b and a > 0
                consec = False
                if off >= 4:
                    prev = struct.unpack_from("<I", mm, off - 4)[0]
                    consec = prev in (days - 1, days + 1)
                score = (3 if twin else 0) + (2 if consec else 0)
                if score:
                    by_date[dt.isoformat()] += score
            lines.append("top scored dates:")
            for d, s in sorted(by_date.items(), key=lambda x: -x[1])[:20]:
                lines.append(f"  {d}: score={s}")
            lines.append(
                f"expected GAME={GAME.isoformat()} score={by_date.get(GAME.isoformat(), 0)}"
            )

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
