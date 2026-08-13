#!/usr/bin/env python3
"""Compare Sipho job-object (±128) vs at-club controls — loan club field lock."""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "dynamics-b.fm"
EXTRACT = ROOT / "tmp" / "dynamics-b-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-jobobj-sipho-vs-control.txt"
PARENT, LOAN = 920, 1456


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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-jcmp-", suffix=".bin")
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


def find_job_sites(mm: mmap.mmap, job: int) -> list[int]:
    """Prefer sites with 64 ff motif nearby (job/squad object), not random noise."""
    jb = struct.pack("<I", job)
    hits = []
    pos = 0
    while len(hits) < 80:
        j = mm.find(jb, pos)
        if j < 0:
            break
        w = mm[max(0, j - 64) : j + 128]
        score = 0
        if b"\x64\xff" in w:
            score += 3
        if struct.pack("<I", LOAN) in w or struct.pack("<I", PARENT) in w:
            score += 2
        if b"\xff\xff\xff\xff" in w:
            score += 1
        hits.append((score, j))
        pos = j + 1
    hits.sort(reverse=True)
    return [j for s, j in hits if s >= 2][:12] or [j for s, j in hits[:6]]


def dump_site(mm: mmap.mmap, job: int, off: int, label: str) -> list[str]:
    lines = [f"### {label} job={job} @{off}"]
    lo, hi = max(0, off - 32), min(len(mm), off + 160)
    # annotate interesting u32s
    for base in range(lo, hi, 16):
        chunk = mm[base : min(base + 16, hi)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        mark = ">" if base <= off < base + 16 else " "
        notes = []
        for i in range(0, len(chunk) - 3, 4):
            abs_i = base + i
            if abs_i + 4 > hi:
                break
            v = struct.unpack_from("<I", mm, abs_i)[0]
            rel = abs_i - off
            if v == job:
                notes.append(f"job@{rel:+d}")
            elif v == PARENT:
                notes.append(f"PARENT@{rel:+d}")
            elif v == LOAN:
                notes.append(f"LOAN@{rel:+d}")
            elif v == 0:
                notes.append(f"0@{rel:+d}")
        note = ("  " + ",".join(notes[:6])) if notes else ""
        lines.append(f"  {mark}{base:08x}  {hx}{note}")
    # extract candidate club-ish fields at fixed deltas from job
    lines.append("  fixed-delta u32 from job:")
    for d in range(0, 128, 4):
        if off + d + 4 <= len(mm):
            v = struct.unpack_from("<I", mm, off + d)[0]
            tag = ""
            if v == PARENT:
                tag = " PARENT"
            elif v == LOAN:
                tag = " LOAN"
            elif 50 <= v <= 100_000:
                tag = " clubish"
            elif v == 0:
                tag = " zero"
            elif v == 0xFFFFFFFF:
                tag = " ff"
            if tag:
                lines.append(f"    +{d:3d} = {v}{tag}")
    return lines


def main() -> int:
    mod = load_extractor()
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    sipho = next(p for p in data["players"] if "Sithole" in (p.get("name") or ""))
    controls = [
        next(p for p in data["players"] if "ller" in (p.get("name") or "") and "Robert" in (p.get("name") or "")),
        next(p for p in data["players"] if "Tusjak" in (p.get("name") or "")),
        next(p for p in data["players"] if "Kizza" in (p.get("name") or "")),
    ]
    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    lines = ["# job-object Sipho vs at-club", ""]
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for label, p in [("SIPHO-LOANED", sipho)] + [
                    (f"CTRL-{p.get('name')}", p) for p in controls
                ]:
                    job = int(p["jobId"])
                    sites = find_job_sites(mm, job)
                    lines.append(f"## {label} sites={sites}")
                    for s in sites[:4]:
                        lines.extend(dump_site(mm, job, s, label))
                        lines.append("")
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text[:14000])
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
