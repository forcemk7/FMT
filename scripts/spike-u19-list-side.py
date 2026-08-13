#!/usr/bin/env python3
"""Compare U19 job-lists before vs after Schalke name — which has live squad?"""

from __future__ import annotations

import importlib.util
import mmap
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from u19_squad_discovery import (  # noqa: E402
    MOTIF_LIST,
    find_all,
    parse_list_after_name,
    read_lp32,
    resolve_u19_squad,
)

spec = importlib.util.spec_from_file_location(
    "extract_ft",
    ROOT / "scripts" / "extract-first-team-fast.py",
)
assert spec and spec.loader
extract_ft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_ft)

WANT = [
    "Carsten Kraft",
    "James Solo",
    "Luca Eschweiler",
    "Jan Breite",
]
SCREENSHOT_WRONG = [
    "Alparslan",
    "André Fayet",
    "Andre Fayet",
    "Clemens Prus",
    "Tammo Nieweler",
]


def pick_bin() -> Path:
    cands = sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-fm-*.bin"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in cands:
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no bin")


def parse_list_before_name(
    mm: mmap.mmap, name_abs: int, window: int = 250
) -> dict | None:
    lo = max(0, name_abs - window)
    start = lo
    last = None
    while True:
        m = mm.find(MOTIF_LIST, start, name_abs)
        if m < 0:
            break
        last = m
        start = m + 1
    if last is None:
        return None
    count_abs = last + len(MOTIF_LIST)
    cnt = struct.unpack_from("<H", mm, count_abs)[0]
    if not (3 <= cnt <= 50):
        return None
    jobs_abs = count_abs + 2
    if jobs_abs + 4 * cnt > len(mm):
        return None
    jobs = [
        struct.unpack_from("<I", mm, jobs_abs + 4 * i)[0] for i in range(cnt)
    ]
    ok = sum(1 for jid in jobs if 50_000 <= jid <= 2_000_000)
    if ok < max(3, (cnt + 1) // 2):
        return None
    return {
        "motifAbs": last,
        "countAbs": count_abs,
        "jobsAbs": jobs_abs,
        "count": cnt,
        "jobs": jobs,
        "delta": last - name_abs,
    }


def names_for_jobs(mm: mmap.mmap, jobs: list[int]) -> list[tuple[int, int, str]]:
    job_uid = extract_ft.resolve_job_uids_batch(mm, jobs)
    out: list[tuple[int, int, str]] = []
    for job in jobs:
        uid = job_uid.get(job, 0)
        if not uid:
            out.append((job, 0, "?"))
            continue
        doubles = extract_ft.collect_doubles(mm, uid)
        name = extract_ft.resolve_name(mm, uid, doubles) or "?"
        out.append((job, uid, name))
    return out


def score_names(rows: list[tuple[int, int, str]]) -> dict:
    names = [n for _j, _u, n in rows]
    joined = " | ".join(names)
    return {
        "n": len(rows),
        "wantHits": [w for w in WANT if any(w.lower() in n.lower() for n in names)],
        "screenshotHits": [
            w for w in SCREENSHOT_WRONG if any(w.lower() in n.lower() for n in names)
        ],
        "names": names,
    }


def main() -> int:
    bin_path = pick_bin()
    print(f"bin={bin_path.name}", flush=True)
    t0 = time.perf_counter()
    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hit = resolve_u19_squad(mm, "Schalke 04")
            assert hit and hit.get("list")
            name_abs = hit["nameAbs"]
            u19_name = hit["u19Name"]
            after = hit["list"]
            before = parse_list_before_name(mm, name_abs, 250)

            # Also: list after LONG form name if present
            long_raw = b"FC Schalke 04 U19"
            long_hit = None
            for h in find_all(mm, long_raw, limit=10, lo=40_000_000, hi=120_000_000):
                if h >= 4 and struct.unpack_from("<I", mm, h - 4)[0] == len(long_raw):
                    lst = parse_list_after_name(mm, h, len(long_raw))
                    if lst:
                        long_hit = {"nameAbs": h, "list": lst}
                        break

            print(f"short resolve name={u19_name!r} @{name_abs} method={hit['method']}")
            print(
                f"  AFTER  n={after['count']} countAbs={after['countAbs']} delta={after['delta']}"
            )
            if before:
                print(
                    f"  BEFORE n={before['count']} countAbs={before['countAbs']} delta={before['delta']}"
                )
            if long_hit:
                print(
                    f"  LONG after n={long_hit['list']['count']} "
                    f"countAbs={long_hit['list']['countAbs']} nameAbs={long_hit['nameAbs']}"
                )

            candidates = [
                ("AFTER_short", after),
            ]
            if before:
                candidates.append(("BEFORE_short", before))
            if long_hit and long_hit["list"]["countAbs"] != after["countAbs"]:
                candidates.append(("AFTER_long", long_hit["list"]))

            for label, lst in candidates:
                print(f"\n## {label} resolving {lst['count']} jobs…", flush=True)
                rows = names_for_jobs(mm, lst["jobs"])
                sc = score_names(rows)
                print(f"  want hits: {sc['wantHits']}")
                print(f"  screenshot-ish hits: {sc['screenshotHits']}")
                for job, uid, name in rows:
                    mark = ""
                    for w in WANT:
                        if w.lower() in name.lower():
                            mark = "  << WANT"
                            break
                    print(f"  {name}  job={job} uid={uid}{mark}")

            # Neighbour context
            print("\n## nearby lp32 *U19*")
            for off in range(name_abs - 500, name_abs + 500):
                s = read_lp32(mm, off)
                if s and s.endswith(" U19"):
                    print(f"  @{off} {s!r} d={off - name_abs}")

            print(f"\nelapsed={time.perf_counter() - t0:.1f}s")
        finally:
            mm.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
