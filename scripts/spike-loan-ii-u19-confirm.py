#!/usr/bin/env python3
"""
T004B confirm: II/U19 loan detect recipe (generalized Sipho layout).

Recipe (handoff to T004 integrate):
  1. Motif-first scan for `64 ff 24` OR `64 ff 26`
  2. Require pre4 at motif-4..motif == 00 00 00 00
  3. Look back 8..49 bytes for a squad jobId
  4. Require duplicated loanClubId u32 pair starting at motif+21
  5. loanClub in [50, 100000], ≠ parentClub

On live-0112 (parent=920):
  Braescu 506980 → 916 (Köln)     kind=24 back=41
  Manole  506986 → 2238 (Augsburg) kind=24 back=37
  Ozturk  365838 → 2249 (Rot-Wei*) kind=24 back=49
  Sipho   382267 → 1456 (Legia)    kind=26 back=25  (control; product today)
  Millwood 538884 → NO hit (no 64ff2x loan object on job)

*2249 name lock weaker than 916/2238; still same object shape.
False positives: 0 on FT/II/U19 at-club with back_hi=48 (Ozturk needs 49).
back_hi=56 also tags Vlad→912 (Frankfurt) — T004A.

Overlap with T004A/Sipho: identical layout; only motif third byte differs
(0x26 international Sipho vs 0x24 domestic II/U19). Product LOAN_OUT_MOTIF
is 64ff26-only today — widen kinds + filters, do not invent a second join.
"""

from __future__ import annotations

import json
import mmap
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "spike-loan-ii-u19-confirm.txt"
PARENT = 920

EXPECT = {
    506980: 916,  # Braescu → Köln
    506986: 2238,  # Manole → Augsburg
    365838: 2249,  # Ozturk → Essen cand
    382267: 1456,  # Sipho control
}
MISS = {538884}  # Millwood


def load_jobs(data: dict) -> set[int]:
    jobs = {int(p["jobId"]) for p in data["players"]}
    jobs |= {int(p["jobId"]) for p in data["reserves"]["players"]}
    jobs |= {int(p["jobId"]) for p in data["u19"]["players"]}
    return jobs


def detect(mm: mmap.mmap, jobs: set[int], *, back_hi: int = 49) -> dict[int, int]:
    out: dict[int, int] = {}
    for kind in (0x24, 0x26):
        motif = bytes((0x64, 0xFF, kind))
        pos = 0
        while True:
            j = mm.find(motif, pos)
            if j < 0:
                break
            if j < 4 or mm[j - 4 : j] != b"\x00\x00\x00\x00":
                pos = j + 1
                continue
            matched = None
            for back in range(8, back_hi + 1):
                start = j - back
                if start < 0:
                    continue
                job = struct.unpack_from("<I", mm, start)[0]
                if job in jobs:
                    matched = job
                    break
            if matched is not None and matched not in out and j + 29 <= len(mm):
                a = struct.unpack_from("<I", mm, j + 21)[0]
                b = struct.unpack_from("<I", mm, j + 25)[0]
                if (
                    a == b
                    and 50 <= a <= 100_000
                    and a != PARENT
                    and a != matched
                ):
                    out[matched] = a
            pos = j + 1
    return out


def main() -> int:
    raw = EXTRACT.read_bytes()
    data = None
    for enc in ("utf-16", "utf-8-sig"):
        try:
            data = json.loads(raw.decode(enc))
            break
        except Exception:
            pass
    assert data is not None
    jobs = load_jobs(data)
    lines = ["# T004B confirm", ""]
    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hit = detect(mm, jobs, back_hi=49)
        finally:
            mm.close()

    ok = True
    for job, club in EXPECT.items():
        got = hit.get(job)
        mark = "PASS" if got == club else "FAIL"
        if got != club:
            ok = False
        lines.append(f"{mark} job={job} expect={club} got={got}")
    for job in MISS:
        if job in hit:
            ok = False
            lines.append(f"FAIL Millwood unexpectedly hit → {hit[job]}")
        else:
            lines.append(f"PASS Millwood job={job} correctly untagged (no motif)")

    # at-club FP check: known non-loan FT controls from T004A
    controls = {
        "Paco": 106935,
        "Bandeira": 334108,
        "Kizza": 285346,
        "Jones": 364642,
        "Seimen": 113517,
    }
    for name, job in controls.items():
        if job in hit:
            ok = False
            lines.append(f"FAIL FP {name} job={job} → {hit[job]}")
        else:
            lines.append(f"PASS no-FP {name} job={job}")

    lines.append(f"totalTagged={len(hit)}")
    lines.append("RESULT " + ("PASS" if ok else "FAIL"))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
