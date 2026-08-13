#!/usr/bin/env python3
"""T007 spike: Abbe/lookback + Overview Loans GT vs detect on live-0112."""

from __future__ import annotations

import importlib.util
import json
import mmap
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-t007-abbe.txt"
PARENT = 920

# Audit Overview→Loans misses + known tagged + U19 Kraft
GT_NAMES = {
    "Lukas Abbe",
    "Thanos Resvanis",
    "Danny Dunkel",
    "Kasprzak",  # partial
    "Alexandr Davyskiba",
    "Ben Millwood",
    "Carsten Kraft",
    "Miguel Pérez",
    "Miguel Perez",
    "Sipho Sithole",
    "Moise Vlad-Paul",
    "Robert Brăescu",
    "Robert Braescu",
    "Andrei Manole",
    "Recep Öztürk",
    "Recep Ozturk",
    "Lion Görrissen",
    "Lion Gorrissen",
    "Landri Risse",
    "Nino Zetzmann",
    "Wolfgang Kirsch",
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


def iter_players(data: dict):
    for p in data.get("players") or []:
        yield "FT", p
    for key, unit in (("reserves", "II"), ("u19", "U19")):
        for p in (data.get(key) or {}).get("players") or []:
            yield unit, p


def name_match(name: str) -> bool:
    n = name or ""
    if n in GT_NAMES:
        return True
    low = n.lower()
    for g in GT_NAMES:
        if g.lower() in low or low in g.lower():
            return True
    return False


def probe_lookback(mm: mmap.mmap, eft, jobs: set[int], hi: int) -> dict[int, tuple]:
    """Like detect but returns (loanClub, back, motif_at) and uses custom hi."""
    out: dict[int, tuple] = {}
    pos = 0
    while True:
        j = mm.find(eft.LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        loan_club = eft._parse_loan_out_template(mm, j, PARENT)
        if loan_club is None:
            pos = j + 1
            continue
        matched: int | None = None
        matched_back: int | None = None
        for back in range(eft.LOAN_LOOKBACK_LO, hi + 1):
            start = j - back
            if start < 0:
                continue
            job = struct.unpack_from("<I", mm, start)[0]
            if job in jobs and job != loan_club:
                matched = job
                matched_back = back
                break
        if matched is not None and matched not in out:
            out[matched] = (loan_club, matched_back, j)
        pos = j + 1
    return out


def main() -> None:
    lines: list[str] = []
    data = load_json(EXTRACT)
    eft = load_eft()
    jobs: set[int] = set()
    by_job: dict[int, tuple] = {}
    for unit, p in iter_players(data):
        job = int(p.get("jobId") or 0)
        if not job:
            continue
        jobs.add(job)
        by_job[job] = (
            unit,
            p.get("name"),
            p.get("uid"),
            (p.get("loan") or {}).get("status"),
            (p.get("loan") or {}).get("loanClubId"),
        )

    lines.append("## Extract GT-ish + loanedOut")
    loaned = 0
    for unit, p in iter_players(data):
        loan = p.get("loan") or {}
        if loan.get("status") == "loanedOut":
            loaned += 1
        if name_match(p.get("name") or "") or loan.get("status") == "loanedOut":
            lines.append(
                f"  {unit:3} job={p.get('jobId')} uid={p.get('uid')} "
                f"loan={loan.get('status')} club={loan.get('loanClubId')} "
                f"name={p.get('name')!r}"
            )
    lines.append(f"loanedOut count={loaned} jobs={len(jobs)}")

    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    # Current product detect
    hit57 = eft.detect_loaned_out_jobs(mm, jobs, PARENT)
    lines.append(f"\n## Product detect lookback<=57 hits={len(hit57)}")
    for job, club in sorted(hit57.items()):
        meta = by_job.get(job)
        lines.append(f"  job={job} club={club} meta={meta}")

    # Extended lookbacks
    for hi in (57, 69, 73, 80, 96, 128):
        hit = probe_lookback(mm, eft, jobs, hi)
        # Focus GT jobs
        focus = {
            366246: "Abbe",
            364668: "Resvanis",
            352031: "Dunkel",
            538884: "Millwood",
            437615: "Vlad",
            382267: "Sipho",
        }
        lines.append(f"\n## lookback_hi={hi} total_hits={len(hit)}")
        for job, label in focus.items():
            if job in hit:
                lines.append(f"  HIT {label} job={job} → {hit[job]}")
            else:
                lines.append(f"  MISS {label} job={job}")
        # New hits vs 57
        if hi > 57:
            new = {j: hit[j] for j in hit if j not in hit57}
            lines.append(f"  NEW vs 57: {len(new)}")
            for job, info in sorted(new.items(), key=lambda x: x[1][1] or 0):
                meta = by_job.get(job)
                lines.append(f"    job={job} {info} meta={meta}")

    # Dump motif hex around Abbe candidate from prior spike
    motif = 56322046
    lines.append(f"\n## Hex around motif {motif} (Abbe prior)")
    if 0 <= motif < len(mm) - 40:
        chunk = mm[motif - 80 : motif + 40]
        lines.append(chunk.hex(" "))
        # find job u32 366246 in lookback window
        jb = struct.pack("<I", 366246)
        for back in range(8, 129):
            start = motif - back
            if start >= 0 and mm[start : start + 4] == jb:
                lines.append(f"  Abbe job at back={back}")
        club = eft._parse_loan_out_template(mm, motif, PARENT)
        lines.append(f"  parse_template → {club}")

    motif2 = 56322846
    lines.append(f"\n## Hex around motif {motif2} (Resvanis prior)")
    if 0 <= motif2 < len(mm) - 40:
        club = eft._parse_loan_out_template(mm, motif2, PARENT)
        lines.append(f"  parse_template → {club}")
        jb = struct.pack("<I", 364668)
        for back in range(8, 129):
            start = motif2 - back
            if start >= 0 and mm[start : start + 4] == jb:
                lines.append(f"  Resvanis job at back={back}")

    mm.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)
    print("\n".join(lines[:80]))


if __name__ == "__main__":
    main()
