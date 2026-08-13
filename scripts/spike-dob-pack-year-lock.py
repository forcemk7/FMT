#!/usr/bin/env python3
"""Lock personality-pack-19 as birth year; hunt month/day / day-of-year beside it."""

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
EXTRACT = json.loads(
    (ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json").read_text(encoding="utf-8-sig")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-pack-year-lock.txt"
EPOCH = date(1900, 1, 1)
GAME = date(2039, 7, 1)


def main() -> None:
    lines: list[str] = []
    by_uid = {int(p["uid"]): p for p in EXTRACT.get("players") or []}

    with (ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin").open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            year_ok = 0
            have_pack = 0
            lines.append("## pack-19 as year_u16 vs fixture DOB year")
            windows: list[tuple[str, date, int, bytes]] = []
            for p in PLAYERS:
                uid = int(p["uid"])
                dob = date(*map(int, p["dob"].split("-")))
                ex = by_uid.get(uid, {})
                pack = ex.get("personalityPackAbs")
                dab = ex.get("doubleUidAbs")
                if pack is None:
                    lines.append(f"  {p['name']}: NO pack")
                    continue
                have_pack += 1
                off = int(pack) - 19
                y = struct.unpack_from("<H", mm, off)[0]
                ok = y == dob.year
                if ok:
                    year_ok += 1
                lines.append(
                    f"  {p['name']}: pack={pack} y@-19={y} dob_year={dob.year} "
                    f"ok={ok} dab={dab} dab-pack={(dab - pack) if dab else None}"
                )
                # capture ±32 around pack-19
                lo = off - 32
                hi = off + 48
                windows.append((p["name"], dob, off, bytes(mm[lo:hi])))

            lines.append(f"year lock: {year_ok}/{have_pack} (players with pack)")

            # Month / day / doy consensus relative to year field
            lines.append("\n## fields near year (rel to year abs)")
            month_hits: Counter[int] = Counter()
            day_hits: Counter[int] = Counter()
            doy_hits: Counter[int] = Counter()
            days_hits: Counter[int] = Counter()
            md_u16_hits: Counter[int] = Counter()
            for name, dob, year_abs, blob in windows:
                base = 32  # year at index 32 in blob
                # month u8
                for i, b in enumerate(blob):
                    rel = i - base
                    if b == dob.month:
                        month_hits[rel] += 1
                    if b == dob.day:
                        day_hits[rel] += 1
                doy = dob.timetuple().tm_yday
                days = (dob - EPOCH).days
                for i in range(0, len(blob) - 1):
                    rel = i - base
                    v = struct.unpack_from("<H", blob, i)[0]
                    if v == doy:
                        doy_hits[rel] += 1
                    if v == days & 0xFFFF:
                        days_hits[rel] += 1
                    if v == (dob.month << 8) | dob.day or v == (dob.day << 8) | dob.month:
                        md_u16_hits[rel] += 1
                    packed = dob.day + (dob.month << 5) + ((dob.year - 1900) << 9)
                    if v == packed:
                        md_u16_hits[rel + 1000] += 1  # tag packed separately
                _ = None

            lines.append(f"month_u8 top: {month_hits.most_common(12)}")
            lines.append(f"day_u8 top: {day_hits.most_common(12)}")
            lines.append(f"doy_u16 top: {doy_hits.most_common(12)}")
            lines.append(f"days_u16 top: {days_hits.most_common(12)}")
            lines.append(f"md/packed_u16 top: {md_u16_hits.most_common(12)}")

            # Dump hex around year for a few
            lines.append("\n## hex around year field (year at +0)")
            for name, dob, year_abs, blob in windows[:8]:
                lines.append(f"  {name} dob={dob.isoformat()} year_abs={year_abs}")
                # show with year centered
                for i in range(0, len(blob), 16):
                    chunk = blob[i : i + 16]
                    rel = i - 32
                    mark = " <<<" if rel == 0 else ""
                    lines.append(f"    {rel:+4d} {chunk.hex(' ')}{mark}")

            # Also check dab-relative year for players without pack
            lines.append("\n## players without pack: year_u16 near dab?")
            for p in PLAYERS:
                uid = int(p["uid"])
                dob = date(*map(int, p["dob"].split("-")))
                ex = by_uid.get(uid, {})
                if ex.get("personalityPackAbs") is not None:
                    continue
                dab = ex.get("doubleUidAbs")
                if dab is None:
                    lines.append(f"  {p['name']}: no dab")
                    continue
                pat = struct.pack("<H", dob.year)
                lo = max(0, dab - 2048)
                hi = min(len(mm), dab + 2048)
                window = bytes(mm[lo:hi])
                rels = []
                start = 0
                while True:
                    j = window.find(pat, start)
                    if j < 0:
                        break
                    rels.append(lo + j - dab)
                    start = j + 1
                lines.append(f"  {p['name']}: dab={dab} year_rels={rels[:12]}")

            # Age from year-only for mentoring gate
            lines.append("\n## mentoring age from year-only (game=2039-07-01)")
            # age_floor = game.year - birth_year - 1; age_ceil = game.year - birth_year
            under24_exact = 0
            under24_safe = 0  # use ceil so we don't miss young players
            for p in PLAYERS:
                uid = int(p["uid"])
                dob = date(*map(int, p["dob"].split("-")))
                age = int(p["age"])
                ex = by_uid.get(uid, {})
                pack = ex.get("personalityPackAbs")
                if pack is None:
                    continue
                y = struct.unpack_from("<H", mm, int(pack) - 19)[0]
                age_ceil = GAME.year - y
                age_floor = age_ceil - 1
                exact = age < 24
                safe = age_ceil < 24 or (age_ceil == 24 and True)  # include possibles
                # Better: if age_floor < 24 include (might include some 24s)
                include = age_floor < 24
                if exact == (age < 24):
                    under24_exact += 1
                if include == (age < 24) or (include and age == 24):
                    under24_safe += 1
                lines.append(
                    f"  {p['name']}: real_age={age} year={y} floor={age_floor} "
                    f"ceil={age_ceil} include_if_floor<24={include}"
                )

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
