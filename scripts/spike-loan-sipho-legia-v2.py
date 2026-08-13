#!/usr/bin/env python3
"""Sipho loan v2: larger radii, job-neighborhood, Legia squad overlap."""

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
OUT = ROOT / "tmp" / "fm-spike" / "loan-sipho-legia-v2.txt"
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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-sipho2-", suffix=".bin")
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


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 500) -> list[int]:
    out, pos = [], 0
    while len(out) < limit:
        j = mm.find(needle, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    return out


def hexdump(mm: mmap.mmap, off: int, radius: int = 64) -> list[str]:
    lo, hi = max(0, off - radius), min(len(mm), off + radius)
    rows = []
    for base in range(lo, hi, 16):
        chunk = mm[base : min(base + 16, hi)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        mark = ">" if base <= off < base + 16 else " "
        rows.append(f"  {mark}{base:08x}  {hx}")
    return rows


def main() -> int:
    mod = load_extractor()
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    sipho = next(p for p in data["players"] if "Sithole" in (p.get("name") or ""))
    uid, job = int(sipho["uid"]), int(sipho["jobId"])
    lines = [f"# sipho v2 · uid={uid} job={job} parent={PARENT} loan={LOAN}", ""]

    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                uid_b = struct.pack("<I", uid)
                job_b = struct.pack("<I", job)
                parent_b = struct.pack("<I", PARENT)
                loan_b = struct.pack("<I", LOAN)

                uid_hits = find_all(mm, uid_b, 200)
                job_hits = find_all(mm, job_b, 200)
                loan_hits = find_all(mm, loan_b, 8000)
                parent_hits = find_all(mm, parent_b, 8000)
                lines.append(
                    f"counts uid={len(uid_hits)} job={len(job_hits)} "
                    f"loan1456={len(loan_hits)}(+cap) parent920={len(parent_hits)}(+cap)"
                )

                # Closest loan hit to each uid hit
                lines.append("## nearest 1456 to each Sipho UID hit")
                for uh in uid_hits[:60]:
                    best = None
                    # binary-ish scan: check loan hits (may be capped)
                    for lh in loan_hits:
                        d = abs(lh - uh)
                        if best is None or d < best[0]:
                            best = (d, lh)
                    if best and best[0] <= 65536:
                        lines.append(f"  uid@{uh} nearestLoan@{best[1]} dist={best[0]}")
                lines.append("")

                # Same for job
                lines.append("## nearest 1456 to Sipho job hits (dist<=16k)")
                for jh in job_hits[:80]:
                    best = None
                    for lh in loan_hits:
                        d = abs(lh - jh)
                        if best is None or d < best[0]:
                            best = (d, lh)
                    if best and best[0] <= 16384:
                        lines.append(f"  job@{jh} nearestLoan@{best[1]} dist={best[0]}")
                        if best[0] <= 512:
                            lines.extend(hexdump(mm, best[1], 48))
                lines.append("")

                # Brute: for each loan hit, check if uid within ±8KB (loan-centric)
                print("loan-centric uid proximity…", flush=True)
                lines.append("## 1456 hits with Sipho UID within ±8KB")
                close = []
                for lh in loan_hits:
                    lo, hi = max(0, lh - 8192), min(len(mm), lh + 8192)
                    # search uid in window
                    j = mm.find(uid_b, lo, hi)
                    if j >= 0:
                        # also parent in same window?
                        has_p = mm.find(parent_b, lo, hi) >= 0
                        close.append((lh, j - lh, has_p))
                lines.append(f"  closePairs={len(close)}")
                for lh, rel, has_p in close[:30]:
                    lines.append(f"  loan@{lh} uidRel={rel} parentAlso={has_p}")
                    lines.extend(hexdump(mm, lh, 64))
                    if abs(rel) <= 256:
                        lines.extend(hexdump(mm, lh + rel, 64))
                lines.append("")

                # Parent+loan within 64 bytes of each other, then check Sipho nearby
                print("parent-loan pairs near Sipho…", flush=True)
                lines.append("## 920+1456 within 64b, with Sipho uid/job within 8KB")
                pair_hits = []
                # Use limited parent hits near known Sipho regions
                sipho_anchors = uid_hits[:40] + job_hits[:40]
                for anchor in sipho_anchors:
                    lo, hi = max(0, anchor - 8192), min(len(mm), anchor + 8192)
                    pos = lo
                    while True:
                        j = mm.find(parent_b, pos, hi)
                        if j < 0:
                            break
                        for dlt in range(-64, 68, 4):
                            k = j + dlt
                            if lo <= k <= hi - 4 and mm[k : k + 4] == loan_b:
                                pair_hits.append((anchor, j, k, dlt))
                        pos = j + 1
                lines.append(f"  pairHits={len(pair_hits)}")
                # dedupe by parent off
                seen = set()
                for anchor, j, k, dlt in pair_hits:
                    if j in seen:
                        continue
                    seen.add(j)
                    lines.append(
                        f"  anchor@{anchor} parent@{j} loan@{k} delta={dlt}"
                    )
                    lines.extend(hexdump(mm, min(j, k), 80))
                    if len(seen) >= 20:
                        break
                lines.append("")

                # Discover if Sipho job appears on another squad list (Legia?)
                print("discover squads for Sipho job…", flush=True)
                squads = mod.discover_squads(mm)
                hosts = [
                    (tid, len(jobs))
                    for tid, (_a, _c, jobs) in squads.items()
                    if job in jobs
                ]
                lines.append(f"## Sipho job on discovered squads: {hosts}")

                # Resolve Legia: search club catalog for name Legia near 1456
                lines.append("## 'Legia' string near clubId 1456")
                needle = b"Legia"
                pos = 0
                n = 0
                while n < 30:
                    j = mm.find(needle, pos)
                    if j < 0:
                        break
                    w = mm[max(0, j - 64) : j + 64]
                    if loan_b in w:
                        lines.append(f"  Legia@{j} with1456 nearby")
                        lines.extend(hexdump(mm, j, 48))
                        n += 1
                    pos = j + 1
                lines.append("")

                # Does Sipho UID appear in employment with a DIFFERENT job (Legia job)?
                lines.append("## all emp-like jobs for Sipho UID in employment tail")
                search_lo = max(0, len(mm) - mod.EMPLOYMENT_TAIL)
                needle = b"\x02" + uid_b
                jobs = set()
                pos = search_lo
                while True:
                    j = mm.find(needle, pos)
                    if j < 0:
                        break
                    if j >= 6 and mm[j - 5] == 0x02 and mm[j - 6] in (0x08, 0x09, 0x0A, 0x0B):
                        jb = struct.unpack_from("<I", mm, j - 4)[0]
                        jobs.add((mm[j - 6], jb, j - 6))
                    pos = j + 1
                lines.append(f"  empJobs={sorted((t, j) for t, j, _ in jobs)}")
                for tag, jb, off in sorted(jobs, key=lambda x: x[2]):
                    # clubs near this emp tag
                    clubs = []
                    for off2 in range(off - 64, off + 128, 4):
                        if 0 <= off2 <= len(mm) - 4:
                            v = struct.unpack_from("<I", mm, off2)[0]
                            if v in (PARENT, LOAN, uid, job):
                                clubs.append((off2 - off, v))
                    lines.append(f"  tag={tag:02x} job={jb} @{off} markers={clubs}")
                    lines.extend(hexdump(mm, off, 64))

            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text[:16000])
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
