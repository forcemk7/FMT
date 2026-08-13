#!/usr/bin/env python3
"""T007: per-player loan club via UID-neighborhood + alternate motifs."""

from __future__ import annotations

import importlib.util
import json
import mmap
import struct
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-t007-uid-clubs.txt"
PARENT = 920

PLAYERS = [
    ("Abbe", 2002266504, 366246),
    ("Resvanis", 2002264926, 364668),
    ("Dunkel", 2002252289, 352031),
    ("Zetzmann", 2002136568, 236310),
    ("Konya", 2002115380, 221126),  # guess — may be wrong uid
    ("Vlad", 2002330407, 437615),
    ("Sipho", 2002282525, 382267),
    ("Millwood", 2002422274, 538884),
    ("Davyskiba", 2002422387, 538997),
    ("Kraft", 2002441688, 558298),
    ("Seimen", 2000175080, 113517),  # at-club control
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


def main() -> None:
    lines: list[str] = []
    eft = load_eft()
    data = load_json(EXTRACT)

    # resolve Konya uid from extract
    name_jobs = {}
    roster = list(data.get("players") or [])
    roster += list((data.get("reserves") or {}).get("players") or [])
    roster += list((data.get("u19") or {}).get("players") or [])
    for p in roster:
        if p.get("name") and p.get("jobId"):
            name_jobs[p["name"]] = (int(p["uid"]), int(p["jobId"]))
    lines.append("## name→uid/job sample")
    for n, v in sorted(name_jobs.items()):
        if any(
            x in n.lower()
            for x in (
                "abbe",
                "resvanis",
                "dunkel",
                "zetzmann",
                "konya",
                "kasprzak",
                "kirsch",
                "mhlongo",
                "kraft",
                "millwood",
                "davyskiba",
                "perez",
                "pérez",
            )
        ):
            lines.append(f"  {n} → {v}")

    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    # Collect valid loan clubs from motifs (set of known foreign loan destinations)
    loan_clubs: set[int] = set()
    motifs: list[tuple[int, int]] = []
    pos = 0
    while True:
        j = mm.find(eft.LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        c = eft._parse_loan_out_template(mm, j, PARENT)
        if c is not None:
            loan_clubs.add(c)
            motifs.append((j, c))
        pos = j + 1
    lines.append(f"valid loan clubs n={len(loan_clubs)}")

    for label, uid, job in PLAYERS:
        # update from extract if name known
        for n, (u, jid) in name_jobs.items():
            if label.lower() in n.lower():
                uid, job = u, jid
                label = n
                break

        lines.append(f"\n## {label} uid={uid} job={job}")
        # double-UID sites
        needle = struct.pack("<I", uid) + struct.pack("<I", uid)
        doubles = []
        p = 0
        while len(doubles) < 30:
            s = mm.find(needle, p)
            if s < 0:
                break
            doubles.append(s)
            p = s + 1
        lines.append(f"  doubles={len(doubles)}")

        club_hits = Counter()
        motif_near = []
        for d in doubles:
            lo, hi = max(0, d - 256), min(len(mm), d + 256)
            # scan u32s
            for off in range(lo, hi - 3, 4):
                val = struct.unpack_from("<I", mm, off)[0]
                if val in loan_clubs and val != PARENT:
                    club_hits[val] += 1
            # any loan motif in window?
            for mj, c in motifs:
                if lo <= mj <= hi:
                    motif_near.append((mj - d, c, mj))
        lines.append(f"  loanClub hits near doubles: {club_hits.most_common(8)}")
        lines.append(f"  motifs near doubles: {motif_near[:6]}")

        # job||...||motif structural: require pad immediately before motif
        # and job within 8..80 before motif with only 'list noise' between
        job_b = struct.pack("<I", job)
        structural = []
        p = 0
        while len(structural) < 20:
            s = mm.find(job_b, p)
            if s < 0:
                break
            # look forward 8..96 for pad+motif
            for dist in range(8, 97):
                mj = s + dist
                if mj + 30 >= len(mm):
                    break
                if mm[mj : mj + 2] != eft.LOAN_OUT_MOTIF_PREFIX:
                    continue
                # require pad at mj-8
                if mm[mj - 8 : mj] != b"\xff\xff\xff\xff\xff\x00\x00\x00":
                    # also try standard 00×4 FF×4 FF 00×4 — actually pad is
                    # FF FF FF FF FF 00 00 00 00 then motif? From hex: 
                    # 00 00 00 00 FF FF FF FF FF 00 00 00 00 64 ff
                    continue
            # proper pad check
            for dist in range(8, 97):
                mj = s + dist
                if mj + 30 >= len(mm):
                    break
                if mm[mj - 12 : mj] != b"\x00\x00\x00\x00\xff\xff\xff\xff\xff\x00\x00\x00":
                    # last 4 of pad before motif is 00 00 00 00? 
                    # hex: FF FF FF FF FF 00 00 00 00 64 ff → motif-9 = FF, motif-8..-1 = FF 00 00 00 00? 
                    # Actually: bytes before motif: ff 00 00 00 00 | 64 ff
                    # Full: 00 00 00 00 | ff ff ff ff | ff | 00 00 00 00 | 64 ff
                    continue
                if mm[mj : mj + 2] != eft.LOAN_OUT_MOTIF_PREFIX:
                    continue
                c = eft._parse_loan_out_template(mm, mj, PARENT)
                if c is not None:
                    structural.append((dist, c, mj, s))
                    break
            # fix pad pattern
            p = s + 1

        # Correct pad: motif-13..motif = 00×4 + FF×4 + FF + 00×4
        structural2 = []
        p = 0
        sites = 0
        while sites < 500:
            s = mm.find(job_b, p)
            if s < 0:
                break
            sites += 1
            for dist in range(8, 97):
                mj = s + dist
                if mj < 13 or mj + 30 > len(mm):
                    continue
                if mm[mj - 13 : mj] != b"\x00\x00\x00\x00\xff\xff\xff\xff\xff\x00\x00\x00\x00":
                    continue
                if mm[mj : mj + 2] != eft.LOAN_OUT_MOTIF_PREFIX:
                    continue
                c = eft._parse_loan_out_template(mm, mj, PARENT)
                if c is not None:
                    structural2.append((dist, c, mj))
                    break
            p = s + 1
        lines.append(
            f"  job→pad+motif hits={structural2[:8]} (scanned_sites={sites})"
        )

    # Alternate: tag every job that is the FARTHEST squad job in lookback
    # AND also tag closest — union for mentoring exclude (accept wrong club)
    lines.append("\n## Mentoring-oriented: union closest+farthest lookback<=80")
    jobs = set()
    by_job = {}
    for group in (
        data.get("players") or [],
        (data.get("reserves") or {}).get("players") or [],
        (data.get("u19") or {}).get("players") or [],
    ):
        for p in group:
            if p.get("jobId"):
                jobs.add(int(p["jobId"]))
                by_job[int(p["jobId"])] = p.get("name")
    # include T004C gaps
    for jid, nm in (
        (315711, "Gorrissen"),
        (317202, "Risse"),
        (351592, "Perez"),
    ):
        jobs.add(jid)
        by_job[jid] = nm

    out: dict[int, int] = {}
    for mj, c in motifs:
        matches = []
        for back in range(8, 81):
            start = mj - back
            if start < 0:
                continue
            jid = struct.unpack_from("<I", mm, start)[0]
            if jid in jobs and jid != c:
                matches.append((back, jid))
        if not matches:
            continue
        for _, jid in (matches[0], matches[-1]):
            if jid not in out:
                out[jid] = c
    lines.append(f"union hits={len(out)}")
    for jid, c in sorted(out.items(), key=lambda x: by_job.get(x[0]) or ""):
        lines.append(f"  {by_job.get(jid)} job={jid} club={c}")

    # FP check: known at-club
    at_club = {
        106935: "Paco",
        334108: "Bandeira",
        285346: "Kizza",
        364642: "Jones",
        113517: "Seimen",
    }
    fps = [jid for jid in at_club if jid in out]
    lines.append(f"FP at-club controls: {[(at_club[j], j) for j in fps]}")

    mm.close()
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
