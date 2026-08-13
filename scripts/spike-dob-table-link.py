#!/usr/bin/env python3
"""Link unique mark+days DOB sites back to players via personIndex / nearby ids."""

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
OUT = ROOT / "tmp" / "fm-spike" / "dob-table-link.txt"
MARK = bytes.fromhex("01006c07")
EPOCH = date(1900, 1, 1)
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


def person_index(mm: mmap.mmap, dab: int) -> int | None:
    if dab + 35 > len(mm):
        return None
    pi = struct.unpack_from("<I", mm, dab + 31)[0]
    return pi if 0 < pi < 200_000 else None


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
                pi = person_index(mm, dab) if dab is not None else None
                needle = MARK + struct.pack("<I", days)
                sites: list[int] = []
                j = mm.find(needle)
                while j >= 0 and len(sites) < 20:
                    sites.append(j)
                    j = mm.find(needle, j + 1)
                site = sites[0] if sites else None
                rows.append(
                    {
                        "name": p["name"],
                        "uid": uid,
                        "dob": dob,
                        "days": days,
                        "dab": dab,
                        "pi": pi,
                        "site": site,
                        "sites": sites,
                    }
                )

            # Dump ±64 around each DOB site with annotations
            lines.append("## DOB site dumps (±64) with pi/uid markers")
            pi_near: Counter[int] = Counter()
            for r in rows:
                if r["site"] is None:
                    lines.append(f"  {r['name']}: no site")
                    continue
                s = r["site"]
                lo = max(0, s - 64)
                hi = min(len(mm), s + 96)
                blob = bytes(mm[lo:hi])
                lines.append(
                    f"\n  {r['name']} pi={r['pi']} uid={r['uid']} site={s} "
                    f"sites={len(r['sites'])}"
                )
                lines.append(f"  hex={blob.hex(' ')}")
                # find pi / uid relatives
                if r["pi"] is not None:
                    pat = struct.pack("<I", r["pi"])
                    start = 0
                    while True:
                        i = blob.find(pat, start)
                        if i < 0:
                            break
                        rel = i - (s - lo)
                        pi_near[rel] += 1
                        lines.append(f"    pi @{rel:+d}")
                        start = i + 1
                up = struct.pack("<I", r["uid"])
                start = 0
                while True:
                    i = blob.find(up, start)
                    if i < 0:
                        break
                    rel = i - (s - lo)
                    lines.append(f"    uid @{rel:+d}")
                    start = i + 1

            lines.append("\n## shared pi-relative offsets near DOB site")
            for rel, n in pi_near.most_common(20):
                lines.append(f"  {rel:+d}: {n}")

            # Search: does person double neighborhood contain pointer (= site abs)?
            lines.append("\n## pointer from double±8KB to DOB site abs?")
            ptr_ok = 0
            for r in rows:
                if r["dab"] is None or r["site"] is None:
                    continue
                dab, site = r["dab"], r["site"]
                win = bytes(mm[max(0, dab - 8192) : dab + 8192])
                # absolute pointer as u32 or u64 lower 32
                pats = [
                    ("u32", struct.pack("<I", site & 0xFFFFFFFF)),
                    ("u32_plus4", struct.pack("<I", (site + 4) & 0xFFFFFFFF)),
                    ("u32_daysfield", struct.pack("<I", (site + 4) & 0xFFFFFFFF)),
                ]
                found = []
                for name, pat in pats:
                    if pat in win:
                        found.append(name)
                # also relative offset dab->site as i32 in window
                delta = site - dab
                if struct.pack("<i", delta) in win:
                    found.append("i32_delta")
                if found:
                    ptr_ok += 1
                    lines.append(f"  {r['name']}: FOUND {found} delta={delta:+d}")
                else:
                    lines.append(f"  {r['name']}: no ptr delta={delta:+d}")
            lines.append(f"ptr_ok={ptr_ok}/{len(rows)}")

            # Cluster DOB sites — are they in a dense table?
            lines.append("\n## DOB site clustering")
            sites = sorted(r["site"] for r in rows if r["site"] is not None)
            if len(sites) >= 2:
                gaps = [sites[i + 1] - sites[i] for i in range(len(sites) - 1)]
                lines.append(f"  count={len(sites)} span={sites[-1] - sites[0]}")
                lines.append(f"  gap min/med/max={min(gaps)}/{sorted(gaps)[len(gaps)//2]}/{max(gaps)}")
                lines.append(f"  gap top={Counter(gaps).most_common(10)}")
                for r in sorted(rows, key=lambda x: x["site"] or 0):
                    if r["site"] is None:
                        continue
                    lines.append(
                        f"  @{r['site']}: {r['name']} pi={r['pi']} days={r['days']}"
                    )

            # After days, decode common trailing u32s — correlate with pi
            lines.append("\n## trailing u32 after mark+days vs personIndex")
            for off in (4, 8, 12, 16, 20, 24):  # after days start (= mark+4)
                matches = 0
                vals = []
                for r in rows:
                    if r["site"] is None or r["pi"] is None:
                        continue
                    pos = r["site"] + 4 + off
                    if pos + 4 > len(mm):
                        continue
                    val = struct.unpack_from("<I", mm, pos)[0]
                    vals.append(val)
                    if val == r["pi"]:
                        matches += 1
                lines.append(
                    f"  days+{off}: pi_match={matches} "
                    f"sample_vals={vals[:8]}"
                )

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
