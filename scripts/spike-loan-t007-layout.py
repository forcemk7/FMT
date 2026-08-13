#!/usr/bin/env python3
"""T007: dissect job-list layout before shared loan motifs; club name locks."""

from __future__ import annotations

import importlib.util
import json
import mmap
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-t007-layout.txt"
PARENT = 920

MOTIFS = [
    (56322046, 904, "Abbe/Zetzmann cluster"),
    (56322846, 911, "Resvanis/Dunkel cluster"),
    (56323032, 912, "Vlad alone"),
    (56387915, 1456, "Sipho alone"),
]


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


def ascii_hits(mm: mmap.mmap, needle: bytes, limit: int = 5) -> list[int]:
    out = []
    pos = 0
    while len(out) < limit:
        j = mm.find(needle, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    return out


def main() -> None:
    lines: list[str] = []
    eft = load_eft()
    data = load_json(EXTRACT)
    by_job: dict[int, str] = {}
    jobs: set[int] = set()
    for p in data.get("players") or []:
        if p.get("jobId"):
            jobs.add(int(p["jobId"]))
            by_job[int(p["jobId"])] = str(p.get("name"))
    for key in ("reserves", "u19"):
        for p in (data.get(key) or {}).get("players") or []:
            if p.get("jobId"):
                jobs.add(int(p["jobId"]))
                by_job[int(p["jobId"])] = str(p.get("name"))

    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    for motif, club, label in MOTIFS:
        lines.append(f"\n## {label} motif@{motif} club={club}")
        start = motif - 96
        chunk = mm[start:motif + 32]
        # annotate every u32 that is a known job
        lines.append("rel u32 map (motif-rel):")
        for off in range(0, motif - start, 4):
            abs_off = start + off
            val = struct.unpack_from("<I", mm, abs_off)[0]
            rel = abs_off - motif
            if val in jobs:
                lines.append(f"  rel={rel:4d} job={val} {by_job.get(val)}")
            elif val == club:
                lines.append(f"  rel={rel:4d} CLUB={val}")
            elif val == 0xFFFFFFFF:
                lines.append(f"  rel={rel:4d} FFFFFFFF")
            elif val == 0:
                pass
        # dump hex with job markers
        lines.append("hex motif-80..+32:")
        lines.append(mm[motif - 80 : motif + 32].hex(" "))

        # What is the LAST job before the FF pad?
        # Find ff ff ff ff before motif
        pad = mm.rfind(b"\xff\xff\xff\xff", max(0, motif - 32), motif)
        lines.append(f"FFFFFFFF before motif at {pad} (rel {pad - motif if pad>=0 else None})")
        if pad >= 8:
            # walk back collecting consecutive job-like u32s
            cursor = pad
            # skip optional bytes between jobs and FFFFFFFF
            seq = []
            pos = pad - 4
            while pos >= motif - 200:
                val = struct.unpack_from("<I", mm, pos)[0]
                if val in jobs:
                    seq.append((pad - pos, val, by_job.get(val)))
                    pos -= 4
                    continue
                if val == 0:
                    pos -= 4
                    continue
                break
            lines.append(f"  jobs immediately before pad (closest first): {seq[:12]}")

    # Club name locks for 904 / 911
    lines.append("\n## Club id name locks")
    for cid, names in [
        (904, [b"Nurnberg", b"N\xc3\xbcrnberg", b"1. FC N", b"Nuernberg", b"Club Brugge"]),
        (911, [b"Bochum", b"VfL Bochum", b"Heidenheim", b"Hoffenheim"]),
        (912, [b"Frankfurt", b"Eintracht"]),
        (946, [b"St. Pauli", b"Pauli"]),
    ]:
        lines.append(f"club {cid}:")
        # search club id near utf8 names in save is heavy; instead count id occurrences near name
        for name in names:
            hits = ascii_hits(mm, name, limit=3)
            lines.append(f"  needle {name!r} hits={len(hits)} sample={hits}")

    # Employment / loan status another way: scan for job||64ff within short gap
    lines.append("\n## Per-job: unique motifs where job is CLOSEST squad job")
    # Build all motifs
    motifs = []
    pos = 0
    while True:
        j = mm.find(eft.LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        c = eft._parse_loan_out_template(mm, j, PARENT)
        if c is not None:
            motifs.append((j, c))
        pos = j + 1

    focus = [366246, 364668, 352031, 236310, 221126, 437615, 382267]
    for job in focus:
        # find motifs where this job is the closest in lookback 8..80
        wins = []
        shares = []
        for mj, c in motifs:
            closest = None
            has = False
            for back in range(8, 81):
                start = mj - back
                if start < 0:
                    continue
                jid = struct.unpack_from("<I", mm, start)[0]
                if jid in jobs and jid != c:
                    if closest is None:
                        closest = (back, jid)
                    if jid == job:
                        has = True
                        shares.append((back, mj, c, closest))
            if has and closest and closest[1] == job:
                wins.append((closest[0], mj, c))
        lines.append(
            f"  {by_job.get(job)} job={job} closest_wins={wins[:3]} "
            f"shared_appearances={len(shares)} first_share={shares[:2]}"
        )

    # Job-anchored: for each job take motif at EXACT structural offset if unique
    # Try: job at fixed offsets relative to motif for known good loans
    lines.append("\n## Fixed-offset histogram for product-true loans")
    true = {
        382267: 1456,
        437615: 912,
        506980: 916,
        506986: 2238,
        365838: 2249,
        315711: 946,
        317202: 108997,
        351592: 2245,
    }
    for job, expect in true.items():
        offs = []
        for mj, c in motifs:
            if c != expect:
                continue
            for back in range(8, 96):
                if struct.unpack_from("<I", mm, mj - back)[0] == job:
                    offs.append(back)
                    break
        lines.append(f"  job={job} expectClub={expect} backs={offs[:5]}")

    mm.close()
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
