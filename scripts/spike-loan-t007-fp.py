#!/usr/bin/env python3
"""T007: FP check at-club controls with lookback hi=73/80 per-unit."""
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
CTRL = {106935, 334108, 285346, 364642, 113517}  # Paco/Bandeira/Kizza/Jones/Seimen


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
        for back in range(8, hi + 1):
            start = j - back
            if start < 0:
                continue
            job = struct.unpack_from("<I", mm, start)[0]
            if job in jobs and job != club:
                if job not in out:
                    out[job] = club
                break
        pos = j + 1
    return out


eft = load_eft()
data = load_json(EXTRACT)
ft = {int(p["jobId"]) for p in data.get("players") or [] if p.get("jobId")}
with BIN.open("rb") as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
for hi in (73, 80, 96, 128):
    hit = detect_hi(mm, eft, ft, hi)
    fps = sorted(j for j in hit if j in CTRL)
    extras = sorted(
        (j, hit[j])
        for j in hit
        if j
        not in {
            382267,
            437615,
            366246,
            364668,
            315711,
        }
    )
    print(f"hi={hi} ft_hits={len(hit)} ctrl_fp={fps} other={extras}")
mm.close()
