#!/usr/bin/env python3
"""T007: resolve Kasprzak/Kirsch near name ASCII → job/uid."""
from __future__ import annotations

import json
import mmap
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"

raw = EXTRACT.read_bytes()
for enc in ("utf-16", "utf-8-sig", "utf-8"):
    try:
        data = json.loads(raw.decode(enc))
        break
    except Exception:
        pass

jobs = {}
uids = {}
for group in (
    data.get("players") or [],
    (data.get("reserves") or {}).get("players") or [],
    (data.get("u19") or {}).get("players") or [],
):
    for p in group:
        if p.get("jobId"):
            jobs[int(p["jobId"])] = p.get("name")
        if p.get("uid"):
            uids[int(p["uid"])] = p.get("name")

with BIN.open("rb") as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

for name in (b"Kasprzak", b"Kirsch"):
    print(f"\n## {name!r}")
    pos = 0
    n = 0
    while n < 8:
        j = mm.find(name, pos)
        if j < 0:
            break
        n += 1
        print(f"  @{j}")
        # scan ±128 for squad job or person uid
        lo, hi = max(0, j - 128), min(len(mm), j + 128)
        found_jobs = []
        found_uids = []
        for off in range(lo, hi - 3):
            val = struct.unpack_from("<I", mm, off)[0]
            if val in jobs:
                found_jobs.append((off - j, val, jobs[val]))
            if val in uids and 1_000_000_000 < val < 2_200_000_000:
                found_uids.append((off - j, val, uids[val]))
        print(f"    jobs near: {found_jobs[:8]}")
        print(f"    uids near: {found_uids[:8]}")
        # also any high uid-looking values
        pos = j + 1

mm.close()
