#!/usr/bin/env python3
"""T007: motif→job collisions; find true loan clubs for Abbe et al."""

from __future__ import annotations

import importlib.util
import json
import mmap
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-t007-collisions.txt"
PARENT = 920

FOCUS = {
    366246: "Abbe",
    364668: "Resvanis",
    352031: "Dunkel",
    236310: "Zetzmann",
    437615: "Vlad",
    382267: "Sipho",
    506980: "Braescu",
    506986: "Manole",
    365838: "Ozturk",
    538884: "Millwood",
    538997: "Davyskiba",
    558298: "Kraft",
    315711: "Gorrissen",
    317202: "Risse",
    351592: "Perez",
}


def load_json(path: Path) -> dict:
    raw = path.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            continue
    raise SystemExit(f"cannot decode {path}")


def load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    lines: list[str] = []
    data = load_json(EXTRACT)
    eft = load_eft()
    jobs: set[int] = set()
    by_job: dict[int, str] = {}
    for p in data.get("players") or []:
        if p.get("jobId"):
            jobs.add(int(p["jobId"]))
            by_job[int(p["jobId"])] = f"FT:{p.get('name')}"
    for key, u in (("reserves", "II"), ("u19", "U19")):
        for p in (data.get(key) or {}).get("players") or []:
            if p.get("jobId"):
                jobs.add(int(p["jobId"]))
                by_job[int(p["jobId"])] = f"{u}:{p.get('name')}"
    # gap jobs from T004C
    jobs |= set(FOCUS)

    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    # For each valid loan motif, list ALL squad jobs in lookback 8..128
    lines.append("## Motifs with >1 squad job in lookback OR focus job present")
    pos = 0
    motif_n = 0
    while True:
        j = mm.find(eft.LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        loan_club = eft._parse_loan_out_template(mm, j, PARENT)
        if loan_club is None:
            pos = j + 1
            continue
        motif_n += 1
        found: list[tuple[int, int, str]] = []
        for back in range(8, 129):
            start = j - back
            if start < 0:
                continue
            job = struct.unpack_from("<I", mm, start)[0]
            if job in jobs and job != loan_club:
                found.append((back, job, by_job.get(job, FOCUS.get(job, "?"))))
        focus_hit = [x for x in found if x[1] in FOCUS]
        if len(found) > 1 or focus_hit:
            lines.append(
                f"motif@{j} club={loan_club} kind={mm[j+2]:02x} jobs={found}"
            )
        pos = j + 1
    lines.append(f"valid motifs scanned={motif_n}")

    # For each FOCUS job: nearest valid loan motif (any direction within 2KB)
    lines.append("\n## Nearest valid loan motif per FOCUS job")
    # collect all valid motifs
    motifs: list[tuple[int, int]] = []
    pos = 0
    while True:
        j = mm.find(eft.LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        club = eft._parse_loan_out_template(mm, j, PARENT)
        if club is not None:
            motifs.append((j, club))
        pos = j + 1

    for job, label in FOCUS.items():
        jb = struct.pack("<I", job)
        sites = []
        p = 0
        while True:
            s = mm.find(jb, p)
            if s < 0:
                break
            sites.append(s)
            p = s + 1
            if len(sites) > 200:
                break
        best = None
        for site in sites:
            for mj, club in motifs:
                dist = mj - site  # positive = motif after job (lookback = dist)
                if 8 <= dist <= 200:
                    cand = (dist, site, mj, club)
                    if best is None or cand[0] < best[0]:
                        best = cand
        if best:
            lines.append(
                f"  {label} job={job} nearest_back={best[0]} "
                f"job@{best[1]} motif@{best[2]} club={best[3]} sites={len(sites)}"
            )
        else:
            lines.append(f"  {label} job={job} NO motif in back 8..200 sites={len(sites)}")

    # Prefer longest lookback? Or prefer job that appears ASAP before motif
    # with pre4==0 filter from T004B
    lines.append("\n## Detect variants")
    variants = [
        ("product", 57, False, False),
        ("hi73", 73, False, False),
        ("hi80", 80, False, False),
        ("hi73_pre4", 73, True, False),
        ("hi80_pre4", 80, True, False),
        ("hi80_pre4_farthest", 80, True, True),
        ("hi96_pre4", 96, True, False),
    ]
    for name, hi, pre4, farthest in variants:
        out: dict[int, int] = {}
        pos = 0
        while True:
            j = mm.find(eft.LOAN_OUT_MOTIF_PREFIX, pos)
            if j < 0:
                break
            if pre4 and j >= 4 and mm[j - 4 : j] != b"\x00" * 4:
                pos = j + 1
                continue
            loan_club = eft._parse_loan_out_template(mm, j, PARENT)
            if loan_club is None:
                pos = j + 1
                continue
            matches: list[tuple[int, int]] = []
            for back in range(8, hi + 1):
                start = j - back
                if start < 0:
                    continue
                job = struct.unpack_from("<I", mm, start)[0]
                if job in jobs and job != loan_club:
                    matches.append((back, job))
            if not matches:
                pos = j + 1
                continue
            pick = matches[-1] if farthest else matches[0]
            job = pick[1]
            if job not in out:
                out[job] = loan_club
            pos = j + 1
        lines.append(f"\n### {name} hits={len(out)}")
        for job, club in sorted(out.items()):
            lab = FOCUS.get(job) or by_job.get(job, "?")
            mark = " *" if job in FOCUS else ""
            lines.append(f"  {lab} job={job} club={club}{mark}")
        for job, lab in FOCUS.items():
            if job not in out:
                lines.append(f"  MISS {lab} job={job}")

    mm.close()
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
