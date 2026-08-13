#!/usr/bin/env python3
"""Hunt CM0102-style TCMDate (dayOfYear + year) and mark+year for DOB."""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-tcmdate-hunt.txt"
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


def tcm_patterns(dob: date) -> dict[str, bytes]:
    yday0 = dob.timetuple().tm_yday - 1  # CM style
    yday1 = dob.timetuple().tm_yday
    leap = 1 if (dob.year % 4 == 0 and (dob.year % 100 != 0 or dob.year % 400 == 0)) else 0
    return {
        "tcm_d0_y_leapI": struct.pack("<hhi", yday0, dob.year, leap),
        "tcm_d1_y_leapI": struct.pack("<hhi", yday1, dob.year, leap),
        "tcm_d0_y_leapH": struct.pack("<hhh", yday0, dob.year, leap),
        "tcm_d1_y_leapH": struct.pack("<hhh", yday1, dob.year, leap),
        "tcm_y_d0": struct.pack("<hh", dob.year, yday0),
        "tcm_y_d1": struct.pack("<hh", dob.year, yday1),
        "tcm_d0_y": struct.pack("<hh", yday0, dob.year),
        "tcm_d1_y": struct.pack("<hh", yday1, dob.year),
        "mark_tcm_d0_y": MARK + struct.pack("<hh", yday0, dob.year),
        "mark_tcm_y_d0": MARK + struct.pack("<hh", dob.year, yday0),
        "mark_year": MARK + struct.pack("<H", dob.year),
        "mark_year_md": MARK + struct.pack("<HBB", dob.year, dob.month, dob.day),
    }


def scan_rel(win: bytes, rel0: int, pat: bytes) -> list[int]:
    outs: list[int] = []
    start = 0
    while True:
        i = win.find(pat, start)
        if i < 0:
            break
        outs.append(i - rel0)
        start = i + 1
    return outs


def main() -> None:
    lines: list[str] = []
    by_pat: dict[str, dict[str, set[int]]] = {k: {} for k in next(iter([
        tcm_patterns(date(2000, 1, 1))
    ])).keys()}

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                y, m, d = map(int, p["dob"].split("-"))
                dob = date(y, m, d)
                dab = best(mm, int(p["uid"]))
                if dab is None:
                    lines.append(f"## {p['name']}: no double")
                    continue
                lo = max(0, dab - 8192)
                hi = min(len(mm), dab + 8192)
                win = bytes(mm[lo:hi])
                rel0 = dab - lo
                pats = tcm_patterns(dob)
                lines.append(
                    f"## {p['name']} dob={dob} yday={dob.timetuple().tm_yday} "
                    f"best={dab}"
                )
                any_hit = False
                for name, pat in pats.items():
                    offs = scan_rel(win, rel0, pat)
                    if offs:
                        any_hit = True
                        by_pat.setdefault(name, {})[p["name"]] = set(offs)
                        lines.append(f"  {name}: {offs[:12]}")
                if not any_hit:
                    lines.append("  (no TCM/mark-year patterns in ±8KB)")

            lines.append("\n## consensus (≥70% of players hitting pattern, shared/majority offset)")
            n = len(PLAYERS)
            for name, per in sorted(by_pat.items()):
                if len(per) < max(5, int(0.5 * n)):
                    continue
                ctr: Counter[int] = Counter()
                for s in per.values():
                    ctr.update(s)
                need = max(5, int(0.7 * len(per)))
                maj = [o for o, c in ctr.items() if c >= need]
                shared = set.intersection(*per.values()) if per else set()
                lines.append(
                    f"  {name}: hit_players={len(per)}/{n} "
                    f"shared={sorted(shared)[:12]} majority={sorted(maj)[:12]} "
                    f"top={ctr.most_common(5)}"
                )

            # Existence anywhere in head (not just near UID)
            lines.append("\n## head existence counts (first 5 abs hits)")
            for p in PLAYERS[:6]:
                y, m, d = map(int, p["dob"].split("-"))
                dob = date(y, m, d)
                for name in ("tcm_d0_y_leapI", "tcm_d0_y", "mark_tcm_d0_y", "mark_year"):
                    pat = tcm_patterns(dob)[name]
                    hits = []
                    j = 0
                    end = min(len(mm), PERSON_HEAD)
                    while len(hits) < 5:
                        j = mm.find(pat, j, end)
                        if j < 0:
                            break
                        hits.append(j)
                        j += 1
                    lines.append(f"  {p['name']} {name}: {hits}")

            # Game date as TCM for mid-2039
            lines.append("\n## game date TCM samples around 2039-07-01")
            for g in (date(2039, 7, 1), date(2039, 5, 15), date(2039, 6, 30)):
                for name, pat in tcm_patterns(g).items():
                    if not name.startswith("tcm_d"):
                        continue
                    j = mm.find(pat, 0, min(len(mm), 64 * 1024 * 1024))
                    lines.append(f"  {g} {name} first@{j}")
        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # summary
    print("\n".join([ln for ln in lines if ln.startswith("##") or ln.startswith("  ") and ("consensus" in ln or "hit_players" in ln or "NO" in ln or "no TCM" in ln or "existence" in ln or "game date" in ln or "first@" in ln)][-60:]))
    print("wrote", OUT)
    # also print consensus block fully
    idx = next(i for i, ln in enumerate(lines) if "consensus" in ln)
    print("\n".join(lines[idx:]))


if __name__ == "__main__":
    main()
