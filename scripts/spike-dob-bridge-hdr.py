#!/usr/bin/env python3
"""
Follow the 4-byte header sitting just before mark+days DOB layout.

Layout observed:
  [hdr 4B] 00 01 00 6c 07  01 00 6c 07  DAYS_u32  [often ffffffff]

Test whether hdr (or nearby ids after DOB) also appears near the person double-UID.
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
OUT = ROOT / "tmp" / "fm-spike" / "dob-bridge-hdr.txt"
MARK = bytes.fromhex("01006c07")
PRE = bytes.fromhex("0001006c07")
EPOCH = date(1900, 1, 1)
PERSON_HEAD = 512 * 1024 * 1024
RADII = (64, 256, 1024, 4096, 16384, 65536, 262144, 1_048_576)


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


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 80) -> list[int]:
    hits: list[int] = []
    j = mm.find(needle)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(needle, j + 1)
    return hits


def near(hits: list[int], center: int | None) -> tuple[int | None, int | None]:
    if center is None or not hits:
        return None, None
    h = min(hits, key=lambda x: abs(x - center))
    return h, h - center


def main() -> None:
    lines: list[str] = []
    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            rows = []
            for p in PLAYERS:
                dob = date(*map(int, p["dob"].split("-")))
                days = (dob - EPOCH).days
                uid = int(p["uid"])
                dab = best_double(mm, uid)
                needle = MARK + struct.pack("<I", days)
                sites = find_all(mm, needle, limit=8)
                site = sites[0] if sites else None
                hdr = None
                pre_ok = False
                trail = None
                trail2 = None
                if site is not None and site >= 9:
                    # Prefer PRE immediately before MARK
                    if bytes(mm[site - 5 : site]) == PRE:
                        pre_ok = True
                        hdr = bytes(mm[site - 9 : site - 5])
                    else:
                        # Müller-like: sometimes an extra byte before PRE
                        for back in range(5, 16):
                            if site - back - 4 >= 0 and bytes(mm[site - back : site - back + 5]) == PRE:
                                pre_ok = True
                                hdr = bytes(mm[site - back - 4 : site - back])
                                break
                        if hdr is None and site >= 4:
                            hdr = bytes(mm[site - 4 : site])
                    # After days: skip optional ffff / second markoids, grab next interesting u32s
                    off = site + 8
                    trail_vals = []
                    for _ in range(8):
                        if off + 4 > len(mm):
                            break
                        v = struct.unpack_from("<I", mm, off)[0]
                        trail_vals.append((off, v, bytes(mm[off : off + 4])))
                        off += 4
                    trail = trail_vals
                rows.append(
                    {
                        "name": p["name"],
                        "uid": uid,
                        "days": days,
                        "dab": dab,
                        "site": site,
                        "hdr": hdr,
                        "pre_ok": pre_ok,
                        "trail": trail,
                    }
                )

            lines.append("## headers before PRE+MARK+days")
            for r in rows:
                hx = r["hdr"].hex() if r["hdr"] else None
                lines.append(
                    f"  {r['name']}: pre_ok={r['pre_ok']} hdr={hx} site={r['site']} dab={r['dab']}"
                )

            # A: does header appear near dab?
            lines.append("\n## A: hdr token vs dab proximity")
            hist = Counter()
            for r in rows:
                if not r["hdr"] or r["dab"] is None:
                    continue
                hits = find_all(mm, r["hdr"], limit=200)
                # exclude the DOB-site header itself
                hits = [h for h in hits if r["site"] is None or abs(h - r["site"]) > 32]
                best_rad = None
                best_d = None
                for h in hits:
                    d = abs(h - r["dab"])
                    for rad in RADII:
                        if d <= rad and (best_rad is None or rad < best_rad):
                            best_rad = rad
                            best_d = h - r["dab"]
                if best_rad is not None:
                    hist[best_rad] += 1
                lines.append(
                    f"  {r['name']}: hdr={r['hdr'].hex()} hits={len(hits)} "
                    f"near_dab_within={best_rad} delta={best_d}"
                )
            lines.append(f"hdr→dab radius hist: {dict(hist)}")

            # B: trail tokens (non ffff / non zero / non tiny) near dab
            lines.append("\n## B: DOB-site trail u32s near dab")
            trail_hist = Counter()
            for r in rows:
                if r["dab"] is None or not r["trail"]:
                    continue
                found = []
                for off, v, raw in r["trail"]:
                    if v in (0, 0xFFFFFFFF) or v < 256:
                        continue
                    if raw == MARK:
                        continue
                    hits = find_all(mm, raw, limit=120)
                    hits = [h for h in hits if abs(h - off) > 16]
                    best_rad = None
                    best_d = None
                    for h in hits:
                        d = abs(h - r["dab"])
                        for rad in RADII:
                            if d <= rad and (best_rad is None or rad < best_rad):
                                best_rad = rad
                                best_d = h - r["dab"]
                    if best_rad is not None:
                        found.append((raw.hex(), best_rad, best_d, v))
                        trail_hist[best_rad] += 1
                lines.append(f"  {r['name']}: {found[:6]}")
            lines.append(f"trail→dab radius hist: {dict(trail_hist)}")

            # C: decode hdr as potential TCM / packed forms; compare across players
            lines.append("\n## C: hdr decode attempts")
            for r in rows:
                if not r["hdr"]:
                    continue
                u32 = struct.unpack("<I", r["hdr"])[0]
                b0, b1, b2, b3 = r["hdr"]
                lines.append(
                    f"  {r['name']}: u32={u32} bytes={list(r['hdr'])} "
                    f"u16le={struct.unpack('<H', r['hdr'][:2])[0]},"
                    f"{struct.unpack('<H', r['hdr'][2:])[0]}"
                )

            # D: is hdr unique in the file? (good key if unique)
            lines.append("\n## D: hdr uniqueness / collision with other players")
            for r in rows:
                if not r["hdr"]:
                    continue
                hits = find_all(mm, r["hdr"], limit=50)
                lines.append(f"  {r['name']}: hdr={r['hdr'].hex()} absolute_hits={len(hits)}")

            # E: search from dab for PRE+MARK layout and read days — any age match in ±2MB?
            lines.append("\n## E: PRE+MARK+days near dab (±2MB) age match?")
            game = date(2039, 7, 1)
            age_match = 0
            for r in rows:
                if r["dab"] is None:
                    continue
                lo = max(0, r["dab"] - 2_000_000)
                hi = min(len(mm), r["dab"] + 2_000_000)
                # search PRE+MARK in window
                window = bytes(mm[lo:hi])
                needle = PRE + MARK
                matches = []
                start = 0
                while True:
                    j = window.find(needle, start)
                    if j < 0:
                        break
                    abs_j = lo + j
                    days_off = abs_j + len(needle)
                    if days_off + 4 <= len(mm):
                        days = struct.unpack_from("<I", mm, days_off)[0]
                        if 30_000 <= days <= 46_000:
                            dob = EPOCH + __import__("datetime").timedelta(days=days)
                            age = game.year - dob.year - (
                                (game.month, game.day) < (dob.month, dob.day)
                            )
                            matches.append((abs_j - r["dab"], days, dob.isoformat(), age))
                    start = j + 1
                    if len(matches) >= 12:
                        break
                # expected age from fixture
                exp = next(p for p in PLAYERS if int(p["uid"]) == r["uid"])["age"]
                hit = [m for m in matches if m[3] == exp or m[1] == r["days"]]
                if hit:
                    age_match += 1
                lines.append(
                    f"  {r['name']}: exp_age={exp} cand={matches[:5]} age_or_days_hit={bool(hit)}"
                )
            lines.append(f"age/days hits near dab (±2MB PRE+MARK): {age_match}/{len(rows)}")

            # F: full-file scan — for each PRE+MARK+days birth-ish unique day, try linking via hdr uniqueness
            lines.append("\n## F: index all PRE+MARK+days; hdr→known player recovery")
            indexed = []
            j = 0
            # scan by finding PRE+MARK (more precise than MARK alone)
            needle = PRE + MARK
            while True:
                j = mm.find(needle, j)
                if j < 0:
                    break
                days_off = j + len(needle)
                if days_off + 4 <= len(mm) and j >= 4:
                    days = struct.unpack_from("<I", mm, days_off)[0]
                    if 30_000 <= days <= 46_000:
                        hdr = bytes(mm[j - 4 : j])
                        indexed.append((j, days, hdr))
                j += 1
                if len(indexed) > 5000:
                    break
            lines.append(f"indexed PRE+MARK birth-ish: {len(indexed)}")
            # How many known DOBs recovered uniquely by days?
            by_days: dict[int, list[tuple[int, bytes]]] = defaultdict(list)
            for abs_j, days, hdr in indexed:
                by_days[days].append((abs_j, hdr))
            recovered = 0
            unique_days = 0
            for r in rows:
                sites = by_days.get(r["days"], [])
                if len(sites) == 1:
                    unique_days += 1
                if any(s[0] + 5 == r["site"] or abs(s[0] - (r["site"] or -1)) < 16 for s in sites):
                    recovered += 1
            lines.append(f"known DOBs with unique PRE+MARK days among index: {unique_days}")
            lines.append(f"known DOB sites present in PRE+MARK index: {recovered}")

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Avoid Windows console encoding issues
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
