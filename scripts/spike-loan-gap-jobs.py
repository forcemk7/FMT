#!/usr/bin/env python3
"""Inspect unresolved squad jobIds (FT/II gaps) — likely loaned-out / ghost slots."""

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
OUT = ROOT / "tmp" / "fm-spike" / "loan-gap-jobs.txt"
GAP_JOBS = [215122, 382374, 315711, 317202, 351592]
# Known clubIds
CLUBS = {
    920: "Schalke",
    13217: "Schalke II club",
}


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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-gap-", suffix=".bin")
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


def hexdump(mm: mmap.mmap, off: int, radius: int = 64) -> list[str]:
    lo = max(0, off - radius)
    hi = min(len(mm), off + radius)
    rows = []
    for base in range(lo, hi, 16):
        chunk = mm[base : min(base + 16, hi)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        mark = "<<" if base <= off < base + 16 else "  "
        rows.append(f"  {mark}{base:08x}  {hx:<47}  {asc}")
    return rows


def main() -> int:
    mod = load_extractor()
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    schalke_jobs = {int(p["jobId"]) for p in data["players"]} | {
        int(p["jobId"]) for p in data["reserves"]["players"]
    }
    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    lines = [f"# gap job inspect · {SAVE.name}", f"gaps={GAP_JOBS}", ""]
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for job in GAP_JOBS:
                    jb = struct.pack("<I", job)
                    hits = []
                    pos = 0
                    while len(hits) < 40:
                        j = mm.find(jb, pos)
                        if j < 0:
                            break
                        hits.append(j)
                        pos = j + 1
                    lines.append(f"## job={job} hits={len(hits)} (showing ≤12)")
                    # classify hits
                    for j in hits[:12]:
                        pre = mm[max(0, j - 2) : j]
                        tag = pre[0] if len(pre) == 2 and pre[1] == 0x02 else None
                        # nearby club ids?
                        window = mm[max(0, j - 64) : j + 64]
                        club_near = []
                        for cid, label in CLUBS.items():
                            if struct.pack("<I", cid) in window:
                                club_near.append(label)
                        # ascii names nearby
                        names = []
                        for k in range(max(0, j - 128), min(len(mm) - 4, j + 128)):
                            ln = mm[k]
                            if 3 <= ln <= 20 and k + 1 + ln <= len(mm):
                                chunk = mm[k + 1 : k + 1 + ln]
                                if all(32 <= b < 127 for b in chunk) and chunk[:1].isalpha():
                                    names.append(chunk.decode("ascii", errors="ignore"))
                        lines.append(
                            f"  @{j} tag={f'{tag:02x}' if tag is not None else '--'} "
                            f"clubsNear={club_near or '-'} namesNear={names[:6]}"
                        )
                        if tag is not None:
                            lines.extend(hexdump(mm, j, 48))
                    # Also try alternate employment layouts: job then uid without 02 separator?
                    # Search 0b02 <job> anywhere already covered via tag classify.
                    lines.append("")
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8")[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
