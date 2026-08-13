#!/usr/bin/env python3
"""
Loan hunt v2:
  1) Re-read FT/II job lists → find jobs that fail UID/name resolve (header gaps).
  2) Cross-club: resolve a few rival FT lists; report any UID overlap with Schalke pool.
  3) Per Schalke UID: count distinct employment jobs in tail (dual-employer check).

Needs: tmp/dynamics-b-extract.json + data/saves/dynamics-b.fm
"""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import tempfile
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "dynamics-b.fm"
EXTRACT = ROOT / "tmp" / "dynamics-b-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-hunt-v2.txt"
EMP_TAGS = (0x08, 0x09, 0x0A, 0x0B)

# Rival / same-league FT lists previously locked in ii-joblist spike (teamId → note).
# We'll rediscover via extract club short names where possible; fallback scan a few known tids.
RIVAL_SHORTS = (
    "Kaiserslautern",
    "Hansa Rostock",
    "Karlsruhe",
    "Borussia Dortmund",
    "Werder Bremen",
    "Hoffenheim",
    "VfB Stuttgart",
    "FC Köln",
    "1. FC Köln",
    "Köln",
    "Hamburger SV",
    "HSV",
    "Nürnberg",
    "1. FC Nürnberg",
)


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def decompress(mod, save: Path) -> Path:
    zstd_off = int(mod.probe_container(save)["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-loanv2-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zstd_off)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    chunk = reader.read(8 << 20)
                except zstd.ZstdError:
                    break
                if not chunk:
                    break
                out.write(chunk)
        finally:
            reader.close()
    return tmp


def read_jobs_at(mm: mmap.mmap, list_abs: int, count: int) -> list[int]:
    """listAbs in extract points at count u16 (or jobs?). Probe both."""
    # Prefer extract convention: listAbs = count header (u16), jobs follow.
    if list_abs + 2 + 4 * count <= len(mm):
        c = struct.unpack_from("<H", mm, list_abs)[0]
        if c == count:
            return [
                struct.unpack_from("<I", mm, list_abs + 2 + 4 * i)[0]
                for i in range(count)
            ]
    # Alternate: listAbs already at first job
    if list_abs + 4 * count <= len(mm):
        return [struct.unpack_from("<I", mm, list_abs + 4 * i)[0] for i in range(count)]
    return []


def jobs_for_uid(mm: mmap.mmap, uid: int, search_lo: int) -> set[int]:
    needle = b"\x02" + struct.pack("<I", uid)
    jobs: set[int] = set()
    pos = search_lo
    while True:
        j = mm.find(needle, pos)
        if j < 0:
            break
        if j >= 6 and mm[j - 5] == 0x02 and mm[j - 6] in EMP_TAGS:
            job = struct.unpack_from("<I", mm, j - 4)[0]
            if 1_000 <= job <= 50_000_000:
                jobs.add(job)
        pos = j + 1
    return jobs


def main() -> int:
    if not EXTRACT.exists() or not SAVE.exists():
        print("need extract + save")
        return 1
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    mod = load_extractor()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [f"# loan hunt v2 · {SAVE.name}", ""]

    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                search_lo = max(0, len(mm) - mod.EMPLOYMENT_TAIL)

                def analyze_squad(label: str, list_abs: int | None, count: int, players: list):
                    lines.append(f"## {label}")
                    lines.append(f"countHeader={count} resolvedPlayers={len(players)} listAbs={list_abs}")
                    if list_abs is None:
                        lines.append("  (no listAbs)")
                        lines.append("")
                        return set(), set()
                    raw = read_jobs_at(mm, int(list_abs), int(count))
                    lines.append(f"  rawJobsRead={len(raw)} nonzero={sum(1 for j in raw if j)}")
                    resolved_jobs = {int(p["jobId"]) for p in players if p.get("jobId")}
                    resolved_uids = {int(p["uid"]) for p in players if p.get("uid")}
                    gap = [j for j in raw if j and j not in resolved_jobs]
                    lines.append(f"  gapJobs (in list, not in extract players): {len(gap)}")
                    if gap:
                        ju = mod.resolve_job_uids_batch(mm, gap)
                        for j in gap:
                            uid = ju.get(j, 0)
                            name = mod.resolve_name(mm, uid) if uid else None
                            emp = sorted(jobs_for_uid(mm, uid, search_lo)) if uid else []
                            lines.append(
                                f"    job={j} uid={uid or '-'} name={name or '-'} empJobs={emp}"
                            )
                    # dual-employer among resolved
                    hist: dict[int, int] = defaultdict(int)
                    multi = []
                    for p in players:
                        uid = int(p["uid"])
                        jset = jobs_for_uid(mm, uid, search_lo)
                        hist[len(jset)] += 1
                        if len(jset) > 1:
                            multi.append((p.get("name"), uid, int(p["jobId"]), sorted(jset)))
                    lines.append(f"  empJobCountHist={dict(sorted(hist.items()))}")
                    lines.append(f"  multiEmp={len(multi)}")
                    for row in multi[:20]:
                        lines.append(f"    {row}")
                    lines.append("")
                    return resolved_jobs, resolved_uids

                sch_jobs: set[int] = set()
                sch_uids: set[int] = set()
                j, u = analyze_squad(
                    "FT",
                    data.get("listAbs"),
                    int(data.get("countHeader") or 0),
                    data.get("players") or [],
                )
                sch_jobs |= j
                sch_uids |= u
                res = data.get("reserves") or {}
                j, u = analyze_squad(
                    "II",
                    res.get("listAbs"),
                    int(res.get("countHeader") or 0),
                    res.get("players") or [],
                )
                sch_jobs |= j
                sch_uids |= u

                lines.append("## Cross-club UID overlap (sample rivals)")
                print("discover rival squads…", flush=True)
                # Use discover_squads then resolve a subset of large lists; map UIDs.
                squads = mod.discover_squads(mm)
                # Rank by size near FT
                candidates = sorted(
                    (
                        (tid, meta)
                        for tid, meta in squads.items()
                        if 15 <= len(meta[2]) <= 45
                    ),
                    key=lambda kv: -len(kv[1][2]),
                )[:12]
                lines.append(f"  sampledSquadTids={len(candidates)} (of {len(squads)} discovered)")
                overlap_hits = []
                for tid, (_abs, count, jobs) in candidates:
                    # skip if jobs heavily overlap Schalke list (same squad)
                    if len(set(jobs) & sch_jobs) >= max(5, len(jobs) // 3):
                        continue
                    ju = mod.resolve_job_uids_batch(mm, list(jobs))
                    uids = set(ju.values())
                    hit = uids & sch_uids
                    if hit:
                        names = []
                        for uid in sorted(hit):
                            # find name from extract
                            nm = next(
                                (
                                    p.get("name")
                                    for p in (data.get("players") or [])
                                    + (res.get("players") or [])
                                    if int(p.get("uid") or 0) == uid
                                ),
                                None,
                            )
                            names.append(f"{nm or uid}")
                        overlap_hits.append((tid, count, len(jobs), names))
                lines.append(f"  squadsWithSchalkeUidOverlap={len(overlap_hits)}")
                for tid, count, nj, names in overlap_hits:
                    lines.append(
                        f"    tid={tid} count={count} jobs={nj} shared={names}"
                    )
                if not overlap_hits:
                    lines.append("  (none — no Schalke pool UID on other FT-sized lists)")
                lines.append("")
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
