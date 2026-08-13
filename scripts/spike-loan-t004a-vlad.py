#!/usr/bin/env python3
"""
T004A spike: find FT domestic loan signal for Vlad (job 437615 → Frankfurt)
that Sipho's 64ff26 recipe misses, without false-positing at-club FT controls.

RE only — does not touch extract-first-team-fast.py / web/main.ts.
"""
from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-t004a-vlad-recipe.txt"

PARENT = 920
VLAD_UID, VLAD_JOB = 2002330407, 437615
SIPHO_UID, SIPHO_JOB = 2002282525, 382267
LEGIA = 1456

# At-club FT controls named in ticket
CTRL_NAMES = ("Paco", "Bandeira", "Kizza", "Jones", "Seimen", "Miraglia")

CLUB_LO, CLUB_HI = 50, 100_000


def load_extract() -> dict:
    raw = EXTRACT.read_bytes()
    text = raw.decode("utf-16" if raw[:2] == b"\xff\xfe" else "utf-8-sig")
    return json.loads(text)


def ft_players(d: dict) -> list[dict]:
    return list(d.get("players") or [])


def hex_dump(mm: mmap.mmap, off: int, length: int = 96) -> list[str]:
    lines = []
    hi = min(len(mm), off + length)
    for base in range(off, hi, 16):
        chunk = mm[base : min(base + 16, hi)]
        hx = " ".join(f"{b:02x}" for b in chunk)
        lines.append(f"  {base:08x}  {hx}")
    return lines


def find_job_ff_sites(mm: mmap.mmap, job: int, cap: int = 40) -> list[int]:
    """jobId followed by FFFFFFFF FFFFFFFF (Sipho loan-object shape)."""
    jb = struct.pack("<I", job)
    out: list[int] = []
    pos = 0
    while len(out) < cap:
        j = mm.find(jb, pos)
        if j < 0:
            break
        if j + 12 <= len(mm):
            a = struct.unpack_from("<I", mm, j + 4)[0]
            b = struct.unpack_from("<I", mm, j + 8)[0]
            if a == 0xFFFFFFFF and b == 0xFFFFFFFF:
                out.append(j)
        pos = j + 1
    return out


def motif_after(mm: mmap.mmap, job_at: int, window: int = 64) -> list[tuple[int, int]]:
    """(rel, kind) for 64 ff ?? after job."""
    hits = []
    lo, hi = job_at, min(len(mm), job_at + window)
    chunk = mm[lo:hi]
    k = 0
    while True:
        i = chunk.find(b"\x64\xff", k)
        if i < 0:
            break
        if i + 2 < len(chunk):
            hits.append((i, chunk[i + 2]))
        k = i + 1
    return hits


def dup_clubs_after(mm: mmap.mmap, start: int, span: int = 96, exclude: set[int] | None = None) -> list[tuple[int, int]]:
    exclude = exclude or set()
    dups = []
    for off in range(0, span):
        if start + off + 8 > len(mm):
            break
        a = struct.unpack_from("<I", mm, start + off)[0]
        b = struct.unpack_from("<I", mm, start + off + 4)[0]
        if a == b and CLUB_LO <= a <= CLUB_HI and a not in exclude:
            dups.append((off, a))
    return dups


def hunt_frankfurt_ids(mm: mmap.mmap) -> list[tuple[int, int]]:
    """Find clubIds near UTF-16 'Eintracht Frankfurt' / 'Frankfurt' name hits."""
    needles = [
        "Eintracht Frankfurt".encode("utf-16-le"),
        "Frankfurt".encode("utf-16-le"),
    ]
    cand: Counter[int] = Counter()
    for nb in needles:
        pos = 0
        n = 0
        while n < 80:
            j = mm.find(nb, pos)
            if j < 0:
                break
            lo, hi = max(0, j - 64), min(len(mm), j + 64)
            for off in range(lo, hi - 3):
                v = struct.unpack_from("<I", mm, off)[0]
                if CLUB_LO <= v <= CLUB_HI and v != PARENT:
                    cand[v] += 1
            n += 1
            pos = j + 1
    return cand.most_common(20)


def emp_jobs_for_uid(mm: mmap.mmap, uid: int, search_lo: int = 40_000_000) -> list[tuple[int, int]]:
    """Employment tag 02|uid → nearby job candidates (same recipe as hunt spikes)."""
    needle = b"\x02" + struct.pack("<I", uid)
    jobs: list[tuple[int, int]] = []
    pos = max(0, search_lo)
    while len(jobs) < 30:
        j = mm.find(needle, pos)
        if j < 0:
            break
        # look ±32 for plausible job u32
        for off in range(-32, 48, 4):
            st = j + off
            if st < 0 or st + 4 > len(mm):
                continue
            v = struct.unpack_from("<I", mm, st)[0]
            if 50_000 <= v <= 900_000:
                jobs.append((j, v))
        pos = j + 1
    return jobs


def scan_64ff_kinds_near_jobs(
    mm: mmap.mmap, job_map: dict[int, str], radius: int = 96
) -> dict[int, list[tuple[int, int, bool, list[int]]]]:
    """job → list of (abs_motif, kind, ff_pad, dups)."""
    out: dict[int, list[tuple[int, int, bool, list[int]]]] = defaultdict(list)
    for job, _name in job_map.items():
        jb = struct.pack("<I", job)
        pos = 0
        seen = 0
        while seen < 40:
            j = mm.find(jb, pos)
            if j < 0:
                break
            lo, hi = max(0, j - 32), min(len(mm), j + radius)
            chunk = mm[lo:hi]
            k = 0
            while True:
                i = chunk.find(b"\x64\xff", k)
                if i < 0:
                    break
                if i + 2 < len(chunk):
                    kind = chunk[i + 2]
                    if 0x20 <= kind <= 0x30:
                        abs_m = lo + i
                        ff = (
                            j + 12 <= len(mm)
                            and struct.unpack_from("<I", mm, j + 4)[0] == 0xFFFFFFFF
                            and struct.unpack_from("<I", mm, j + 8)[0] == 0xFFFFFFFF
                        )
                        dups = [c for _, c in dup_clubs_after(mm, abs_m, 80, {PARENT, job})]
                        out[job].append((abs_m, kind, ff, dups[:6]))
                k = i + 1
            seen += 1
            pos = j + 1
    return out


def try_recipe_a_ffpad_any_64ff2x_dup(
    mm: mmap.mmap, jobs: set[int], parent: int
) -> dict[int, int | None]:
    """
    Broader than product: FF-pad job + any 64ff2x in +8..+56 + first foreign dup club.
    """
    hits: dict[int, int | None] = {}
    for job in jobs:
        for site in find_job_ff_sites(mm, job):
            motifs = motif_after(mm, site, 56)
            good = [(rel, k) for rel, k in motifs if 0x20 <= k <= 0x30 and 8 <= rel <= 56]
            if not good:
                continue
            # prefer 0x26 then others
            good.sort(key=lambda x: (0 if x[1] == 0x26 else 1, x[0]))
            rel, kind = good[0]
            motif_at = site + rel
            dups = dup_clubs_after(mm, motif_at, 96, {parent, job})
            hits[job] = dups[0][1] if dups else None
            break
    return hits


def try_recipe_b_job_ffpad_foreign_dup_no_motif(
    mm: mmap.mmap, jobs: set[int], parent: int
) -> dict[int, int | None]:
    """FF-pad job sites with foreign club×2 in +16..+96 even without 64ff."""
    hits: dict[int, int | None] = {}
    for job in jobs:
        for site in find_job_ff_sites(mm, job):
            dups = [
                (off, c)
                for off, c in dup_clubs_after(mm, site, 96, {parent, job})
                if off >= 16
            ]
            if dups:
                hits[job] = dups[0][1]
                break
    return hits


def try_recipe_c_uid_near_foreign_dup(
    mm: mmap.mmap,
    uid_job: dict[int, int],
    parent: int,
    frank_candidates: set[int],
) -> dict[int, list[tuple[int, int]]]:
    """At double-UID, look for frank_candidates or any foreign dup within ±128."""
    out: dict[int, list[tuple[int, int]]] = {}
    for uid, job in uid_job.items():
        nb = struct.pack("<I", uid)
        found: list[tuple[int, int]] = []
        pos = 0
        while len(found) < 20:
            j = mm.find(nb, pos)
            if j < 0:
                break
            if j + 8 <= len(mm) and mm[j + 4 : j + 8] == nb:
                lo, hi = max(0, j - 128), min(len(mm), j + 128)
                for off in range(lo, hi - 7):
                    a = struct.unpack_from("<I", mm, off)[0]
                    b = struct.unpack_from("<I", mm, off + 4)[0]
                    if a == b and a in frank_candidates:
                        found.append((off, a))
                    elif a == b and CLUB_LO <= a <= CLUB_HI and a not in (parent, job):
                        # only keep if also near job bytes
                        if mm.find(struct.pack("<I", job), lo, hi) >= 0:
                            found.append((off, a))
            pos = j + 1
        if found:
            out[uid] = found[:8]
    return out


def try_recipe_d_sipho_shape_byte_diff(mm: mmap.mmap) -> list[str]:
    """Dump Sipho FF-pad+64ff26 site vs Vlad FF-pad sites side by side."""
    lines = ["## Sipho vs Vlad FF-pad job sites"]
    sipho_sites = find_job_ff_sites(mm, SIPHO_JOB)
    vlad_sites = find_job_ff_sites(mm, VLAD_JOB)
    lines.append(f"Sipho FF-pad sites ({len(sipho_sites)}): {sipho_sites[:10]}")
    lines.append(f"Vlad FF-pad sites ({len(vlad_sites)}): {vlad_sites[:10]}")
    for label, sites in (("SIPHO", sipho_sites[:3]), ("VLAD", vlad_sites[:5])):
        for s in sites:
            motifs = motif_after(mm, s, 64)
            dups = dup_clubs_after(mm, s, 96, {PARENT, SIPHO_JOB if label == "SIPHO" else VLAD_JOB})
            lines.append(f"### {label} @{s} motifs={[(r, hex(k)) for r,k in motifs]} dups={dups[:6]}")
            lines.extend(hex_dump(mm, s, 80))
    return lines


def main() -> int:
    d = load_extract()
    assert int(d["clubId"]) == PARENT
    players = ft_players(d)
    by_name: dict[str, dict] = {}
    for p in players:
        by_name[(p.get("name") or "")] = p

    controls = []
    for p in players:
        n = p.get("name") or ""
        if any(c.lower() in n.lower() for c in CTRL_NAMES):
            controls.append(p)

    vlad = next(p for p in players if int(p["uid"]) == VLAD_UID)
    sipho = next(p for p in players if int(p["uid"]) == SIPHO_UID)

    lines: list[str] = [
        "# T004A Vlad domestic loan detect spike",
        f"parent={PARENT} gameDate={d.get('gameDate')}",
        f"Vlad job={vlad['jobId']} uid={vlad['uid']} loan={vlad.get('loan')}",
        f"Sipho job={sipho['jobId']} uid={sipho['uid']} loan={sipho.get('loan')}",
        f"controls={[ (p.get('name'), p.get('jobId')) for p in controls ]}",
        "",
    ]

    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

        # --- Frankfurt club id candidates ---
        frank = hunt_frankfurt_ids(mm)
        lines.append("## Frankfurt name → nearby clubId top")
        for cid, cnt in frank:
            lines.append(f"  clubId={cid} score={cnt}")
        frank_set = {cid for cid, _ in frank[:8]}

        # Known: Legia 1456 works for Sipho. Also probe common FM DB ids near Frankfurt names.
        # Add any club appearing as dup near Vlad FF-pad sites.
        lines.append("")
        lines.extend(try_recipe_d_sipho_shape_byte_diff(mm))

        job_map = {int(vlad["jobId"]): "Vlad", int(sipho["jobId"]): "Sipho"}
        for p in controls:
            job_map[int(p["jobId"])] = (p.get("name") or "?")[:20]

        lines.append("")
        lines.append("## 64ff2x near FT jobs (Vlad/Sipho/controls)")
        near = scan_64ff_kinds_near_jobs(mm, job_map)
        for job, name in sorted(job_map.items(), key=lambda x: x[1]):
            rows = near.get(job) or []
            # summarize unique (kind, ff)
            summary = Counter((k, ff) for _, k, ff, _ in rows)
            best = rows[:4]
            lines.append(f"  {name} job={job} sites={len(rows)} kinds={dict(summary)}")
            for abs_m, kind, ff, dups in best:
                lines.append(f"    @{abs_m} kind={kind:#x} ff={ff} dups={dups}")

        # Recipe A/B on FT jobs
        ft_jobs = {int(p["jobId"]) for p in players if p.get("jobId")}
        hit_a = try_recipe_a_ffpad_any_64ff2x_dup(mm, ft_jobs, PARENT)
        hit_b = try_recipe_b_job_ffpad_foreign_dup_no_motif(mm, ft_jobs, PARENT)

        def describe(hits: dict[int, int | None]) -> list[str]:
            out = []
            name_of = {int(p["jobId"]): p.get("name") for p in players}
            for job, club in sorted(hits.items()):
                out.append(f"  job={job} {name_of.get(job)} loanClub={club}")
            return out

        lines.append("")
        lines.append(f"## RECIPE A: FF-pad + any 64ff2x + dup → {len(hit_a)} FT hits")
        lines.extend(describe(hit_a))
        lines.append(
            f"  Vlad in A? {VLAD_JOB in hit_a}  Sipho in A? {SIPHO_JOB in hit_a}  "
            f"ctrl hits={[int(p['jobId']) in hit_a for p in controls]}"
        )

        lines.append("")
        lines.append(f"## RECIPE B: FF-pad + foreign dup (no motif) → {len(hit_b)} FT hits")
        lines.extend(describe(hit_b)[:40])
        lines.append(
            f"  Vlad in B? {VLAD_JOB in hit_b}  Sipho in B? {SIPHO_JOB in hit_b}  "
            f"ctrl hits={[int(p['jobId']) in hit_b for p in controls]}"
        )

        # Product recipe (64ff26 only)
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "eft", ROOT / "scripts" / "extract-first-team-fast.py"
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        hit_prod = mod.detect_loaned_out_jobs(mm, ft_jobs, PARENT)
        lines.append("")
        lines.append(f"## PRODUCT 64ff26 → {len(hit_prod)} FT hits")
        lines.extend(describe(hit_prod))

        # UID-near Frankfurt candidates
        uid_job = {VLAD_UID: VLAD_JOB, SIPHO_UID: SIPHO_JOB}
        for p in controls:
            uid_job[int(p["uid"])] = int(p["jobId"])
        # expand frank_set with dups seen on Vlad sites
        for site in find_job_ff_sites(mm, VLAD_JOB)[:10]:
            for _, c in dup_clubs_after(mm, site, 128, {PARENT, VLAD_JOB}):
                frank_set.add(c)
        # also add top frankfurt name hits
        frank_set |= {cid for cid, _ in frank[:12]}

        lines.append("")
        lines.append(f"## RECIPE C: double-UID near frank/foreign dups frank_set={sorted(frank_set)[:20]}")
        c_hits = try_recipe_c_uid_near_foreign_dup(mm, uid_job, PARENT, frank_set)
        for uid, rows in c_hits.items():
            name = next((p.get("name") for p in players if int(p["uid"]) == uid), str(uid))
            lines.append(f"  {name} uid={uid} hits={rows[:6]}")

        # Employment dual-job probe
        lines.append("")
        lines.append("## employment 02|uid nearby jobs (cap)")
        for label, uid, job in (
            ("Vlad", VLAD_UID, VLAD_JOB),
            ("Sipho", SIPHO_UID, SIPHO_JOB),
            ("Seimen", 2000175080, 113517),
            ("Paco", 2000136577, 106935),
        ):
            emps = emp_jobs_for_uid(mm, uid)
            uniq = sorted({j for _, j in emps})
            lines.append(f"  {label} extractJob={job} empJobs={uniq[:12]} n={len(uniq)}")

        # Deep: for each Vlad FF-pad site, list ALL u32 clubish + motifs; check if 912/790/etc
        # appear in Frankfurt name neighborhood more than noise.
        lines.append("")
        lines.append("## Vlad FF-pad site clubish u32 histogram vs Frankfurt name scores")
        vlad_clubs: Counter[int] = Counter()
        for site in find_job_ff_sites(mm, VLAD_JOB):
            for off in range(0, 128, 4):
                if site + off + 4 > len(mm):
                    break
                v = struct.unpack_from("<I", mm, site + off)[0]
                if CLUB_LO <= v <= CLUB_HI and v not in (PARENT, VLAD_JOB):
                    vlad_clubs[v] += 1
        frank_score = dict(frank)
        for cid, cnt in vlad_clubs.most_common(30):
            lines.append(f"  clubish={cid} at_sites={cnt} frankNameScore={frank_score.get(cid, 0)}")

        # Diff Sipho loan object bytes at motif: what third-byte variants exist globally
        # with FF-pad lookback for ANY squad job — count how many FT jobs hit per kind.
        lines.append("")
        lines.append("## global FF-pad + 64ff2x kind → FT job hit counts")
        kind_hits: dict[int, set[int]] = defaultdict(set)
        pos = 0
        scanned = 0
        while scanned < 2_000_000:
            j = mm.find(b"\x64\xff", pos)
            if j < 0:
                break
            scanned += 1
            if j + 2 >= len(mm):
                pos = j + 1
                continue
            kind = mm[j + 2]
            if not (0x20 <= kind <= 0x30):
                pos = j + 1
                continue
            for back in range(8, 57):
                st = j - back
                if st < 0:
                    continue
                if st + 12 > len(mm):
                    continue
                if (
                    struct.unpack_from("<I", mm, st + 4)[0] != 0xFFFFFFFF
                    or struct.unpack_from("<I", mm, st + 8)[0] != 0xFFFFFFFF
                ):
                    continue
                job = struct.unpack_from("<I", mm, st)[0]
                if job in ft_jobs:
                    kind_hits[kind].add(job)
                    break
            pos = j + 1
        for kind in sorted(kind_hits):
            jobs_hit = kind_hits[kind]
            names = [
                next((p.get("name") for p in players if int(p["jobId"]) == j), str(j))
                for j in sorted(jobs_hit)
            ]
            lines.append(f"  kind={kind:#x} n={len(jobs_hit)} names={names}")

        mm.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:120]))
    print("...")
    print(f"wrote {OUT} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
