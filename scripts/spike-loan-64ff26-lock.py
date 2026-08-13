#!/usr/bin/env python3
"""
Lock loan marker: Sipho job site has `64 ff 26` then loanClub 1456×2.
Scan all FT+II jobs for 64 ff 2x motifs and nearby foreign clubIds.
"""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "dynamics-b.fm"
EXTRACT = ROOT / "tmp" / "dynamics-b-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-64ff26-lock.txt"
PARENT, LOAN = 920, 1456
CLUB_LO, CLUB_HI = 50, 100_000


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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-64ff-", suffix=".bin")
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


def analyze_job(mm: mmap.mmap, job: int, name: str) -> dict:
    jb = struct.pack("<I", job)
    best = None
    pos = 0
    while True:
        j = mm.find(jb, pos)
        if j < 0:
            break
        # look for 64 ff within +0..+48 after job
        window = mm[j : j + 96]
        motifs = []
        k = 0
        while True:
            i = window.find(b"\x64\xff", k)
            if i < 0 or i > 48:
                break
            kind = window[i + 2] if i + 2 < len(window) else None
            motifs.append((i, kind))
            k = i + 1
        clubs = []
        for off in range(0, 96, 4):
            if j + off + 4 > len(mm):
                break
            v = struct.unpack_from("<I", mm, j + off)[0]
            if CLUB_LO <= v <= CLUB_HI and v not in (job,):
                clubs.append((off, v))
        score = 0
        if motifs:
            score += 5
            if any(k == 0x26 for _, k in motifs):
                score += 10
        if any(v == LOAN for _, v in clubs):
            score += 20
        if any(v == PARENT for _, v in clubs):
            score += 3
        cand = {
            "off": j,
            "score": score,
            "motifs": motifs,
            "clubs": clubs,
            "loanAt": next((off for off, v in clubs if v == LOAN), None),
            "parentAt": next((off for off, v in clubs if v == PARENT), None),
        }
        if best is None or cand["score"] > best["score"]:
            best = cand
        pos = j + 1
    return {"name": name, "job": job, "best": best}


def main() -> int:
    mod = load_extractor()
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    players = [(p.get("name"), int(p["jobId"]), "FT") for p in data["players"]]
    players += [
        (p.get("name"), int(p["jobId"]), "II")
        for p in data["reserves"]["players"]
    ]
    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    lines = ["# 64 ff 2x loan motif lock", ""]
    motif_hist: Counter[int] = Counter()
    loaned = []
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for name, job, unit in players:
                    row = analyze_job(mm, job, name or "?")
                    best = row["best"]
                    if not best:
                        lines.append(f"  {unit} {name}: NO site")
                        continue
                    for _i, kind in best["motifs"]:
                        if kind is not None:
                            motif_hist[kind] += 1
                    has26 = any(k == 0x26 for _, k in best["motifs"])
                    has_loan_foreign = any(
                        v not in (PARENT,) and 50 <= v <= 100_000
                        for off, v in best["clubs"]
                        if off >= 32
                    )
                    marker = ""
                    if has26:
                        marker = " <<64ff26"
                    if best["loanAt"] is not None:
                        marker += " <<LEGIA"
                    lines.append(
                        f"  {unit} {name} job={job} @{best['off']} "
                        f"motifs={[(i, f'0x{k:02x}' if k is not None else None) for i,k in best['motifs']]} "
                        f"clubs={best['clubs'][:8]}{marker}"
                    )
                    if has26 or best["loanAt"] is not None:
                        loaned.append(row)
                lines.append("")
                lines.append(f"## motif kind histogram: {dict(sorted(motif_hist.items()))}")
                lines.append(f"## flagged (64ff26 or Legia near): {len(loaned)}")
                for row in loaned:
                    b = row["best"]
                    lines.append(
                        f"  {row['name']} job={row['job']} @{b['off']} "
                        f"loanAt={b['loanAt']} parentAt={b['parentAt']} clubs={b['clubs']}"
                    )
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
