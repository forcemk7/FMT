#!/usr/bin/env python3
"""Sprint: lock Reserves/U19 squad tids via known job IDs + team-name strings.

Uses cached ~2GB decompress when available; otherwise streams once to temp.
"""

from __future__ import annotations

import importlib.util
import mmap
import os
import struct
import tempfile
import time
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "squad-subunit-tid-lock.txt"
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))

# Calibration from prior spikes
JOB_II = 237871  # Ermin Maric
JOB_U19 = 439758  # James Solo
JOB_U19_PREV = 540180  # Sangaré
TID_FT = 193616

NAMES = [
    b"Schalke 04 II",
    b"FC Schalke 04 II",
    b"Schalke 04 U19",
    b"FC Schalke 04 U19",
]


def load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def pick_bin() -> Path | None:
    cands = sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in cands:
        if p.stat().st_size > 1_500_000_000:
            return p
    return None


def decompress(save: Path) -> Path:
    eft = load_eft()
    zoff = int(eft.probe_container(save)["zstdOffset"])
    fd, name = tempfile.mkstemp(prefix="fmt-sub-", suffix=".bin")
    os.close(fd)
    tmp = Path(name)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zoff)
        r = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = r.read(8 << 20)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                out.write(b)
        finally:
            try:
                r.close()
            except zstd.ZstdError:
                pass
    return tmp


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 200) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def main() -> int:
    eft = load_eft()
    t0 = time.perf_counter()
    lines = [f"# subunit tid lock · {SAVE.name}", ""]
    print("resolve bin…", flush=True)
    bin_path = pick_bin()
    owned = False
    if bin_path is None:
        print("decompressing…", flush=True)
        bin_path = decompress(SAVE)
        owned = True
    lines.append(f"bin={bin_path.name} size={bin_path.stat().st_size}")
    print(f"mmap {bin_path.name}…", flush=True)

    try:
        with bin_path.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                squads = eft.discover_squads(mm)
                lines.append(f"discovered squads={len(squads)}")

                # Which tids contain calibration jobs?
                targets = {
                    "II/Ermin": JOB_II,
                    "U19/Solo": JOB_U19,
                    "U19prev/Sangare": JOB_U19_PREV,
                }
                lines.append("")
                lines.append("## tids whose job list contains calibration jobs")
                job_to_tids: dict[str, list[tuple[int, int, int]]] = {}
                for label, job in targets.items():
                    hits = []
                    for tid, (list_abs, count, jobs) in squads.items():
                        if job in jobs:
                            hits.append((tid, list_abs, len(jobs)))
                    hits.sort(key=lambda x: x[1])
                    job_to_tids[label] = hits
                    lines.append(f"{label} job={job}: {len(hits)} tid(s)")
                    for tid, abs_, n in hits[:12]:
                        mark = " <<FT" if tid == TID_FT else ""
                        lines.append(f"  tid={tid} nJobs={n} listAbs={abs_}{mark}")

                # Ranked manager hits for interesting tids
                interest = {TID_FT}
                for hits in job_to_tids.values():
                    for tid, _, _ in hits:
                        interest.add(tid)
                # also prior candidate
                interest.add(595080)
                mh = eft.scan_manager_hits(mm, sorted(interest))
                lines.append("")
                lines.append("## manager hits (0b02) on interest tids")
                for tid in sorted(interest, key=lambda t: -mh.get(t, 0)):
                    n = len(squads[tid][2]) if tid in squads else -1
                    lines.append(f"  tid={tid} managerHits={mh.get(tid, 0)} nJobs={n}")

                # Name-string → nearest squad listAbs
                lines.append("")
                lines.append("## team-name strings → nearest squad listAbs")
                for name in NAMES:
                    hits = find_all(mm, name, limit=20)
                    lines.append(f"{name!r}: {len(hits)} hits")
                    for h in hits[:6]:
                        # nearest squad by listAbs
                        if not squads:
                            continue
                        nearest = min(
                            squads.items(),
                            key=lambda kv: abs(kv[1][0] - h),
                        )
                        tid, (labs, count, jobs) = nearest
                        lines.append(
                            f"  @{h} nearest tid={tid} Δlist={labs - h:+d} "
                            f"nJobs={len(jobs)} containsII={JOB_II in jobs} "
                            f"containsU19={JOB_U19 in jobs}"
                        )
                        # also dump u32s in +256 after name for tid-like values
                        window = bytes(mm[h : min(len(mm), h + 256)])
                        tids_near = []
                        for i in range(0, len(window) - 3, 4):
                            v = struct.unpack_from("<I", window, i)[0]
                            if v in squads:
                                tids_near.append((i, v))
                        if tids_near:
                            lines.append(f"    squad tids in +256: {tids_near[:8]}")

                # For each locked tid candidate, show sample jobs + overlap with FT
                lines.append("")
                lines.append("## candidate squad overlap vs FT")
                ft_jobs = set(squads[TID_FT][2]) if TID_FT in squads else set()
                cand_tids = []
                for hits in job_to_tids.values():
                    cand_tids.extend(t for t, _, _ in hits)
                for tid in sorted(set(cand_tids)):
                    if tid not in squads:
                        continue
                    jobs = squads[tid][2]
                    overlap = len(ft_jobs & set(jobs))
                    lines.append(
                        f"tid={tid} n={len(jobs)} overlapFT={overlap} "
                        f"listAbs={squads[tid][0]}"
                    )

                # Sibling lists near FT listAbs cluster (from prior roster dump)
                if TID_FT in squads:
                    ft_abs = squads[TID_FT][0]
                    lines.append("")
                    lines.append(f"## squads with listAbs within ±64KB of FT@{ft_abs}")
                    near = [
                        (tid, labs, len(jobs))
                        for tid, (labs, _c, jobs) in squads.items()
                        if abs(labs - ft_abs) <= 64_000
                    ]
                    near.sort(key=lambda x: x[1])
                    for tid, labs, n in near:
                        flags = []
                        jobs = squads[tid][2]
                        if JOB_II in jobs:
                            flags.append("II")
                        if JOB_U19 in jobs:
                            flags.append("U19")
                        if JOB_U19_PREV in jobs:
                            flags.append("U19prev")
                        if tid == TID_FT:
                            flags.append("FT")
                        lines.append(
                            f"  @{labs} tid={tid} n={n} "
                            f"{'+'.join(flags) if flags else '-'}"
                        )

            finally:
                mm.close()
    finally:
        if owned:
            bin_path.unlink(missing_ok=True)

    lines.append("")
    lines.append(f"elapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
