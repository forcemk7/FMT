#!/usr/bin/env python3
"""T007: per-unit detect with raised lookback (matches extract call pattern)."""
from __future__ import annotations

import importlib.util
import json
import mmap
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
PARENT = 920


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


def detect_hi(mm, eft, jobs, hi):
    out = {}
    pos = 0
    while True:
        j = mm.find(eft.LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        club = eft._parse_loan_out_template(mm, j, PARENT)
        if club is None:
            pos = j + 1
            continue
        matched = None
        for back in range(8, hi + 1):
            start = j - back
            if start < 0:
                continue
            job = struct.unpack_from("<I", mm, start)[0]
            if job in jobs and job != club:
                matched = job
                break
        if matched is not None and matched not in out:
            out[matched] = club
        pos = j + 1
    return out


def main():
    eft = load_eft()
    data = load_json(EXTRACT)
    ft = {int(p["jobId"]) for p in data.get("players") or [] if p.get("jobId")}
    ii = {
        int(p["jobId"])
        for p in (data.get("reserves") or {}).get("players") or []
        if p.get("jobId")
    }
    u19 = {
        int(p["jobId"])
        for p in (data.get("u19") or {}).get("players") or []
        if p.get("jobId")
    }
    # gaps as if T004C resolved them onto lists
    ft |= {315711}
    ii |= {317202, 351592}

    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    for hi in (57, 73, 80):
        print(f"\n## hi={hi}")
        for label, jobs in (("FT", ft), ("II", ii), ("U19", u19)):
            hit = detect_hi(mm, eft, jobs, hi)
            print(f"  {label} hits={len(hit)}")
            for job, club in sorted(hit.items()):
                print(f"    job={job} club={club}")

    mm.close()


if __name__ == "__main__":
    main()
