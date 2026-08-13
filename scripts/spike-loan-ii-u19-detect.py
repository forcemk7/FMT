#!/usr/bin/env python3
"""
T004B RE: II/U19 loan detect recipe vs Sipho 64 ff 26 lock.

Uses tmp/live-0112-decomp.bin + tmp/live-0112-extract.json.
Writes tmp/fm-spike/spike-loan-ii-u19.txt — no product edits.
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "spike-loan-ii-u19.txt"

PARENT = 920
CLUB_LO, CLUB_HI = 50, 100_000

# Ground truth (ticket T004B) + Sipho control + FT Vlad contrast
GT = [
    ("II", "Manole", 2002390860, 506986, "Augsburg"),
    ("II", "Braescu", 2002390854, 506980, "Koln"),
    ("U19", "Millwood", 2002422274, 538884, "SC Paderborn"),
    ("U19", "Ozturk", 2002266096, 365838, "RW Essen"),
    ("FT", "Sipho", 2002282525, 382267, "Legia"),
    ("FT", "Vlad", 2002330407, 437615, "Eintracht Frankfurt"),
]

# Known positive loan club for Sipho
KNOWN_LOAN = {"Legia": 1456}

NAME_NEEDLES = {
    "Augsburg": [b"Augsburg", "Augsburg".encode("utf-16-le")],
    "Koln": [
        b"K\xc3\xb6ln",
        "Köln".encode("utf-16-le"),
        b"FC Koln",
        b"1. FC K",
        "1. FC Köln".encode("utf-16-le"),
    ],
    "SC Paderborn": [b"Paderborn", "Paderborn".encode("utf-16-le")],
    "RW Essen": [b"Essen", "Essen".encode("utf-16-le"), b"Rot-Weiss", b"RW Essen"],
    "Legia": [b"Legia", "Legia".encode("utf-16-le")],
    "Eintracht Frankfurt": [b"Frankfurt", "Frankfurt".encode("utf-16-le")],
}


def load_extract() -> dict:
    raw = EXTRACT.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            continue
    raise RuntimeError("cannot decode extract")


def players_by_unit(data: dict) -> dict[str, list[dict]]:
    out = {
        "FT": list(data.get("players") or []),
        "II": list((data.get("reserves") or {}).get("players") or []),
        "U19": list((data.get("u19") or {}).get("players") or []),
    }
    return out


def find_all(mm: mmap.mmap, needle: bytes, *, limit: int = 200) -> list[int]:
    hits: list[int] = []
    pos = 0
    while len(hits) < limit:
        j = mm.find(needle, pos)
        if j < 0:
            break
        hits.append(j)
        pos = j + 1
    return hits


def clubish(v: int, *, job: int) -> bool:
    return CLUB_LO <= v <= CLUB_HI and v not in (job, PARENT) and v != 0xFFFFFFFF


def scan_job_sites(mm: mmap.mmap, job: int, *, radius: int = 128) -> list[dict]:
    jb = struct.pack("<I", job)
    sites = []
    for off in find_all(mm, jb, limit=120):
        lo, hi = max(0, off - 8), min(len(mm), off + radius)
        window = mm[lo:hi]
        motifs = []
        k = 0
        while True:
            i = window.find(b"\x64\xff", k)
            if i < 0:
                break
            # relative to job start
            rel = (lo + i) - off
            if -8 <= rel <= 96:
                kind = window[i + 2] if i + 2 < len(window) else None
                motifs.append((rel, kind))
            k = i + 1
        dups: list[tuple[int, int]] = []
        singles: list[tuple[int, int]] = []
        for rel in range(-8, radius - 3):
            abs_off = off + rel
            if abs_off < 0 or abs_off + 8 > len(mm):
                continue
            a = struct.unpack_from("<I", mm, abs_off)[0]
            b = struct.unpack_from("<I", mm, abs_off + 4)[0]
            if a == b and clubish(a, job=job):
                dups.append((rel, a))
            elif clubish(a, job=job) and rel >= 0:
                singles.append((rel, a))
        # FF-pad before job? (common employment header)
        pre = mm[max(0, off - 4) : off]
        sites.append(
            {
                "off": off,
                "motifs": motifs,
                "dups": dups[:12],
                "singles": singles[:20],
                "pre": pre.hex(),
                "has26": any(k == 0x26 for _, k in motifs),
                "has24": any(k == 0x24 for _, k in motifs),
                "has25": any(k == 0x25 for _, k in motifs),
            }
        )
    return sites


def score_site(s: dict) -> int:
    sc = 0
    if s["has26"]:
        sc += 50
    if s["has24"]:
        sc += 10
    if s["has25"]:
        sc += 8
    if s["dups"]:
        sc += 15
    if s["pre"] in ("00000000", "ffffffff", "02000000"):
        sc += 2
    # prefer motif close after job
    for rel, kind in s["motifs"]:
        if 8 <= rel <= 48 and kind in (0x24, 0x25, 0x26):
            sc += 20
            break
    return sc


def motif_first_detect(
    mm: mmap.mmap,
    jobs: set[int],
    *,
    kinds: set[int],
    back_lo: int = 8,
    back_hi: int = 48,
) -> dict[int, dict]:
    """Generalize product detect_loaned_out_jobs across motif third bytes."""
    out: dict[int, dict] = {}
    for kind in kinds:
        motif = bytes((0x64, 0xFF, kind))
        pos = 0
        while True:
            j = mm.find(motif, pos)
            if j < 0:
                break
            matched: int | None = None
            back_used = None
            for back in range(back_lo, back_hi + 1):
                start = j - back
                if start < 0:
                    continue
                job = struct.unpack_from("<I", mm, start)[0]
                if job in jobs:
                    matched = job
                    back_used = back
                    break
            if matched is not None and matched not in out:
                loan_club = None
                loan_rel = None
                hi = min(len(mm), j + 96)
                for off in range(j, hi - 7):
                    a = struct.unpack_from("<I", mm, off)[0]
                    b = struct.unpack_from("<I", mm, off + 4)[0]
                    if (
                        a == b
                        and CLUB_LO <= a <= CLUB_HI
                        and a != PARENT
                        and a != matched
                    ):
                        loan_club = a
                        loan_rel = off - j
                        break
                out[matched] = {
                    "kind": kind,
                    "motifAt": j,
                    "back": back_used,
                    "loanClub": loan_club,
                    "loanRel": loan_rel,
                }
            pos = j + 1
    return out


def resolve_club_ids_near_names(mm: mmap.mmap) -> dict[str, list[tuple[int, int]]]:
    """
    For each club name needle, find string hits and collect nearby clubish u32s
    that also appear as duplicated pairs (club object signature).
    """
    resolved: dict[str, list[tuple[int, int]]] = {}
    for label, needles in NAME_NEEDLES.items():
        cand_counts: Counter[int] = Counter()
        samples: list[tuple[int, int]] = []
        for needle in needles:
            for off in find_all(mm, needle, limit=40):
                for rel in range(-64, 128, 4):
                    abs_off = off + rel
                    if abs_off < 0 or abs_off + 8 > len(mm):
                        continue
                    a = struct.unpack_from("<I", mm, abs_off)[0]
                    b = struct.unpack_from("<I", mm, abs_off + 4)[0]
                    if a == b and CLUB_LO <= a <= CLUB_HI and a != PARENT:
                        cand_counts[a] += 1
                        if len(samples) < 8:
                            samples.append((abs_off, a))
        top = cand_counts.most_common(8)
        resolved[label] = [(cid, n) for cid, n in top]
    return resolved


def hexdump(mm: mmap.mmap, center: int, radius: int = 48) -> list[str]:
    lo, hi = max(0, center - radius), min(len(mm), center + radius)
    lines = []
    for i in range(lo, hi, 16):
        chunk = mm[i : min(i + 16, hi)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        mark = ""
        if i <= center < i + 16:
            mark = " <<"
        lines.append(f"  {i:10d}: {hx}{mark}")
    return lines


def main() -> int:
    if not BIN.exists() or not EXTRACT.exists():
        print("need live-0112 decomp + extract")
        return 1
    data = load_extract()
    by_unit = players_by_unit(data)
    lines: list[str] = [
        "# T004B spike-loan-ii-u19",
        f"parent={PARENT} bin={BIN.name} bytes={BIN.stat().st_size}",
        "",
    ]

    # Build control job sets (at-club II/U19: no GT loan names)
    gt_jobs = {j for *_, j, _ in [(a, b, c, d, e) for a, b, c, d, e in GT]}
    # unpack properly
    gt_jobs = {t[3] for t in GT}
    ctrl_ii = [
        (p.get("name"), int(p["jobId"]))
        for p in by_unit["II"]
        if int(p["jobId"]) not in gt_jobs and not p.get("loan")
    ][:8]
    ctrl_u19 = [
        (p.get("name"), int(p["jobId"]))
        for p in by_unit["U19"]
        if int(p["jobId"]) not in gt_jobs and not p.get("loan")
    ][:8]
    all_jobs = (
        {int(p["jobId"]) for p in by_unit["FT"]}
        | {int(p["jobId"]) for p in by_unit["II"]}
        | {int(p["jobId"]) for p in by_unit["U19"]}
    )

    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            lines.append("## club-name → candidate clubIds (dup near string)")
            resolved = resolve_club_ids_near_names(mm)
            for label, tops in resolved.items():
                lines.append(f"  {label}: {tops}")
            # Flatten best guesses
            guess: dict[str, int | None] = {}
            for label, tops in resolved.items():
                guess[label] = tops[0][0] if tops else None
            if KNOWN_LOAN.get("Legia"):
                guess["Legia"] = KNOWN_LOAN["Legia"]
            lines.append(f"  guess={guess}")
            lines.append("")

            lines.append("## per-GT best job site (motif / dups)")
            best_by_job: dict[int, dict] = {}
            for unit, name, uid, job, club in GT:
                sites = scan_job_sites(mm, job)
                ranked = sorted(sites, key=score_site, reverse=True)
                best = ranked[0] if ranked else None
                best_by_job[job] = best or {}
                gclub = guess.get(club)
                hit_guess = None
                if best and gclub is not None:
                    for rel, cid in best.get("dups", []) + best.get("singles", []):
                        if cid == gclub:
                            hit_guess = (rel, cid)
                            break
                lines.append(
                    f"  {unit} {name} job={job} uid={uid} →{club} guessClub={gclub} "
                    f"sites={len(sites)} bestScore={score_site(best) if best else None}"
                )
                if best:
                    lines.append(
                        f"    @{best['off']} pre={best['pre']} "
                        f"motifs={[(r, f'0x{k:02x}' if k is not None else None) for r,k in best['motifs']]} "
                        f"dups={best['dups'][:6]} guessHit={hit_guess}"
                    )
                    # dump around best motif if any, else job
                    center = best["off"]
                    if best["motifs"]:
                        center = best["off"] + best["motifs"][0][0]
                    lines.extend(hexdump(mm, center, 40))
                lines.append("")

            lines.append("## motif-first detect sweeps (product-style)")
            sweeps = [
                ("64ff26 only back8-48", {0x26}, 8, 48),
                ("64ff24 only back8-48", {0x24}, 8, 48),
                ("64ff24/25/26 back8-48", {0x24, 0x25, 0x26}, 8, 48),
                ("64ff24/25/26 back8-64", {0x24, 0x25, 0x26}, 8, 64),
                ("64ff24/26 back8-56", {0x24, 0x26}, 8, 56),
            ]
            for label, kinds, blo, bhi in sweeps:
                hit = motif_first_detect(
                    mm, all_jobs, kinds=kinds, back_lo=blo, back_hi=bhi
                )
                lines.append(f"### {label} → {len(hit)} jobs tagged")
                # GT outcomes
                for unit, name, uid, job, club in GT:
                    h = hit.get(job)
                    mark = "HIT" if h else "miss"
                    lines.append(
                        f"  {mark} {unit} {name} job={job} {h} expect={club}/{guess.get(club)}"
                    )
                # false positives among controls
                fp_ii = [c for c in ctrl_ii if c[1] in hit]
                fp_u19 = [c for c in ctrl_u19 if c[1] in hit]
                fp_ft = [
                    (p.get("name"), int(p["jobId"]))
                    for p in by_unit["FT"]
                    if int(p["jobId"]) in hit
                    and int(p["jobId"]) not in gt_jobs
                    and not (p.get("loan") or {}).get("status") == "loanedOut"
                ][:12]
                lines.append(
                    f"  FP sample II={[(n, j, hit[j]) for n, j in fp_ii[:5]]} "
                    f"U19={[(n, j, hit[j]) for n, j in fp_u19[:5]]} "
                    f"FT_atclub={[(n, j, hit[j]) for n, j in fp_ft[:5]]}"
                )
                lines.append("")

            # Targeted: for each GT, does guessed clubId appear as dup after ANY 64ff2x near job?
            lines.append("## targeted: guessClub as post-motif dup near job")
            for unit, name, uid, job, club in GT:
                gclub = guess.get(club)
                if gclub is None:
                    lines.append(f"  {name}: no guess clubId for {club}")
                    continue
                sites = scan_job_sites(mm, job, radius=160)
                found = []
                for s in sites:
                    for rel, kind in s["motifs"]:
                        # scan dups after motif
                        motif_abs = s["off"] + rel
                        for drel in range(0, 96, 4):
                            abs_off = motif_abs + drel
                            if abs_off + 8 > len(mm):
                                break
                            a = struct.unpack_from("<I", mm, abs_off)[0]
                            b = struct.unpack_from("<I", mm, abs_off + 4)[0]
                            if a == b == gclub:
                                found.append(
                                    {
                                        "jobOff": s["off"],
                                        "motifRel": rel,
                                        "kind": kind,
                                        "dupRelFromMotif": drel,
                                    }
                                )
                lines.append(
                    f"  {unit} {name} guess={gclub} matches={len(found)} sample={found[:3]}"
                )

            # Also: search job+uid employment records for secondary club
            lines.append("")
            lines.append("## employment-tag (0x08-0x0b 02 job 02 uid) secondary clubs ±96")
            for unit, name, uid, job, club in GT:
                needle = (
                    b"\x02"
                    + struct.pack("<I", job)
                    + b"\x02"
                    + struct.pack("<I", uid)
                )
                emp_hits = []
                for off in find_all(mm, needle, limit=30):
                    # tag byte at off-1? pattern was EMP_TAG + 02 + job + 02 + uid
                    tag = mm[off - 1] if off >= 1 else None
                    clubs = []
                    for rel in range(-96, 96, 4):
                        abs_off = off + rel
                        if abs_off < 0 or abs_off + 4 > len(mm):
                            continue
                        v = struct.unpack_from("<I", mm, abs_off)[0]
                        if clubish(v, job=job):
                            clubs.append((rel, v))
                    emp_hits.append({"off": off, "tag": tag, "clubs": clubs[:15]})
                # summarize distinct club ids
                dist: Counter[int] = Counter()
                for h in emp_hits:
                    for _, v in h["clubs"]:
                        dist[v] += 1
                lines.append(
                    f"  {unit} {name} empSites={len(emp_hits)} topClubs={dist.most_common(8)} "
                    f"guess={guess.get(club)} inTop={guess.get(club) in dist}"
                )

        finally:
            mm.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} lines={len(lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
