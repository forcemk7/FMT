#!/usr/bin/env python3
"""Lock: parent short → U19 name → colocated subunit job-list (BEFORE name).

U19 is NOT the II affiliate clubId/team-body join. Youth rows keep the
subunit header within ~220 bytes *before* the lp32 name (list → labels).
After-name lists are often neighbour/decoy squads.

Recipe:
  1. Prefer exact lp32 f'{S} U19' in mid-file (~40–120MB)
  2. From name start, within −220 bytes, take last
       ff×4 | 00 | ff×4 | count:u16∈[3,50] | jobs:u32×n
     with majority of jobs in 50000..2000000
  3. Fallback: after-name +150 (decoy-prone)
  4. If exact miss, fuzzy-match other *U19 labels in the same band
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import mmap
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from u19_squad_discovery import resolve_u19_squad  # noqa: E402

OUT = ROOT / "tmp" / "fm-spike" / "squad-u19-namelist-lock.txt"

CROSS_PARENTS = [
    "Schalke 04",
    "Kaiserslautern",
    "Hansa Rostock",
    "Karlsruhe",
    "Borussia Dortmund",
    "Werder Bremen",
    "Hoffenheim",
    "VfB Stuttgart",
]

SCHALKE_MUST_INCLUDE = [
    "Carsten Kraft",
    "James Solo",
    "Luca Eschweiler",
    "Jan Breite",
]
SCHALKE_MUST_EXCLUDE = [
    "Alparslan Yiğit",
    "André Fayet",
    "Clemens Prus",
    "Tammo Nieweler",
]


def pick_bin(explicit: Path | None = None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise SystemExit(f"bin not found: {explicit}")
        return explicit
    for p in sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-fm-*.bin"),
        key=lambda q: q.stat().st_mtime,
        reverse=True,
    ):
        if p.stat().st_size > 1_500_000_000:
            return p
    for p in sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
        key=lambda q: q.stat().st_mtime,
        reverse=True,
    ):
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no fmt-*.bin probe found in Temp")


def load_extract_ft():
    spec = importlib.util.spec_from_file_location(
        "extract_ft",
        ROOT / "scripts" / "extract-first-team-fast.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def names_for_jobs(extract_ft, mm: mmap.mmap, jobs: list[int]) -> list[str]:
    job_uid = extract_ft.resolve_job_uids_batch(mm, jobs)
    out: list[str] = []
    for job in jobs:
        uid = job_uid.get(job, 0)
        if not uid:
            out.append("?")
            continue
        doubles = extract_ft.collect_doubles(mm, uid)
        out.append(extract_ft.resolve_name(mm, uid, doubles) or "?")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bin", type=Path, default=None)
    args = ap.parse_args()
    bin_path = pick_bin(args.bin)
    t0 = time.perf_counter()
    lines: list[str] = [
        f"# u19 name→BEFORE-list lock · {bin_path.name}",
        f"# size={bin_path.stat().st_size}",
        "",
    ]
    print(f"mmap {bin_path.name}…", flush=True)
    extract_ft = load_extract_ft()

    cross: dict[str, dict] = {}
    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for parent in CROSS_PARENTS:
                hit = resolve_u19_squad(mm, parent)
                if not hit or not hit.get("list"):
                    lines.append(f"FAIL {parent}: no hit")
                    print(f"FAIL {parent}", flush=True)
                    continue
                lst = hit["list"]
                side = "before" if lst["delta"] < 0 else "after"
                row = {
                    "u19Name": hit["u19Name"],
                    "method": hit["method"],
                    "matchScore": hit.get("matchScore"),
                    "nameAbs": hit["nameAbs"],
                    "countAbs": lst["countAbs"],
                    "listCount": lst["count"],
                    "delta": lst["delta"],
                    "listSide": side,
                }
                cross[parent] = row
                lines.append(
                    f"OK {parent}: {row['u19Name']} method={row['method']} "
                    f"side={side} n={row['listCount']} name@{row['nameAbs']} "
                    f"list@{row['countAbs']} delta={row['delta']}"
                )
                print(lines[-1], flush=True)

            lines.append("")
            sch = cross.get("Schalke 04")
            if not sch:
                lines.append("VERIFY Schalke 04: FAIL (no hit)")
                print(lines[-1], flush=True)
            elif sch["listSide"] != "before":
                lines.append(
                    f"VERIFY Schalke 04: FAIL listSide={sch['listSide']} (want before)"
                )
                print(lines[-1], flush=True)
            else:
                print("resolving Schalke U19 names for anchor check…", flush=True)
                hit = resolve_u19_squad(mm, "Schalke 04")
                assert hit and hit["list"]
                names = names_for_jobs(extract_ft, mm, hit["list"]["jobs"])
                joined = " | ".join(names)
                missing = [
                    w
                    for w in SCHALKE_MUST_INCLUDE
                    if not any(w.lower() in n.lower() for n in names)
                ]
                leaked = [
                    w
                    for w in SCHALKE_MUST_EXCLUDE
                    if any(w.lower() in n.lower() for n in names)
                ]
                if missing or leaked:
                    lines.append(
                        f"VERIFY Schalke 04: FAIL missing={missing} leaked={leaked}"
                    )
                    lines.append(f"  names: {joined}")
                else:
                    lines.append(
                        "VERIFY Schalke 04: PASS (before-list + Kraft/Solo/Eschweiler/Breite)"
                    )
                print(lines[-1], flush=True)
        finally:
            mm.close()

    ok = len(cross)
    before_ok = sum(1 for r in cross.values() if r.get("listSide") == "before")
    lines.append("")
    lines.append(f"crossClub {ok}/{len(CROSS_PARENTS)} before={before_ok}/{ok}")
    lines.append(f"elapsedMs={int((time.perf_counter() - t0) * 1000)}")
    lines.append("")
    lines.append("## cross JSON")
    lines.append(json.dumps(cross, indent=2))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({ok}/{len(CROSS_PARENTS)})", flush=True)
    sch_ok = any("PASS" in ln for ln in lines if "VERIFY Schalke" in ln)
    return 0 if ok == len(CROSS_PARENTS) and before_ok == ok and sch_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
