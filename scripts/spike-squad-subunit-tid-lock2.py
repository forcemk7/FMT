#!/usr/bin/env python3
"""Sprint: resolve current jobs for II/U19 UIDs; find owning squad tids."""

from __future__ import annotations

import importlib.util
import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "squad-subunit-tid-lock2.txt"

PLAYERS = [
    ("Ermin_II", 2002138129),
    ("Solo_U19", 2002332550),
    ("Sangare_prev", 2002423570),
    ("Reserve_prev", 2002206353),
    ("Seimen_FT", 2000175080),  # control
]

TID_FT = 193616


def load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def pick_bin() -> Path:
    for p in sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no bin")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 80) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def jobs_for_uid(mm: mmap.mmap, uid: int) -> list[tuple[int, int, bytes]]:
    """Find 0b/09/0a/08 02 <job> 02 <uid> associations → (job, abs, tag)."""
    uidb = struct.pack("<I", uid)
    hits = []
    for tag in (0x0B, 0x09, 0x0A, 0x08):
        # pattern: tag 02 <job:u32> 02 <uid>
        # search uid first then check back
        for uoff in find_all(mm, b"\x02" + uidb, limit=60):
            if uoff < 7:
                continue
            if mm[uoff - 6] == tag and mm[uoff - 5] == 0x02:
                job = struct.unpack_from("<I", mm, uoff - 4)[0]
                if 1000 <= job <= 5_000_000:
                    hits.append((job, uoff - 6, bytes([tag])))
    # dedupe by job
    seen = set()
    out = []
    for job, abs_, tag in hits:
        if job in seen:
            continue
        seen.add(job)
        out.append((job, abs_, tag))
    return out


def dump(mm: mmap.mmap, off: int, before: int = 48, after: int = 80) -> str:
    lo = max(0, off - before)
    hi = min(len(mm), off + after)
    return f"@{off} " + bytes(mm[lo:hi]).hex(" ")


def main() -> int:
    eft = load_eft()
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# subunit tid lock2 · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            squads = eft.discover_squads(mm)
            lines.append(f"squads={len(squads)}")

            uid_jobs: dict[str, list[int]] = {}
            for name, uid in PLAYERS:
                jobs = jobs_for_uid(mm, uid)
                uid_jobs[name] = [j for j, _, _ in jobs]
                lines.append("")
                lines.append(f"## {name} uid={uid}")
                lines.append(f"  assoc jobs={[(j, t.hex()) for j, _, t in jobs]}")
                for job, abs_, tag in jobs[:8]:
                    owners = [
                        tid
                        for tid, (_a, _c, js) in squads.items()
                        if job in js
                    ]
                    lines.append(
                        f"  job={job} tag={tag.hex()} @{abs_} "
                        f"in_squad_tids={owners[:8]}"
                    )

            # For any job that landed in a squad, summarize
            lines.append("")
            lines.append("## jobs → owning tids summary")
            for name, jobs in uid_jobs.items():
                for job in jobs:
                    owners = [
                        (tid, len(js), a)
                        for tid, (a, _c, js) in squads.items()
                        if job in js
                    ]
                    if owners:
                        lines.append(f"{name} job={job} → {owners}")

            # Dump around live U19 name @60415908 from prior sprint
            lines.append("")
            lines.append("## context around Schalke 04 U19 @60415908")
            for off in (60415905, 60415908):
                if 0 <= off < len(mm):
                    lines.append(dump(mm, off, 32, 128))
                    # u32 values that are known squad tids
                    for i in range(0, 160, 4):
                        v = struct.unpack_from("<I", mm, off + i)[0]
                        if v in squads:
                            lines.append(
                                f"  +{i}: tid={v} nJobs={len(squads[v][2])} "
                                f"listAbs={squads[v][0]}"
                            )

            # Search tid integers near U19/II name hits in live region (50–80MB)
            lines.append("")
            lines.append("## squad tids occurring within ±2KB of live name hits")
            for label, needle in (
                ("II", b"Schalke 04 II"),
                ("U19", b"Schalke 04 U19"),
            ):
                for h in find_all(mm, needle, limit=30):
                    if h < 50_000_000 or h > 200_000_000:
                        continue  # skip early catalog / late noise
                    found = []
                    lo, hi = max(0, h - 2048), min(len(mm), h + 2048)
                    for off in range(lo, hi - 3):
                        v = struct.unpack_from("<I", mm, off)[0]
                        if v in squads and v != TID_FT:
                            found.append((off - h, v, len(squads[v][2])))
                    # dedupe tid keep closest
                    best: dict[int, tuple[int, int]] = {}
                    for rel, tid, n in found:
                        if tid not in best or abs(rel) < abs(best[tid][0]):
                            best[tid] = (rel, n)
                    if best:
                        lines.append(f"{label}@{h}: {sorted(best.items(), key=lambda x: abs(x[1][0]))[:8]}")

            # 595080 job list sample
            if 595080 in squads:
                labs, count, jobs = squads[595080]
                lines.append("")
                lines.append(f"## tid=595080 n={len(jobs)} listAbs={labs}")
                lines.append(f"  jobs sample={jobs[:20]}")
                # any of our resolved jobs in it?
                all_jobs = {j for js in uid_jobs.values() for j in js}
                lines.append(f"  overlap_calib_jobs={sorted(all_jobs & set(jobs))}")

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
