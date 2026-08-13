#!/usr/bin/env python3
"""
T004C spike: resolve missing GT loan UIDs (Risse, Pérez, Görrissen)
against live-0112 decomp + extract. RE only — no product edits.

Outputs: tmp/fm-spike/loan-missing-uids-live0112.txt
"""

from __future__ import annotations

import json
import mmap
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-missing-uids-live0112.txt"

EMP_TAGS = (0x08, 0x09, 0x0A, 0x0B)
EMPLOYMENT_TAIL = 128 * 1024 * 1024
UID_LO, UID_HI = 1_000_000, 2_200_000_000

MISSING = [
    ("Landri Risse", 2002217460, "Darmstadt"),
    ("Miguel Perez", 2002251850, "Kiel"),
    ("Lion Gorrissen", 2002215969, "St. Pauli"),
]
FT_GAPS = [215122, 382374, 315711]
KNOWN_JOBS = {
    382267: "Sipho",
    437615: "Vlad",
    506986: "Manole",
    506980: "Braescu",
    538884: "Millwood",
    365838: "Ozturk",
}


def pack_u32(n: int) -> bytes:
    return struct.pack("<I", n)


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 200) -> list[int]:
    hits: list[int] = []
    pos = 0
    while len(hits) < limit:
        j = mm.find(needle, pos)
        if j < 0:
            break
        hits.append(j)
        pos = j + 1
    return hits


def emp_jobs_for_uid(mm: mmap.mmap, uid: int) -> list[tuple[int, int, int]]:
    """Return (abs, tag, job) for <tag> 02 <job> 02 <uid> hits (whole file)."""
    needle = b"\x02" + pack_u32(uid)
    out: list[tuple[int, int, int]] = []
    for j in find_all(mm, needle, limit=500):
        if j >= 6 and mm[j - 5] == 0x02 and mm[j - 6] in EMP_TAGS:
            job = struct.unpack_from("<I", mm, j - 4)[0]
            tag = mm[j - 6]
            if 1_000 <= job <= 50_000_000:
                out.append((j - 6, tag, job))
    return out


def resolve_gap_jobs(mm: mmap.mmap, jobs: list[int]) -> dict[int, list[tuple[int, int, int]]]:
    """For each gap job, find employment patterns <tag> 02 <job> 02 <uid>."""
    result: dict[int, list[tuple[int, int, int]]] = {}
    for job in jobs:
        hits: list[tuple[int, int, int]] = []
        jb = pack_u32(job)
        for tag in EMP_TAGS:
            pat = bytes([tag, 0x02]) + jb + b"\x02"
            for j in find_all(mm, pat, limit=50):
                if j + 11 <= len(mm):
                    uid = struct.unpack_from("<I", mm, j + 7)[0]
                    hits.append((j, tag, uid))
        result[job] = hits
    return result


def nearby_u32(mm: mmap.mmap, off: int, radius: int, candidates: set[int]) -> list[tuple[int, int]]:
    """Return (rel, value) for candidate u32s found within ±radius of off."""
    lo = max(0, off - radius)
    hi = min(len(mm), off + radius)
    found: list[tuple[int, int]] = []
    for cand in candidates:
        needle = pack_u32(cand)
        pos = lo
        while True:
            j = mm.find(needle, pos, hi)
            if j < 0:
                break
            found.append((j - off, cand))
            pos = j + 1
    return sorted(found, key=lambda x: abs(x[0]))


def ascii_near(mm: mmap.mmap, off: int, radius: int = 96) -> list[str]:
    lo = max(0, off - radius)
    hi = min(len(mm), off + radius)
    names: list[str] = []
    for k in range(lo, max(lo, hi - 4)):
        ln = mm[k]
        if 3 <= ln <= 24 and k + 1 + ln <= hi:
            chunk = mm[k + 1 : k + 1 + ln]
            if all(32 <= b < 127 for b in chunk) and chunk[:1].isalpha():
                s = chunk.decode("ascii", errors="ignore")
                if s not in names:
                    names.append(s)
    return names[:8]


def double_uid_sites(mm: mmap.mmap, uid: int) -> list[int]:
    """Sites where uid appears as consecutive u32 pair (person double-UID)."""
    needle = pack_u32(uid) + pack_u32(uid)
    return find_all(mm, needle, limit=40)


def collect_extract_pool(data: dict) -> tuple[set[int], set[int], dict[int, str], dict[int, int]]:
    uids: set[int] = set()
    jobs: set[int] = set()
    name_of: dict[int, str] = {}
    job_of: dict[int, int] = {}

    def add(p: dict, unit: str) -> None:
        uid = int(p.get("uid") or 0)
        job = int(p.get("jobId") or 0)
        if uid:
            uids.add(uid)
            name_of[uid] = f"{unit}:{p.get('name') or uid}"
        if job:
            jobs.add(job)
            if uid:
                job_of[uid] = job

    for p in data.get("players") or []:
        add(p, "FT")
    reserves = data.get("reserves") or {}
    for p in reserves.get("players") or []:
        add(p, "II")
    u19 = data.get("u19") or data.get("youth") or {}
    for p in (u19.get("players") if isinstance(u19, dict) else []) or []:
        add(p, "U19")
    # alternate shapes
    for key, unit in (("iiPlayers", "II"), ("u19Players", "U19"), ("reservesPlayers", "II")):
        for p in data.get(key) or []:
            add(p, unit)
    return uids, jobs, name_of, job_of


def squad_list_jobs(mm: mmap.mmap, list_abs: int, count: int) -> list[int]:
    if list_abs < 0 or list_abs + 2 + 4 * count > len(mm):
        return []
    hdr = struct.unpack_from("<H", mm, list_abs)[0]
    if hdr != count:
        # try without verifying
        pass
    return [struct.unpack_from("<I", mm, list_abs + 2 + 4 * i)[0] for i in range(count)]


def main() -> int:
    lines: list[str] = [
        "# T004C missing loan UIDs · live-0112",
        f"decomp={DECOMP.name} size={DECOMP.stat().st_size if DECOMP.exists() else 'MISSING'}",
        f"extract={EXTRACT.name}",
        "",
    ]
    if not DECOMP.exists() or not EXTRACT.exists():
        lines.append("BLOCKED: need live-0112-decomp.bin + live-0112-extract.json")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        return 1

    data = json.loads(EXTRACT.read_text(encoding="utf-16"))
    pool_uids, pool_jobs, name_of, job_of = collect_extract_pool(data)
    ft = data.get("players") or []
    reserves = data.get("reserves") or {}
    u19_block = data.get("u19") or {}
    ii = reserves.get("players") or []
    u19 = u19_block.get("players") or []
    lines.append(
        f"## extract pool FT={len(ft)} II={len(ii)} U19={len(u19)} uids={len(pool_uids)} "
        f"countHeader={data.get('countHeader')}"
    )
    for name, uid, club in MISSING:
        lines.append(
            f"  {name} uid={uid} →"
            f"{'IN extract ' + name_of[uid] if uid in pool_uids else 'MISSING from FT/II/U19'} "
            f"(FM:{club})"
        )
    lines.append("")

    list_abs = int(data.get("listAbs") or 0)
    count_hdr = int(data.get("countHeader") or len(ft))

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # Re-read FT (+II) jobs from extract listAbs / countHeader
            ft_jobs_from_list = squad_list_jobs(mm, list_abs, count_hdr) if list_abs else []
            lines.append(
                f"## FT listAbs={list_abs} countHeader={count_hdr} jobsRead={len(ft_jobs_from_list)}"
            )
            resolved_jobs = {int(p["jobId"]) for p in ft if p.get("jobId")}
            gap_jobs = (
                [j for j in ft_jobs_from_list if j not in resolved_jobs]
                if ft_jobs_from_list
                else list(FT_GAPS)
            )
            lines.append(f"  resolvedJobs={len(resolved_jobs)} gapJobs={gap_jobs}")

            ii_list_abs = int(reserves.get("listAbs") or 0)
            ii_count = int(reserves.get("countHeader") or 0)
            ii_jobs_list = squad_list_jobs(mm, ii_list_abs, ii_count) if ii_list_abs and ii_count else []
            ii_resolved = {int(p["jobId"]) for p in ii if p.get("jobId")}
            ii_gaps = [j for j in ii_jobs_list if j not in ii_resolved]
            lines.append(
                f"## II listAbs={ii_list_abs} countHeader={ii_count} "
                f"jobsRead={len(ii_jobs_list)} gapJobs={ii_gaps}"
            )
            all_gaps = list(dict.fromkeys(gap_jobs + ii_gaps))
            lines.append("")

            lines.append("## gap job employment resolve (tag 02 job 02 uid)")
            gap_hits = resolve_gap_jobs(mm, all_gaps or FT_GAPS)
            for job, hits in gap_hits.items():
                uniq = sorted({u for _, _, u in hits if UID_LO <= u <= UID_HI})
                lines.append(f"  job={job} empHits={len(hits)} personUids={uniq[:12]}")
            lines.append("")

            cand_jobs = set(all_gaps or FT_GAPS) | set(KNOWN_JOBS) | set(pool_jobs)
            lines.append("## per missing UID")
            for name, uid, club in MISSING:
                lines.append(f"### {name} uid={uid} FM:{club}")
                emp = emp_jobs_for_uid(mm, uid)
                lines.append(f"  empLinks={[(hex(t), j, a) for a, t, j in emp[:20]]}")
                sites = find_all(mm, pack_u32(uid), limit=80)
                lines.append(f"  uidSites={len(sites)} first={sites[:8]}")
                doubles = double_uid_sites(mm, uid)
                lines.append(f"  doubleUidSites={len(doubles)} offs={doubles[:8]}")

                # near gap / known jobs around each site
                gap_near: list[tuple[int, int, int]] = []  # site, rel, job
                for s in sites[:40]:
                    near = nearby_u32(mm, s, 64, set(all_gaps or FT_GAPS))
                    for rel, job in near[:4]:
                        gap_near.append((s, rel, job))
                lines.append(f"  gapNear(±64)={gap_near[:12]}")

                known_near: list[tuple[int, int, int]] = []
                for s in sites[:40]:
                    near = nearby_u32(mm, s, 64, set(KNOWN_JOBS))
                    for rel, job in near[:4]:
                        known_near.append((s, rel, job))
                lines.append(f"  knownJobNear(±64)={[(s, rel, job, KNOWN_JOBS.get(job)) for s, rel, job in known_near[:8]]}")

                # double-UID neighborhood: look for any job-like u32 + motifs
                for d in doubles[:5]:
                    names = ascii_near(mm, d, 128)
                    # scan ±128 for plausible job ids that appear in FT gaps or pool
                    near_jobs = nearby_u32(mm, d, 128, cand_jobs)
                    window = mm[max(0, d - 48) : d + 64]
                    motif_64ff = window.find(b"\x64\xff")
                    lines.append(
                        f"  double@{d}: asciiNear={names} pool/gapJobsNear={near_jobs[:10]} "
                        f"64ffRelInWin={motif_64ff if motif_64ff >= 0 else None}"
                    )
                    # hexdump 32 bytes around double
                    lo = max(0, d - 16)
                    hx = " ".join(f"{b:02x}" for b in mm[lo : lo + 48])
                    lines.append(f"    hex@{lo}: {hx}")
                lines.append("")

            # Reverse: do any gap jobs appear in employment with ANY uid in MISSING set?
            miss_uids = {u for _, u, _ in MISSING}
            lines.append("## cross: gap jobs × missing UIDs co-occurrence in ±128")
            cross_hits = 0
            for job in all_gaps or FT_GAPS:
                for joff in find_all(mm, pack_u32(job), limit=80)[:40]:
                    near = nearby_u32(mm, joff, 128, miss_uids)
                    if near:
                        cross_hits += 1
                        lines.append(f"  job={job} @{joff} nearMissing={near}")
            if cross_hits == 0:
                lines.append("  (none)")
            lines.append("")

            lines.append("## name string hits (len-prefixed ASCII)")
            for label, needle in (
                ("Risse", b"\x05Risse"),
                ("Landri", b"\x06Landri"),
                ("Perez", b"\x05Perez"),
                ("Gorrissen", b"\x09Gorrissen"),
                ("Goerrissen", b"\x0aGoerrissen"),
            ):
                hits = find_all(mm, needle, limit=20)
                lines.append(f"  {label}: {len(hits)} hits sample={hits[:6]}")
                for h in hits[:3]:
                    near = nearby_u32(mm, h, 256, miss_uids | set(all_gaps or FT_GAPS))
                    lines.append(f"    @{h} nearUidOrGap={near[:8]} ascii={ascii_near(mm, h, 64)}")

        finally:
            mm.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
