#!/usr/bin/env python3
"""T007: validate closest+farthest detect vs full roster FP + Overview GT."""

from __future__ import annotations

import importlib.util
import json
import mmap
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-t007-validate.txt"
PARENT = 920

# In-game Overview→Loans audit (STATUS): 13 outgoing.
# Named from audit + T004 GT. Exact 13 list reconstructed for close-out.
OVERVIEW_LOANS = [
    ("Sipho Sithole", 2002282525, 382267, True),
    ("Moise Vlad-Paul", 2002330407, 437615, True),
    ("Nino Zetzmann", 2002136568, 236310, True),
    ("Robert Braescu", 2002390854, 506980, True),
    ("Andrei Manole", 2002390860, 506986, True),
    ("Recep Ozturk", 2002266096, 365838, True),
    ("Lion Gorrissen", 2002215969, 315711, False),  # gap FT
    ("Landri Risse", 2002217460, 317202, False),  # gap II
    ("Miguel Perez", 2002251850, 351592, False),  # gap II
    ("Lukas Abbe", 2002266504, 366246, True),
    ("Thanos Resvanis", 2002264926, 364668, True),
    ("Danny Dunkel", 2002252289, 352031, True),
    ("Ben Millwood", 2002422274, 538884, True),  # known motif hole
]

# Extra suspects from audit text
EXTRA = [
    ("Alexandr Davyskiba", 2002422387, 538997, True),
    ("Carsten Kraft", 2002441688, 558298, True),
    ("Thami Mhlongo", 2002282452, 382194, True),
]


def load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def load_json(path: Path) -> dict:
    raw = path.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            continue
    raise SystemExit(f"cannot decode {path}")


def detect_endpoints(
    mm: mmap.mmap, eft, jobs: set[int], *, hi: int
) -> dict[int, int]:
    """Motif-first; tag closest AND farthest squad job in lookback."""
    out: dict[int, int | None] = {}
    pos = 0
    while True:
        j = mm.find(eft.LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        loan_club = eft._parse_loan_out_template(mm, j, PARENT)
        if loan_club is None:
            pos = j + 1
            continue
        matches: list[int] = []
        for back in range(eft.LOAN_LOOKBACK_LO, hi + 1):
            start = j - back
            if start < 0:
                continue
            job = struct.unpack_from("<I", mm, start)[0]
            if job in jobs and job != loan_club:
                matches.append(job)
        if matches:
            for job in {matches[0], matches[-1]}:
                if job not in out:
                    out[job] = loan_club
        pos = j + 1
    return out


def main() -> None:
    lines: list[str] = []
    eft = load_eft()
    data = load_json(EXTRACT)
    by_job: dict[int, str] = {}
    jobs: set[int] = set()
    roster = []
    for unit, key in (("FT", None), ("II", "reserves"), ("U19", "u19")):
        group = (
            data.get("players") or []
            if key is None
            else (data.get(key) or {}).get("players") or []
        )
        for p in group:
            roster.append((unit, p))
            if p.get("jobId"):
                jobs.add(int(p["jobId"]))
                by_job[int(p["jobId"])] = f"{unit}:{p.get('name')}"
    for jid, nm in ((315711, "FT:Gorrissen"), (317202, "II:Risse"), (351592, "II:Perez")):
        jobs.add(jid)
        by_job[jid] = nm

    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    for hi in (57, 73, 80):
        hit = detect_endpoints(mm, eft, jobs, hi=hi)
        lines.append(f"\n## endpoints hi={hi} hits={len(hit)}")
        # Overview coverage
        for name, uid, job, in_extract in OVERVIEW_LOANS:
            st = "HIT" if job in hit else "MISS"
            club = hit.get(job)
            lines.append(
                f"  {st} {name} job={job} club={club} in_extract={in_extract}"
            )
        for name, uid, job, in_extract in EXTRA:
            st = "HIT" if job in hit else "MISS"
            lines.append(f"  extra {st} {name} job={job} club={hit.get(job)}")
        # FP: anyone tagged who is NOT in overview/extra loan set
        loan_jobs = {j for *_, j, _ in OVERVIEW_LOANS} | {j for *_, j, _ in EXTRA}
        # also allow Mhlongo if tagged
        fps = []
        for job, club in hit.items():
            if job not in loan_jobs:
                fps.append((by_job.get(job, "?"), job, club))
        lines.append(f"  possible FP vs known loan set: {fps}")

    # Kasprzak / Kirsch search in namelist region?
    lines.append("\n## ASCII name hunt Kasprzak/Kirsch")
    for name in (b"Kasprzak", b"Kirsch", b"Davyskiba", b"Abbe"):
        hits = []
        p = 0
        while len(hits) < 5:
            j = mm.find(name, p)
            if j < 0:
                break
            hits.append(j)
            p = j + 1
        lines.append(f"  {name!r} → {hits}")

    # Millwood: any alternate motif family near job sites (64 ff outside 20-30)?
    lines.append("\n## Millwood alternate 64ff near job sites (back/forward 8..120)")
    job = 538884
    jb = struct.pack("<I", job)
    p = 0
    sites = 0
    found = []
    while sites < 300 and len(found) < 20:
        s = mm.find(jb, p)
        if s < 0:
            break
        sites += 1
        for delta in list(range(8, 121)) + list(range(-120, -7)):
            at = s + abs(delta) if delta > 0 else s + delta
            # forward if delta>0: motif after job; backward: motif before
            mj = s + delta if delta > 0 else s + delta
            if mj < 0 or mj + 3 > len(mm):
                continue
            if mm[mj : mj + 2] != b"\x64\xff":
                continue
            kind = mm[mj + 2]
            found.append((s, delta, kind, mj))
        p = s + 1
    lines.append(f"  sites={sites} 64ff near={found[:15]}")

    mm.close()
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
