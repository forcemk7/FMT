#!/usr/bin/env python3
"""Sprint: parse job lists embedded after Schalke II / U19 name objects."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "squad-subunit-namelist.txt"

JOB_II = 237871
JOB_U19 = 439758
JOB_U19_PREV = 540180
JOB_RES_PREV = 306095


def pick_bin() -> Path:
    for p in sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no bin")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 40) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def try_parse_joblist(mm: mmap.mmap, start: int, window: int = 512) -> dict | None:
    """Hunt count_u16 + packed jobs in [start, start+window)."""
    hi = min(len(mm), start + window)
    best = None
    for off in range(start, hi - 2):
        count = struct.unpack_from("<H", mm, off)[0]
        if not (12 <= count <= 60):
            continue
        jobs_off = off + 2
        if jobs_off + 4 * count > len(mm):
            continue
        jobs = [struct.unpack_from("<I", mm, jobs_off + 4 * k)[0] for k in range(count)]
        # plausible employment ids
        ok = sum(1 for j in jobs if 50_000 <= j <= 2_000_000)
        if ok < max(10, count * 2 // 3):
            continue
        uniq = len(set(jobs))
        if uniq < count * 0.8:
            continue
        score = ok
        # bonus if known calib jobs present
        for mark, job in (
            ("II", JOB_II),
            ("U19", JOB_U19),
            ("U19p", JOB_U19_PREV),
            ("Resp", JOB_RES_PREV),
        ):
            if job in jobs:
                score += 50
        if best is None or score > best["score"]:
            best = {
                "count_at": off,
                "count": count,
                "jobs": jobs,
                "score": score,
                "rel": off - start,
            }
    return best


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# subunit name→joblist · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for label, needle in (
                ("U19", b"Schalke 04 U19"),
                ("II", b"Schalke 04 II"),
                ("FC_U19", b"FC Schalke 04 U19"),
                ("FC_II", b"FC Schalke 04 II"),
            ):
                hits = find_all(mm, needle)
                lines.append(f"## {label} hits={len(hits)}")
                for h in hits:
                    # Prefer live region
                    region = (
                        "early"
                        if h < 20_000_000
                        else "mid"
                        if h < 200_000_000
                        else "late"
                    )
                    parsed = try_parse_joblist(mm, h, 600)
                    if not parsed:
                        lines.append(f"  @{h} ({region}): no joblist")
                        continue
                    jobs = parsed["jobs"]
                    marks = []
                    if JOB_II in jobs:
                        marks.append("HAS_II")
                    if JOB_U19 in jobs:
                        marks.append("HAS_U19")
                    if JOB_U19_PREV in jobs:
                        marks.append("HAS_U19prev")
                    if JOB_RES_PREV in jobs:
                        marks.append("HAS_ResPrev")
                    lines.append(
                        f"  @{h} ({region}): count={parsed['count']} "
                        f"rel=+{parsed['rel']} score={parsed['score']} "
                        f"{' '.join(marks) if marks else '-'}"
                    )
                    lines.append(f"    jobs[0:12]={jobs[:12]}")
                    if marks or region == "mid":
                        # hex around count
                        ca = parsed["count_at"]
                        lines.append(
                            "    ctx: "
                            + bytes(mm[max(0, ca - 48) : ca + 16]).hex(" ")
                        )

            # Explicit: parse from known good U19 site
            lines.append("")
            lines.append("## forced parse after U19@60415908")
            h = 60415908
            # from prior dump, count 1a00 appears after twin ptr block
            # search for 1a 00 followed by jobs including high 0x06xxxx
            for off in range(h, h + 200):
                if struct.unpack_from("<H", mm, off)[0] == 0x1A:
                    jobs = [
                        struct.unpack_from("<I", mm, off + 2 + 4 * k)[0]
                        for k in range(26)
                    ]
                    lines.append(f"  count@+{off - h} jobs0_8={jobs[:8]}")
                    lines.append(
                        f"  contains Solo job {JOB_U19}: {JOB_U19 in jobs}"
                    )
                    lines.append(f"  min/max={min(jobs)}/{max(jobs)}")
                    # show all
                    lines.append(f"  all={jobs}")

            # Find II live mid-file name (50–100MB)
            lines.append("")
            lines.append("## II mid-file candidates")
            for h in find_all(mm, b"Schalke 04 II"):
                if 50_000_000 <= h <= 100_000_000:
                    parsed = try_parse_joblist(mm, h, 800)
                    lines.append(f"@{h}: {parsed}")
                    if parsed:
                        lines.append(
                            "  ctx: "
                            + bytes(
                                mm[
                                    max(0, parsed["count_at"] - 64) : parsed[
                                        "count_at"
                                    ]
                                    + 8
                                ]
                            ).hex(" ")
                        )

        finally:
            mm.close()

    lines.append(f"\nelapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
