#!/usr/bin/env python3
"""
Calibrate Parent/Loan club using Sipho Sithole:
  parent=920 (Schalke), loan=1456 (Legia).
"""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import tempfile
from collections import Counter
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "dynamics-b.fm"
EXTRACT = ROOT / "tmp" / "dynamics-b-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-sipho-legia.txt"

PARENT = 920
LOAN = 1456
EMP_TAGS = (0x08, 0x09, 0x0A, 0x0B)


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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-sipho-", suffix=".bin")
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


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 200) -> list[int]:
    out = []
    pos = 0
    while len(out) < limit:
        j = mm.find(needle, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    return out


def find_doubles(mm: mmap.mmap, uid: int, limit: int = 30) -> list[int]:
    nb = struct.pack("<I", uid)
    out = []
    pos = 0
    while len(out) < limit:
        j = mm.find(nb, pos)
        if j < 0:
            break
        if j + 8 <= len(mm) and mm[j + 4 : j + 8] == nb:
            out.append(j)
        pos = j + 1
    return out


def hexdump(mm: mmap.mmap, off: int, radius: int = 96) -> list[str]:
    lo, hi = max(0, off - radius), min(len(mm), off + radius)
    rows = []
    for base in range(lo, hi, 16):
        chunk = mm[base : min(base + 16, hi)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        mark = ">" if base <= off < base + 16 else " "
        rows.append(f"  {mark}{base:08x}  {hx}")
    return rows


def u32s_in(mm: mmap.mmap, lo: int, hi: int) -> list[tuple[int, int]]:
    out = []
    p = lo & ~3
    end = min(hi, len(mm) - 3)
    while p <= end:
        out.append((p, struct.unpack_from("<I", mm, p)[0]))
        p += 4
    return out


def main() -> int:
    mod = load_extractor()
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    sipho = next(
        p
        for p in data["players"]
        if "Sithole" in (p.get("name") or "") or "Sipho" in (p.get("name") or "")
    )
    uid = int(sipho["uid"])
    job = int(sipho["jobId"])
    lines = [
        f"# Sipho loan calibrate · {SAVE.name}",
        f"name={sipho.get('name')} uid={uid} job={job}",
        f"parent={PARENT} loan={LOAN}",
        "",
    ]
    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                parent_b = struct.pack("<I", PARENT)
                loan_b = struct.pack("<I", LOAN)
                uid_b = struct.pack("<I", uid)
                job_b = struct.pack("<I", job)

                doubles = find_doubles(mm, uid)
                lines.append(f"## double-UID hits={len(doubles)}")
                for d in doubles[:12]:
                    lines.append(f"  @{d}")
                lines.append("")

                # Windows around double-UID containing BOTH clubs
                lines.append("## double-UID windows with BOTH 920 and 1456")
                both_hits = []
                for d in doubles:
                    for rad in (64, 128, 256, 512, 1024, 2048):
                        lo, hi = max(0, d - rad), min(len(mm), d + rad)
                        w = mm[lo:hi]
                        if parent_b in w and loan_b in w:
                            p_off = lo + w.find(parent_b)
                            l_off = lo + w.find(loan_b)
                            both_hits.append((d, rad, p_off - d, l_off - d, p_off, l_off))
                            break
                lines.append(f"  doublesWithBoth={len(both_hits)}")
                for row in both_hits[:20]:
                    lines.append(
                        f"  double@{row[0]} rad={row[1]} parentRel={row[2]} loanRel={row[3]}"
                    )
                    # dump around the closer of the two clubs
                    anchor = row[5] if abs(row[3]) <= abs(row[2]) else row[4]
                    lines.extend(hexdump(mm, anchor, 80))
                lines.append("")

                # Relative offsets between 920 and 1456 near uid
                lines.append("## parent↔loan deltas near any UID hit (±512)")
                uid_hits = find_all(mm, uid_b, limit=80)
                delta_hist: Counter[int] = Counter()
                pair_samples = []
                for uh in uid_hits:
                    lo, hi = max(0, uh - 512), min(len(mm), uh + 512)
                    # find all parent and loan in window
                    parents = []
                    loans = []
                    pos = lo
                    while True:
                        j = mm.find(parent_b, pos, hi)
                        if j < 0:
                            break
                        parents.append(j)
                        pos = j + 1
                    pos = lo
                    while True:
                        j = mm.find(loan_b, pos, hi)
                        if j < 0:
                            break
                        loans.append(j)
                        pos = j + 1
                    for p in parents:
                        for l in loans:
                            delta = l - p
                            if abs(delta) <= 64:
                                delta_hist[delta] += 1
                                if len(pair_samples) < 25:
                                    pair_samples.append((uh, p, l, delta, p - uh, l - uh))
                lines.append(f"  uidHitsScanned={len(uid_hits)}")
                lines.append(f"  tightDeltaHist={dict(sorted(delta_hist.items()))}")
                for uh, p, l, delta, pr, lr in pair_samples[:15]:
                    lines.append(
                        f"  uid@{uh} parent@{p}(rel{pr}) loan@{l}(rel{lr}) delta={delta}"
                    )
                    lines.extend(hexdump(mm, min(p, l), 64))
                lines.append("")

                # Job emp tags + nearby clubs
                lines.append("## employment tags for Sipho job → nearby clubs")
                pos = 0
                n = 0
                while n < 20:
                    j = mm.find(b"\x02" + job_b + b"\x02", pos)
                    if j < 0:
                        break
                    tag = mm[j - 1] if j >= 1 else -1
                    u = struct.unpack_from("<I", mm, j + 6)[0] if j + 10 <= len(mm) else 0
                    clubs = []
                    for off, v in u32s_in(mm, j - 32, j + 96):
                        if v in (PARENT, LOAN, 0, 0xFFFFFFFF) or v == uid:
                            clubs.append((off - j, v))
                    lines.append(
                        f"  @{j-1} tag={tag:02x} uid={u} match={u==uid} clubs={clubs}"
                    )
                    if u == uid or PARENT in [c for _, c in clubs] or LOAN in [
                        c for _, c in clubs
                    ]:
                        lines.extend(hexdump(mm, j - 1, 80))
                    n += 1
                    pos = j + 1
                lines.append("")

                # Search literal adjacency patterns: 920 then 1456 at fixed deltas
                lines.append("## global adjacent patterns parent|loan (sample near Sipho uid)")
                for delta in (4, 8, 12, 16, -4, -8, 20, 24, 28, 32):
                    count_near_uid = 0
                    samples = []
                    pos = 0
                    while True:
                        j = mm.find(parent_b, pos)
                        if j < 0:
                            break
                        k = j + delta
                        if 0 <= k <= len(mm) - 4 and mm[k : k + 4] == loan_b:
                            # near sipho?
                            near = any(abs(j - uh) < 2048 for uh in uid_hits[:40])
                            if near:
                                count_near_uid += 1
                                if len(samples) < 5:
                                    samples.append(j)
                        pos = j + 1
                        if pos > 0 and pos % 50_000_000 == 0:
                            pass
                    if count_near_uid or samples:
                        lines.append(
                            f"  delta={delta:+d} nearUidHits={count_near_uid} samples={samples}"
                        )
                        for s in samples[:2]:
                            lines.extend(hexdump(mm, s, 48))
                lines.append("")

                # Control: at-club Muller — should NOT have 1456 near parent pairs
                mull = next(p for p in data["players"] if "ller" in (p.get("name") or "") and "Robert" in (p.get("name") or ""))
                mu = int(mull["uid"])
                lines.append(f"## control {mull.get('name')} uid={mu} — 1456 near UID?")
                m_hits = find_all(mm, struct.pack("<I", mu), limit=40)
                loan_near = 0
                for uh in m_hits:
                    w = mm[max(0, uh - 256) : uh + 256]
                    if loan_b in w:
                        loan_near += 1
                lines.append(f"  uidHits={len(m_hits)} with1456in±256={loan_near}")

            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text[:14000])
    print(f"\n… wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
