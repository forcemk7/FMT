#!/usr/bin/env python3
"""
Loan / notAtClub hunt using Parent Club + Loan Club contract signal.

Hypotheses:
  A) Gap jobs on Schalke FT/II lists are loaned-out (orphaned jobIds, no emp tag).
  B) At-club players: contract neighborhood has parent=920 and loan=0/absent.
  C) Loaned-out: parent=920 + nonzero loan clubId near person/job.
  D) Gap jobIds may still appear on another club's squad list.

Uses dynamics-b extract + save.
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
OUT = ROOT / "tmp" / "fm-spike" / "loan-parent-loan-club.txt"

PARENT = 920  # Schalke
EMP_TAGS = (0x08, 0x09, 0x0A, 0x0B)
# Plausible clubId range from prior RE (II clubs were 1k–30k; avoid tiny/huge noise)
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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-plc-", suffix=".bin")
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


def read_jobs(mm: mmap.mmap, list_abs: int, count: int) -> list[int]:
    if list_abs + 2 + 4 * count <= len(mm):
        c = struct.unpack_from("<H", mm, list_abs)[0]
        if c == count:
            return [
                struct.unpack_from("<I", mm, list_abs + 2 + 4 * i)[0]
                for i in range(count)
            ]
    return [struct.unpack_from("<I", mm, list_abs + 4 * i)[0] for i in range(count)]


def find_double_uid(mm: mmap.mmap, uid: int, limit: int = 20) -> list[int]:
    nb = struct.pack("<I", uid)
    out: list[int] = []
    pos = 0
    while len(out) < limit:
        j = mm.find(nb, pos)
        if j < 0:
            break
        if j + 8 <= len(mm) and mm[j + 4 : j + 8] == nb:
            out.append(j)
        pos = j + 1
    return out


def club_ids_in_window(mm: mmap.mmap, lo: int, hi: int) -> list[tuple[int, int]]:
    """Return (abs_off, clubId) for plausible clubIds in [lo,hi)."""
    hits = []
    parent_b = struct.pack("<I", PARENT)
    # scan all u32s — expensive windows stay small (±512)
    p = lo
    end = min(hi, len(mm) - 3)
    while p < end:
        v = struct.unpack_from("<I", mm, p)[0]
        if CLUB_LO <= v <= CLUB_HI:
            hits.append((p, v))
        p += 1  # byte-step to catch unaligned? keep aligned for speed
        # actually use 1-byte for accuracy in small windows
    return hits


def club_ids_aligned(mm: mmap.mmap, lo: int, hi: int) -> list[tuple[int, int]]:
    hits = []
    p = lo & ~3
    end = min(hi, len(mm) - 3)
    while p < end:
        v = struct.unpack_from("<I", mm, p)[0]
        if CLUB_LO <= v <= CLUB_HI:
            hits.append((p, v))
        p += 4
    return hits


def parent_loan_candidates(
    mm: mmap.mmap, anchor: int, radius: int = 256
) -> list[tuple[int, int, int]]:
    """
    Find (parent_off, loan_off, loan_id) where u32@parent_off==920 and
    another clubId sits within ±32 bytes (contract parent/loan pair).
    """
    lo = max(0, anchor - radius)
    hi = min(len(mm), anchor + radius)
    parent_b = struct.pack("<I", PARENT)
    out = []
    pos = lo
    while True:
        j = mm.find(parent_b, pos, hi)
        if j < 0:
            break
        # look ±48 bytes for another clubId
        wlo, whi = max(lo, j - 48), min(hi, j + 52)
        for off, cid in club_ids_aligned(mm, wlo, whi):
            if off == j:
                continue
            if cid == PARENT:
                continue
            # prefer close pairs (likely adjacent fields)
            if abs(off - j) <= 32:
                out.append((j, off, cid))
        pos = j + 1
    return out


def main() -> int:
    mod = load_extractor()
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [f"# parent/loan club hunt · {SAVE.name}", ""]

    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                ft_players = data["players"]
                ii_players = data["reserves"]["players"]
                ft_jobs = read_jobs(mm, int(data["listAbs"]), int(data["countHeader"]))
                ii_jobs = read_jobs(
                    mm, int(data["reserves"]["listAbs"]), int(data["reserves"]["countHeader"])
                )
                resolved = {int(p["jobId"]) for p in ft_players} | {
                    int(p["jobId"]) for p in ii_players
                }
                ft_gaps = [j for j in ft_jobs if j and j not in resolved]
                ii_gaps = [j for j in ii_jobs if j and j not in resolved]
                lines.append(f"## Gap jobs FT={ft_gaps} II={ii_gaps}")
                lines.append("")

                # --- A/D: do gap jobs appear on other squad lists? ---
                print("discover squads…", flush=True)
                squads = mod.discover_squads(mm)
                lines.append(f"## Gap jobs on other squad lists (discovered={len(squads)})")
                for gap in ft_gaps + ii_gaps:
                    hosts = []
                    for tid, (_a, _c, jobs) in squads.items():
                        if gap in jobs:
                            hosts.append((tid, len(jobs)))
                    lines.append(f"  job={gap} onSquads={hosts[:8]} n={len(hosts)}")
                lines.append("")

                # --- Broader emp-like patterns for gap jobs (any tag byte) ---
                lines.append("## Gap job: any XX 02 <job> 02 <uid?> in whole file")
                for gap in ft_gaps + ii_gaps:
                    jb = struct.pack("<I", gap)
                    pat_mids = []
                    pos = 0
                    while len(pat_mids) < 30:
                        j = mm.find(b"\x02" + jb + b"\x02", pos)
                        if j < 0:
                            break
                        tag = mm[j - 1] if j >= 1 else None
                        uid = struct.unpack_from("<I", mm, j + 6)[0] if j + 10 <= len(mm) else 0
                        uid_ok = 1_900_000_000 <= uid <= 2_200_000_000
                        pat_mids.append((j - 1, tag, uid, uid_ok))
                        pos = j + 1
                    ok = [r for r in pat_mids if r[3]]
                    lines.append(
                        f"  job={gap} midHits={len(pat_mids)} uidLike={len(ok)} "
                        f"sample={ok[:5] or pat_mids[:3]}"
                    )
                lines.append("")

                # --- B/C: parent+loan pairs near person double-UID ---
                lines.append("## Parent(920)+other club near double-UID (at-club sample)")
                print("scan parent/loan near players…", flush=True)
                pair_hist = Counter()
                loan_ids = Counter()
                per_player = []
                for p in ft_players + ii_players:
                    uid = int(p["uid"])
                    doubles = find_double_uid(mm, uid, limit=8)
                    pairs_all = []
                    for d in doubles[:4]:
                        pairs_all.extend(parent_loan_candidates(mm, d, radius=384))
                    # dedupe by loan club
                    loans = sorted({cid for _a, _b, cid in pairs_all})
                    pair_hist[len(loans)] += 1
                    for cid in loans:
                        loan_ids[cid] += 1
                    if loans:
                        per_player.append((p.get("name"), uid, loans[:12], len(doubles)))
                lines.append(f"  playersScanned={len(ft_players)+len(ii_players)}")
                lines.append(f"  distinctLoanIdCountHist={dict(sorted(pair_hist.items()))}")
                lines.append(f"  topLoanCompanionIds={loan_ids.most_common(15)}")
                lines.append(f"  playersWithAnyCompanion={len(per_player)}")
                # If almost everyone has companions, signal is noisy.
                # Show players with unusual companion counts
                unusual = [r for r in per_player if len(r[2]) >= 3]
                lines.append(f"  playersWith>=3 companions={len(unusual)} (may be noise)")
                for row in per_player[:8]:
                    lines.append(f"    sample {row[0]} loansNear={row[2]}")
                lines.append("")

                # --- Tighter: adjacent u32 pair 920|X or X|920 within 4–8 bytes ---
                lines.append("## Tight adjacent parent|loan u32 pairs near double-UID (±128)")
                tight_by_player = []
                for p in ft_players:
                    uid = int(p["uid"])
                    doubles = find_double_uid(mm, uid, limit=6)
                    found = set()
                    for d in doubles[:3]:
                        lo, hi = max(0, d - 128), min(len(mm), d + 128)
                        pos = lo
                        pb = struct.pack("<I", PARENT)
                        while True:
                            j = mm.find(pb, pos, hi)
                            if j < 0:
                                break
                            for delta in (-8, -4, 4, 8):
                                k = j + delta
                                if k < 0 or k + 4 > len(mm):
                                    continue
                                cid = struct.unpack_from("<I", mm, k)[0]
                                if cid != PARENT and CLUB_LO <= cid <= CLUB_HI:
                                    found.add(cid)
                            pos = j + 1
                    if found:
                        tight_by_player.append((p.get("name"), sorted(found)))
                lines.append(f"  FT with tight companion={len(tight_by_player)}/{len(ft_players)}")
                for name, cids in tight_by_player[:15]:
                    lines.append(f"    {name}: {cids}")
                lines.append("")

                # --- Gap job neighborhoods: parent+loan near list slot? weak ---
                lines.append("## 920 occurrences within ±64 of gap job list slots")
                for label, list_abs, count, gaps in (
                    ("FT", int(data["listAbs"]), int(data["countHeader"]), ft_gaps),
                    (
                        "II",
                        int(data["reserves"]["listAbs"]),
                        int(data["reserves"]["countHeader"]),
                        ii_gaps,
                    ),
                ):
                    raw = read_jobs(mm, list_abs, count)
                    for gap in gaps:
                        try:
                            idx = raw.index(gap)
                        except ValueError:
                            continue
                        # jobs start at list_abs+2
                        slot = list_abs + 2 + 4 * idx
                        w = mm[max(0, slot - 64) : slot + 68]
                        n920 = w.count(struct.pack("<I", PARENT))
                        lines.append(f"  {label} job={gap} idx={idx} slot@{slot} parentHits±64={n920}")

            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
