#!/usr/bin/env python3
"""
Bridge person UniqueID / jobId / name → mark+days DOB sites.

Known: DOB often lives as 01 00 6c 07 + days_y1900_u32 (+ often ffffffff), uniquely once
per player for 24/25 screenshot fixtures — but not near the person double-UID.

This spike hunts absolute / relative bridges from the extract person record.
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
EXTRACT = ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json"
OUT = ROOT / "tmp" / "fm-spike" / "dob-bridge.txt"
MARK = bytes.fromhex("01006c07")
EPOCH = date(1900, 1, 1)
PERSON_HEAD = 512 * 1024 * 1024
RADII = (256, 1024, 4096, 16384, 65536, 262144)


def doubles(mm: mmap.mmap, uid: int) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(mm), PERSON_HEAD)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 16:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def best_double(mm: mmap.mmap, uid: int) -> int | None:
    ds = doubles(mm, uid)
    if not ds:
        return None

    def score(dab: int) -> int:
        blob = bytes(mm[dab : dab + 160])
        s = 0
        if b"\x01\x01\x01" in blob[8:120]:
            s += 5
        if MARK in blob:
            s += 3
        if len(blob) >= 35:
            pi = struct.unpack_from("<I", blob, 31)[0]
            if 0 < pi < 200_000:
                s += 4
        return s

    return sorted(ds, key=lambda d: (-score(d), d))[0]


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 64) -> list[int]:
    hits: list[int] = []
    j = mm.find(needle)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(needle, j + 1)
    return hits


def nearest(hits: list[int], target: int) -> tuple[int | None, int | None]:
    if not hits:
        return None, None
    best = min(hits, key=lambda h: abs(h - target))
    return best, best - target


def u32_hits_in_window(mm: mmap.mmap, center: int, radius: int, value: int) -> list[int]:
    lo = max(0, center - radius)
    hi = min(len(mm), center + radius + 4)
    pat = struct.pack("<I", value)
    window = bytes(mm[lo:hi])
    hits: list[int] = []
    start = 0
    while True:
        j = window.find(pat, start)
        if j < 0:
            break
        hits.append(lo + j)
        start = j + 1
    return hits


def main() -> None:
    lines: list[str] = []
    extract_by_uid: dict[int, dict] = {}
    if EXTRACT.exists():
        body = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
        for p in body.get("players") or []:
            uid = p.get("uid")
            if uid is not None:
                extract_by_uid[int(uid)] = p

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            rows = []
            for p in PLAYERS:
                dob = date(*map(int, p["dob"].split("-")))
                days = (dob - EPOCH).days
                uid = int(p["uid"])
                dab = best_double(mm, uid)
                sites = find_all(mm, MARK + struct.pack("<I", days), limit=8)
                site = sites[0] if sites else None
                ex = extract_by_uid.get(uid, {})
                job = ex.get("jobId")
                rows.append(
                    {
                        "name": p["name"],
                        "uid": uid,
                        "dob": dob,
                        "days": days,
                        "dab": dab,
                        "site": site,
                        "sites": sites,
                        "jobId": int(job) if job is not None else None,
                        "personIndex": (ex.get("extractMeta") or {}).get("personIndex"),
                    }
                )

            # --- A: UID / job near DOB site ---
            lines.append("## A: UID/jobId near DOB site (expanding radius)")
            uid_ok = Counter()
            job_ok = Counter()
            for r in rows:
                if r["site"] is None:
                    lines.append(f"  {r['name']}: no site")
                    continue
                uid_r = None
                job_r = None
                for rad in RADII:
                    if uid_r is None and u32_hits_in_window(mm, r["site"], rad, r["uid"]):
                        uid_r = rad
                    if (
                        job_r is None
                        and r["jobId"] is not None
                        and u32_hits_in_window(mm, r["site"], rad, r["jobId"])
                    ):
                        job_r = rad
                if uid_r is not None:
                    uid_ok[uid_r] += 1
                if job_r is not None:
                    job_ok[job_r] += 1
                lines.append(
                    f"  {r['name']}: site={r['site']} uid_within={uid_r} "
                    f"job_within={job_r} jobId={r['jobId']}"
                )
            lines.append(f"uid radius histogram: {dict(uid_ok)}")
            lines.append(f"job radius histogram: {dict(job_ok)}")

            # --- B: correct UTF-8 name near DOB site ---
            lines.append("\n## B: player name UTF-8 near DOB site")
            name_ok = Counter()
            for r in rows:
                if r["site"] is None:
                    continue
                raw = r["name"].encode("utf-8")
                # also try last token only
                parts = [raw]
                if " " in r["name"]:
                    parts.append(r["name"].split()[-1].encode("utf-8"))
                    parts.append(r["name"].split()[0].encode("utf-8"))
                best_rad = None
                best_delta = None
                for part in parts:
                    hits = find_all(mm, part, limit=40)
                    for h in hits:
                        d = abs(h - r["site"])
                        for rad in RADII:
                            if d <= rad and (best_rad is None or rad < best_rad):
                                best_rad = rad
                                best_delta = h - r["site"]
                if best_rad is not None:
                    name_ok[best_rad] += 1
                lines.append(
                    f"  {r['name']}: name_within={best_rad} delta={best_delta}"
                )
            lines.append(f"name radius histogram: {dict(name_ok)}")

            # --- C: shared relative pointers dab → site ---
            lines.append("\n## C: u32 at dab+rel equals DOB site abs (or site-dab delta)")
            # Check whether dab±N holds absolute pointer to site, or delta, or site//something
            ptr_hits: Counter[int] = Counter()
            delta_store: Counter[int] = Counter()
            for rel in range(-512, 513, 1):
                ok_abs = 0
                ok_delta = 0
                usable = 0
                for r in rows:
                    if r["dab"] is None or r["site"] is None:
                        continue
                    abs_off = r["dab"] + rel
                    if abs_off < 0 or abs_off + 4 > len(mm):
                        continue
                    usable += 1
                    val = struct.unpack_from("<I", mm, abs_off)[0]
                    if val == r["site"]:
                        ok_abs += 1
                    if val == (r["site"] - r["dab"]) & 0xFFFFFFFF:
                        ok_delta += 1
                    if val == r["site"] - r["dab"]:
                        ok_delta += 1
                if ok_abs >= 8:
                    ptr_hits[rel] = ok_abs
                if ok_delta >= 8:
                    delta_store[rel] = ok_delta
            lines.append(f"abs-ptr rels (≥8): {ptr_hits.most_common(20)}")
            lines.append(f"delta-store rels (≥8): {delta_store.most_common(20)}")

            # --- D: common 4-byte tokens appearing BOTH near dab (±256) and near site (±64) ---
            lines.append("\n## D: shared tokens near dab AND near DOB site (need ≥10 players)")
            # For each player, tokens in dab±256 ∩ tokens in site±64; then which token appears for many players
            token_players: dict[bytes, set[str]] = defaultdict(set)
            for r in rows:
                if r["dab"] is None or r["site"] is None:
                    continue
                dab_toks: set[bytes] = set()
                site_toks: set[bytes] = set()
                for base, radius, bucket in (
                    (r["dab"], 256, dab_toks),
                    (r["site"], 64, site_toks),
                ):
                    lo = max(0, base - radius)
                    hi = min(len(mm), base + radius)
                    blob = bytes(mm[lo:hi])
                    for i in range(0, len(blob) - 3):
                        tok = blob[i : i + 4]
                        # skip obvious zeros / ffff / mark
                        if tok in (
                            b"\x00\x00\x00\x00",
                            b"\xff\xff\xff\xff",
                            MARK,
                        ):
                            continue
                        bucket.add(tok)
                for tok in dab_toks & site_toks:
                    # reject if token is the DOB days themselves
                    if tok == struct.pack("<I", r["days"]):
                        continue
                    if tok == struct.pack("<I", r["uid"]):
                        token_players[tok].add(r["name"] + "|uid")
                        continue
                    token_players[tok].add(r["name"])
            shared = sorted(
                ((len(names), tok.hex(), sorted(names)[:8]) for tok, names in token_players.items()),
                reverse=True,
            )
            for n, hx, names in shared[:30]:
                if n < 5:
                    break
                lines.append(f"  n={n} tok={hx} eg={names}")

            # --- E: fingerprint bytes immediately before mark+days ---
            lines.append("\n## E: 16 bytes immediately before mark+days (and after days+8)")
            before: Counter[bytes] = Counter()
            after: Counter[bytes] = Counter()
            for r in rows:
                if r["site"] is None:
                    continue
                s = r["site"]
                if s >= 16:
                    before[bytes(mm[s - 16 : s])] += 1
                after[bytes(mm[s + 8 : s + 24])] += 1
            lines.append("before top:")
            for b, n in before.most_common(12):
                lines.append(f"  n={n} {b.hex()}")
            lines.append("after top:")
            for b, n in after.most_common(12):
                lines.append(f"  n={n} {b.hex()}")

            # --- F: search from dab for MARK + plausible DOB days for THIS player's age ---
            lines.append("\n## F: from dab, nearest MARK+days in birth-year range for fixture age")
            # without knowing DOB, would we find the right days near dab? (we already know no)
            # Instead: scan ALL unique mark+days and see if any value at dab+rel points at their index
            all_dob_sites: list[tuple[int, int]] = []  # (abs, days)
            j = mm.find(MARK)
            scanned = 0
            while j >= 0 and scanned < 200_000:
                if j + 8 <= len(mm):
                    days = struct.unpack_from("<I", mm, j + 4)[0]
                    # birth-ish: 1985–2025 → days ~31000-46000
                    if 30_000 <= days <= 46_000:
                        trail = bytes(mm[j + 8 : j + 12]) if j + 12 <= len(mm) else b""
                        # prefer sites that look like our known layout (ffff or second mark)
                        if trail in (b"\xff\xff\xff\xff", MARK) or True:
                            all_dob_sites.append((j, days))
                scanned += 1
                j = mm.find(MARK, j + 1)

            lines.append(f"candidate mark+days birth-ish sites: {len(all_dob_sites)}")
            # Map days→site for known players; check uniqueness
            by_days: dict[int, list[int]] = defaultdict(list)
            for abs_s, days in all_dob_sites:
                by_days[days].append(abs_s)
            unique = sum(1 for r in rows if r["days"] in by_days and len(by_days[r["days"]]) == 1)
            lines.append(f"known DOBs with unique mark+days site among birth-ish: {unique}/{len(rows)}")

            # --- G: does personIndex as u32 appear near DOB site? ---
            lines.append("\n## G: personIndex near DOB site / shared offset from site")
            pi_ok = Counter()
            pi_rel: Counter[int] = Counter()
            for r in rows:
                pi = r.get("personIndex")
                # also try reading pi from dab+31
                if r["dab"] is not None and r["dab"] + 35 <= len(mm):
                    pi2 = struct.unpack_from("<I", mm, r["dab"] + 31)[0]
                    if 0 < pi2 < 200_000:
                        pi = pi2
                if pi is None or r["site"] is None:
                    continue
                for rad in RADII:
                    hits = u32_hits_in_window(mm, r["site"], rad, int(pi))
                    if hits:
                        pi_ok[rad] += 1
                        for h in hits:
                            pi_rel[h - r["site"]] += 1
                        break
            lines.append(f"pi radius histogram: {dict(pi_ok)}")
            lines.append(f"pi rel to site top: {pi_rel.most_common(15)}")

            # --- H: look for uid as double near DOB site ---
            lines.append("\n## H: UID double near DOB site")
            dbl_ok = Counter()
            for r in rows:
                if r["site"] is None:
                    continue
                pat = struct.pack("<II", r["uid"], r["uid"])
                hits = find_all(mm, pat, limit=20)
                best_rad = None
                best_d = None
                for h in hits:
                    d = abs(h - r["site"])
                    for rad in RADII:
                        if d <= rad and (best_rad is None or rad < best_rad):
                            best_rad = rad
                            best_d = h - r["site"]
                if best_rad is not None:
                    dbl_ok[best_rad] += 1
                lines.append(f"  {r['name']}: double_within={best_rad} delta={best_d}")
            lines.append(f"double radius histogram: {dict(dbl_ok)}")

            # --- I: year-of-birth u16 near dab consensus ---
            lines.append("\n## I: year-of-birth u16 near dab (consensus)")
            year_rel: Counter[int] = Counter()
            for r in rows:
                if r["dab"] is None:
                    continue
                year = r["dob"].year
                pat = struct.pack("<H", year)
                lo = max(0, r["dab"] - 2048)
                hi = min(len(mm), r["dab"] + 2048)
                window = bytes(mm[lo:hi])
                start = 0
                while True:
                    j = window.find(pat, start)
                    if j < 0:
                        break
                    year_rel[lo + j - r["dab"]] += 1
                    start = j + 1
            lines.append(f"year_u16 rel top: {year_rel.most_common(20)}")

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
