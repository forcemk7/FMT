#!/usr/bin/env python3
"""Probe whether 01 00 6c 07 + year_u16 encodes DOB near person doubles."""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-mark-year.txt"
MARK = bytes.fromhex("01006c07")
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


def score(mm: mmap.mmap, dab: int) -> int:
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


def best(mm: mmap.mmap, uid: int) -> int | None:
    ds = doubles(mm, uid)
    return sorted(ds, key=lambda d: (-score(mm, d), d))[0] if ds else None


def effective_mark(blob: bytes) -> int | None:
    j = blob.find(MARK)
    if j < 0:
        return None
    # some records store the type tag twice back-to-back
    if blob[j + 4 : j + 8] == MARK:
        return j + 4
    return j


def main() -> None:
    lines: list[str] = []
    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            lines.append("=== mark+year_u16 near best double (±8KB) ===")
            rel_hits: Counter[int] = Counter()
            found = 0
            for p in PLAYERS:
                y = int(p["dob"][:4])
                dab = best(mm, int(p["uid"]))
                if dab is None:
                    continue
                pat = MARK + struct.pack("<H", y)
                lo = max(0, dab - 8192)
                hi = min(len(mm), dab + 8192)
                win = bytes(mm[lo:hi])
                rel0 = dab - lo
                offs: list[int] = []
                start = 0
                while True:
                    i = win.find(pat, start)
                    if i < 0:
                        break
                    offs.append(i - rel0)
                    start = i + 1
                if offs:
                    found += 1
                    for o in offs:
                        rel_hits[o] += 1
                    lines.append(f"  {p['name']} y={y} offs={offs[:8]}")
                else:
                    lines.append(f"  {p['name']} y={y} NO mark+year")
            lines.append(f"players with mark+year: {found}/{len(PLAYERS)}")
            lines.append(f"top rels: {rel_hits.most_common(10)}")

            lines.append("")
            lines.append("=== after effective mark: year / month / day positions ===")
            year_at: Counter[int] = Counter()
            month_at: Counter[int] = Counter()
            day_at: Counter[int] = Counter()
            for p in PLAYERS:
                y, m, d = map(int, p["dob"].split("-"))
                dab = best(mm, int(p["uid"]))
                if dab is None:
                    continue
                blob = bytes(mm[dab : dab + 1024])
                em = effective_mark(blob)
                if em is None:
                    lines.append(f"  {p['name']}: no mark in +1KB")
                    continue
                trail = blob[em : em + 64]
                ypos = [
                    i
                    for i in range(0, len(trail) - 1)
                    if struct.unpack_from("<H", trail, i)[0] == y
                ]
                mpos = [i for i, b in enumerate(trail) if b == m]
                dpos = [i for i, b in enumerate(trail) if b == d]
                for i in ypos:
                    year_at[i] += 1
                for i in mpos:
                    month_at[i] += 1
                for i in dpos:
                    day_at[i] += 1
                lines.append(
                    f"  {p['name']} em@{em} year@{ypos[:6]} month@{mpos[:8]} day@{dpos[:8]} "
                    f"head={trail[:24].hex(' ')}"
                )

            lines.append("")
            lines.append("year_u16 offset consensus after mark:")
            for off, n in year_at.most_common(10):
                lines.append(f"  +{off}: {n}/{len(PLAYERS)}")
            lines.append("month_u8 offset consensus after mark:")
            for off, n in month_at.most_common(10):
                lines.append(f"  +{off}: {n}/{len(PLAYERS)}")
            lines.append("day_u8 offset consensus after mark:")
            for off, n in day_at.most_common(10):
                lines.append(f"  +{off}: {n}/{len(PLAYERS)}")

            # Layout attempts: mark | year | month | day variants
            lines.append("")
            lines.append("=== layout match rates (after effective mark) ===")
            layouts = {
                "HBB_ymd": lambda t, y, m, d: struct.unpack_from("<HBB", t, 4) == (y, m, d),
                "HBB_ydm": lambda t, y, m, d: struct.unpack_from("<HBB", t, 4) == (y, d, m),
                "BBH_dmy": lambda t, y, m, d: struct.unpack_from("<BBH", t, 4) == (d, m, y),
                "BBH_mdy": lambda t, y, m, d: struct.unpack_from("<BBH", t, 4) == (m, d, y),
                "HHH_ymd": lambda t, y, m, d: struct.unpack_from("<HHH", t, 4) == (y, m, d),
                "H_year_only": lambda t, y, m, d: struct.unpack_from("<H", t, 4)[0] == y,
                # skip repeating mark: data starts at +8 if double tag already folded
                "at0_HBB_ymd": lambda t, y, m, d: struct.unpack_from("<HBB", t, 0) == (y, m, d)
                if False
                else struct.unpack_from("<H", t, 4)[0] == y
                and t[6] == m
                and t[7] == d,
            }
            # redefine cleanly
            def check(name: str, fn) -> None:
                ok = 0
                for p in PLAYERS:
                    y, m, d = map(int, p["dob"].split("-"))
                    dab = best(mm, int(p["uid"]))
                    if dab is None:
                        continue
                    blob = bytes(mm[dab : dab + 1024])
                    em = effective_mark(blob)
                    if em is None:
                        continue
                    trail = blob[em:]
                    try:
                        if fn(trail, y, m, d):
                            ok += 1
                    except struct.error:
                        pass
                lines.append(f"  {name}: {ok}/{len(PLAYERS)}")

            check(
                "mark+4 HBB ymd",
                lambda t, y, m, d: len(t) >= 8
                and struct.unpack_from("<HBB", t, 4) == (y, m, d),
            )
            check(
                "mark+4 HHH ymd",
                lambda t, y, m, d: len(t) >= 10
                and struct.unpack_from("<HHH", t, 4) == (y, m, d),
            )
            check(
                "mark+4 year only",
                lambda t, y, m, d: len(t) >= 6
                and struct.unpack_from("<H", t, 4)[0] == y,
            )
            check(
                "mark+4 BBH dmy",
                lambda t, y, m, d: len(t) >= 8
                and struct.unpack_from("<BBH", t, 4) == (d, m, y),
            )
            check(
                "anywhere in +64: HBB ymd",
                lambda t, y, m, d: any(
                    struct.unpack_from("<HBB", t, i) == (y, m, d)
                    for i in range(0, min(60, len(t) - 4))
                ),
            )
            check(
                "anywhere in +64: BBH dmy",
                lambda t, y, m, d: any(
                    struct.unpack_from("<BBH", t, i) == (d, m, y)
                    for i in range(0, min(60, len(t) - 4))
                ),
            )

            # Whole-head: how often does mark+year exist at all for each DOB year?
            lines.append("")
            lines.append("=== whole-head mark+year existence (first 512MB) ===")
            for p in PLAYERS[:8]:
                y = int(p["dob"][:4])
                pat = MARK + struct.pack("<H", y)
                count = 0
                j = 0
                end = min(len(mm), PERSON_HEAD)
                while count < 5:
                    j = mm.find(pat, j, end)
                    if j < 0:
                        break
                    count += 1
                    j += 1
                # also with month day after year
                m = int(p["dob"][5:7])
                d = int(p["dob"][8:10])
                pat2 = MARK + struct.pack("<HBB", y, m, d)
                j = mm.find(pat2, 0, end)
                lines.append(
                    f"  {p['name']} mark+year hits>={count} mark+ymd_abs={j}"
                )

            # Game date style from earlier probe: 01 00 6c 07 f7 07
            lines.append("")
            lines.append("=== global date-like mark+year samples for 2039 and a DOB year ===")
            for y in (2039, 2015, 2005, 2019):
                pat = MARK + struct.pack("<H", y)
                j = 0
                shown = 0
                while shown < 5:
                    j = mm.find(pat, j, min(len(mm), 8 * 1024 * 1024))
                    if j < 0:
                        break
                    ctx = bytes(mm[j : j + 16])
                    lines.append(f"  y={y} @{j}: {ctx.hex(' ')}")
                    shown += 1
                    j += 1
        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
