#!/usr/bin/env python3
"""
T001 Dynamics layout lock — hunt hierarchy/social/captaincy against GT.

Strategies:
  1) Parallel u8 array next to FT job list (same order)
  2) Shared byte delta from uid/job hits in listAbs / employment / uid windows
  3) Contiguous u8 table matching count signature
  4) Tier membership lists: concatenated u32 jobId/uid runs per hierarchy/social tier

Writes:
  tmp/fm-spike/t001-dynamics-hunt.txt
  data/fixtures/dynamics-layout-spike-notes.md
  data/fixtures/dynamics-layout-locked.json  (if perfect hit)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import mmap
import os
import struct
import tempfile
import unicodedata
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
GT_PATH = ROOT / "data" / "fixtures" / "dynamics-ground-truth-baseline-wip.json"
OUT_TXT = ROOT / "tmp" / "fm-spike" / "t001-dynamics-hunt.txt"
LOCK_PATH = ROOT / "data" / "fixtures" / "dynamics-layout-locked.json"
NOTES_PATH = ROOT / "data" / "fixtures" / "dynamics-layout-spike-notes.md"

HIER_ORDER = ("teamLeader", "highlyInfluential", "influential", "other")
HIER_CODE = {n: i for i, n in enumerate(HIER_ORDER)}
SOC_ORDER = ("core", "secondaryA", "other")
SOC_CODE = {n: i for i, n in enumerate(SOC_ORDER)}


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def norm(s: str) -> str:
    s = s.replace("\u00df", "ss")
    s = "".join(
        c
        for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    return " ".join(s.casefold().split())


def read_json(path: Path) -> dict:
    raw = path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        return json.loads(raw.decode("utf-16"))
    if raw[:2] == b"\xfe\xff":
        return json.loads(raw.decode("utf-16-be"))
    return json.loads(raw.decode("utf-8-sig"))


def load_labeled(extract: Path) -> tuple[dict, list[dict]]:
    gt = read_json(GT_PATH)
    probe = read_json(extract)
    by_name = {norm(p["name"]): p for p in probe.get("players") or []}
    labeled: list[dict] = []
    missing: list[str] = []
    for row in gt["players"]:
        h = row.get("hierarchy")
        if h not in HIER_CODE:
            continue
        hit = by_name.get(norm(row["name"]))
        if not hit:
            # fall back to GT uid/job if present
            if row.get("uid") and row.get("jobId"):
                labeled.append(
                    {
                        "name": row["name"],
                        "hierarchy": h,
                        "hcode": HIER_CODE[h],
                        "socialGroup": row.get("socialGroup"),
                        "scode": SOC_CODE.get(row.get("socialGroup")),
                        "captaincy": row.get("captaincy"),
                        "uid": int(row["uid"]),
                        "jobId": int(row["jobId"]),
                    }
                )
                continue
            missing.append(row["name"])
            continue
        labeled.append(
            {
                "name": row["name"],
                "hierarchy": h,
                "hcode": HIER_CODE[h],
                "socialGroup": row.get("socialGroup"),
                "scode": SOC_CODE.get(row.get("socialGroup")),
                "captaincy": row.get("captaincy"),
                "uid": int(hit["uid"]),
                "jobId": int(hit["jobId"]),
            }
        )
    if missing:
        raise SystemExit(f"Unmapped GT names: {missing}")
    return gt, labeled


def decompress(mod, save: Path) -> Path:
    zstd_off = int(mod.probe_container(save)["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-t001-", suffix=".bin")
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


def score_remap(values: list[int], expected: list[int], n_codes: int) -> tuple[float, dict]:
    if len(values) != len(expected):
        return -1.0, {}
    obs = sorted(set(values))
    if not (2 <= len(obs) <= n_codes):
        return -1.0, {}
    codes = list(range(n_codes))
    best = -1.0
    best_map: dict[int, int] = {}
    for perm in permutations(codes, len(obs)):
        mapping = {obs[i]: perm[i] for i in range(len(obs))}
        mapped = [mapping[v] for v in values]
        hits = sum(1 for a, b in zip(mapped, expected) if a == b)
        score = hits / len(expected)
        if score > best:
            best = score
            best_map = mapping
    return best, best_map


def find_all(mm: mmap.mmap, pat: bytes, limit: int = 128) -> list[int]:
    out: list[int] = []
    pos = 0
    while len(out) < limit:
        j = mm.find(pat, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    return out


def hunt_membership_lists(
    mm: mmap.mmap,
    labeled: list[dict],
    search_lo: int,
    search_hi: int,
    id_key: str,
    group_key: str,
    order: tuple[str, ...],
    lines: list[str],
    label: str,
) -> list[dict]:
    """Find concatenated u32 id runs for each tier in hierarchy/social order."""
    groups: dict[str, list[int]] = {name: [] for name in order}
    for p in labeled:
        g = p.get(group_key)
        if g in groups:
            groups[g].append(int(p[id_key]))

    # Build motif: first 2 ids of largest tier (stable)
    largest = max(order, key=lambda n: len(groups[n]))
    ids = groups[largest]
    if len(ids) < 2:
        lines.append(f"{label}: too few ids in {largest}")
        return []

    hits: list[dict] = []
    # Try several seed pairs from largest tier
    seeds = []
    for i in range(min(6, len(ids) - 1)):
        seeds.append(ids[i : i + 2])
    for a, b in seeds:
        motif = struct.pack("<II", a, b)
        pos = search_lo
        found = 0
        while found < 20:
            j = mm.find(motif, pos, search_hi)
            if j < 0:
                break
            # Expand window: look for a block containing ALL tier ids nearby
            win_lo = max(search_lo, j - 512)
            win_hi = min(search_hi, j + 512 + 4 * len(labeled))
            blob = mm[win_lo:win_hi]
            # Score: how many labeled ids appear as u32 in window
            present = 0
            positions: dict[int, int] = {}
            for p in labeled:
                pat = struct.pack("<I", p[id_key])
                k = blob.find(pat)
                if k >= 0:
                    present += 1
                    positions[p[id_key]] = win_lo + k
            score = present / len(labeled)
            if score >= 0.9:
                # Check whether each tier's ids are clustered
                tier_spans = {}
                ok_tiers = 0
                for tname in order:
                    tids = groups[tname]
                    offs = [positions[i] for i in tids if i in positions]
                    if len(offs) == len(tids) and tids:
                        span = max(offs) - min(offs)
                        # tight if roughly 4*(n-1) apart
                        expected_span = 4 * (len(tids) - 1)
                        tight = span <= expected_span + 64
                        tier_spans[tname] = {
                            "span": span,
                            "expected": expected_span,
                            "tight": tight,
                            "start": min(offs),
                        }
                        if tight:
                            ok_tiers += 1
                hit = {
                    "kind": f"{label}-membership",
                    "idKey": id_key,
                    "seedAbs": j,
                    "window": [win_lo, win_hi],
                    "score": score,
                    "present": present,
                    "okTiers": ok_tiers,
                    "tierSpans": tier_spans,
                    "anchor": "tier-membership-lists",
                }
                hits.append(hit)
                lines.append(
                    f"  {label} seed@{j} present={present}/{len(labeled)} "
                    f"okTiers={ok_tiers} spans={ {k:v['span'] for k,v in tier_spans.items()} }"
                )
            found += 1
            pos = j + 1
    lines.append(f"{label}-membership candidates: {len(hits)}")
    return hits


def hunt_parallel_u8(
    mm: mmap.mmap,
    labeled: list[dict],
    list_off: int,
    jobs: list[int],
    lines: list[str],
) -> list[dict]:
    by_job = {p["jobId"]: p for p in labeled}
    if not all(j in by_job for j in jobs):
        lines.append(
            f"parallel: jobs not all labeled ({sum(1 for j in jobs if j in by_job)}/{len(jobs)})"
        )
        # use intersection order
        jobs = [j for j in jobs if j in by_job]
    if len(jobs) != len(labeled):
        lines.append(f"parallel: using intersect n={len(jobs)}")
    ordered = [by_job[j] for j in jobs]
    n = len(ordered)
    hits: list[dict] = []
    for expected_key, n_codes, kind in (
        ("hcode", 4, "hierarchy-parallel"),
        ("scode", 3, "social-parallel"),
    ):
        expected = [p[expected_key] for p in ordered]
        if any(v is None for v in expected):
            continue
        lo = max(0, list_off - 128 * 1024)
        hi = min(len(mm), list_off + 128 * 1024 + n)
        blob = mm[lo:hi]
        best = []
        for i in range(0, len(blob) - n):
            vals = list(blob[i : i + n])
            if max(vals) > 16:
                continue
            if len(set(vals)) < 2:
                continue
            score, mapping = score_remap(vals, expected, n_codes)
            if score >= 0.9:
                best.append((score, lo + i, mapping, vals))
        best.sort(key=lambda x: -x[0])
        lines.append(f"{kind}: >=0.9 hits={len(best)}")
        for score, abs_off, mapping, vals in best[:12]:
            hits.append(
                {
                    "kind": kind,
                    "abs": abs_off,
                    "relToList": abs_off - list_off,
                    "score": score,
                    "map": {str(k): v for k, v in mapping.items()},
                    "rawMap": mapping,
                    "values": vals,
                    "listOff": list_off,
                    "jobOrder": jobs,
                    "anchor": "parallel-u8-to-job-list",
                }
            )
            lines.append(
                f"  score={score:.3f} abs={abs_off} rel={abs_off-list_off} "
                f"map={mapping} counts={dict(Counter(vals))}"
            )
    return hits


def hunt_delta(
    mm: mmap.mmap,
    labeled: list[dict],
    regions: list[tuple[int, int, str]],
    expected_key: str,
    n_codes: int,
    lines: list[str],
    label: str,
) -> list[dict]:
    expected = [p[expected_key] for p in labeled]
    if any(v is None for v in expected):
        return []
    hits: list[dict] = []
    for lo, hi, rname in regions:
        chosen: list[int] = []
        ok = True
        mid = (lo + hi) // 2
        for p in labeled:
            cands = []
            for key in ("uid", "jobId"):
                for off in find_all(mm, struct.pack("<I", p[key]), limit=80):
                    if lo <= off < hi:
                        cands.append(off)
            if not cands:
                ok = False
                break
            chosen.append(min(cands, key=lambda x: abs(x - mid)))
        if not ok:
            lines.append(f"{label}/{rname}: incomplete coverage")
            continue
        local = []
        for delta in range(-96, 97):
            if delta == 0:
                continue
            values = []
            good = True
            for base in chosen:
                off = base + delta
                if off < 0 or off >= len(mm):
                    good = False
                    break
                values.append(mm[off])
            if not good or max(values) > 32:
                continue
            score, mapping = score_remap(values, expected, n_codes)
            if score >= 0.9:
                local.append((score, delta, mapping, values))
        local.sort(key=lambda x: -x[0])
        lines.append(f"{label}/{rname}: >=0.9={len(local)}")
        for score, delta, mapping, values in local[:8]:
            hits.append(
                {
                    "kind": label,
                    "region": rname,
                    "delta": delta,
                    "score": score,
                    "map": {str(k): v for k, v in mapping.items()},
                    "rawMap": mapping,
                    "values": values,
                    "anchor": "byte-delta-from-id",
                    "regionRange": [lo, hi],
                }
            )
            lines.append(
                f"  score={score:.3f} delta={delta} map={mapping} "
                f"counts={dict(Counter(values))}"
            )
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--save",
        type=Path,
        default=ROOT / "data" / "saves" / "dynamics-a.fm",
    )
    ap.add_argument(
        "--extract",
        type=Path,
        default=ROOT / "tmp" / "dynamics-a-extract.json",
    )
    args = ap.parse_args()
    if not args.save.exists():
        raise SystemExit(f"missing save {args.save}")
    if not args.extract.exists():
        # GT has uids — still works
        args.extract = GT_PATH

    gt, labeled = load_labeled(args.extract)
    lines: list[str] = []
    lines.append(f"save={args.save}")
    lines.append(f"extract={args.extract}")
    lines.append(f"labeled={len(labeled)}")
    lines.append(f"hierarchy={dict(Counter(p['hierarchy'] for p in labeled))}")
    lines.append(f"social={dict(Counter(p['socialGroup'] for p in labeled))}")

    mod = load_extractor()
    print("decompress…", flush=True)
    tmp = decompress(mod, args.save)
    all_hits: list[dict] = []
    list_abs = 0
    jobs: list[int] = []
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                lines.append(f"decompressedBytes={len(mm):,}")
                tid = int((gt.get("extractAnchors") or {}).get("teamId") or 193616)
                squads = mod.discover_squads(mm)
                if tid in squads:
                    list_abs, count, jobs = squads[tid]
                    lines.append(
                        f"live tid={tid} listAbs={list_abs} count={count} jobs={len(jobs)}"
                    )
                else:
                    lines.append(f"tid {tid} missing from discover_squads")

                # Verify roster overlap via jobs
                labeled_jobs = {p["jobId"] for p in labeled}
                if jobs:
                    lines.append(
                        f"job overlap with GT={len(labeled_jobs & set(jobs))}/{len(labeled)}"
                    )

                regions = []
                if list_abs:
                    regions.append(
                        (
                            max(0, list_abs - 512 * 1024),
                            min(len(mm), list_abs + 512 * 1024),
                            "listAbs±512K",
                        )
                    )
                if len(mm) > mod.EMPLOYMENT_TAIL:
                    regions.append(
                        (len(mm) - mod.EMPLOYMENT_TAIL, len(mm), "employment-tail")
                    )
                # uid windows for a team leader
                leader = next(p for p in labeled if p["hierarchy"] == "teamLeader")
                for h in find_all(mm, struct.pack("<I", leader["uid"]), limit=12)[:8]:
                    regions.append(
                        (max(0, h - 4096), min(len(mm), h + 4096), f"leader-uid@{h}")
                    )

                lines.append("")
                lines.append("=== parallel u8 ===")
                if list_abs and jobs:
                    # confirm job list bytes
                    packed = b"".join(struct.pack("<I", j) for j in jobs)
                    if mm[list_abs : list_abs + len(packed)] == packed:
                        lines.append("job list exact at listAbs")
                        all_hits += hunt_parallel_u8(
                            mm, labeled, list_abs, jobs, lines
                        )
                    else:
                        lines.append("job list NOT exact at listAbs — scanning motif")
                        motif = packed[: 4 * min(8, len(jobs))]
                        j = mm.find(motif, max(0, list_abs - 64 * 1024))
                        lines.append(f"motif at {j}")
                        if j >= 0:
                            all_hits += hunt_parallel_u8(
                                mm, labeled, j, jobs, lines
                            )

                lines.append("")
                lines.append("=== delta near ids ===")
                all_hits += hunt_delta(
                    mm, labeled, regions, "hcode", 4, lines, "hierarchy-delta"
                )
                all_hits += hunt_delta(
                    mm, labeled, regions, "scode", 3, lines, "social-delta"
                )

                lines.append("")
                lines.append("=== membership lists near listAbs ===")
                if list_abs:
                    slo = max(0, list_abs - 2 * 1024 * 1024)
                    shi = min(len(mm), list_abs + 2 * 1024 * 1024)
                    all_hits += hunt_membership_lists(
                        mm, labeled, slo, shi, "jobId", "hierarchy", HIER_ORDER, lines, "hier-job"
                    )
                    all_hits += hunt_membership_lists(
                        mm, labeled, slo, shi, "uid", "hierarchy", HIER_ORDER, lines, "hier-uid"
                    )
                    all_hits += hunt_membership_lists(
                        mm, labeled, slo, shi, "jobId", "socialGroup", SOC_ORDER, lines, "soc-job"
                    )
                    all_hits += hunt_membership_lists(
                        mm, labeled, slo, shi, "uid", "socialGroup", SOC_ORDER, lines, "soc-uid"
                    )

                # Captaincy
                lines.append("")
                lines.append("=== captaincy ===")
                for p in labeled:
                    if not p.get("captaincy"):
                        continue
                    lines.append(
                        f"{p['name']} {p['captaincy']} uid={p['uid']} job={p['jobId']} "
                        f"uidHits={len(find_all(mm, struct.pack('<I', p['uid']), 40))} "
                        f"jobHits={len(find_all(mm, struct.pack('<I', p['jobId']), 40))}"
                    )

            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    perfect = [h for h in all_hits if h.get("score") == 1.0]
    # membership perfect: present==n and okTiers==all
    mem_perfect = [
        h
        for h in all_hits
        if h.get("anchor") == "tier-membership-lists"
        and h.get("score") == 1.0
        and h.get("okTiers", 0) >= 3
    ]
    lines.append("")
    lines.append(f"=== perfect enum hits: {len(perfect)} ===")
    for h in perfect[:15]:
        lines.append(json.dumps({k: v for k, v in h.items() if k != "values"}, sort_keys=True))
    lines.append(f"=== strong membership hits: {len(mem_perfect)} ===")
    for h in mem_perfect[:10]:
        lines.append(json.dumps(h, sort_keys=True))

    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_TXT}")

    best = None
    if perfect:
        best = sorted(perfect, key=lambda h: (-h["score"], h.get("kind", "")))[0]
    elif mem_perfect:
        best = sorted(mem_perfect, key=lambda h: (-h.get("okTiers", 0), -h["score"]))[0]

    # Spike notes always
    notes = []
    notes.append("# Dynamics layout spike notes (T001)\n\n")
    notes.append(f"- Save: `{args.save.name}`\n")
    notes.append(f"- Extract/GT join: `{Path(args.extract).name}`\n")
    notes.append(f"- Labeled players: {len(labeled)}\n")
    notes.append(f"- Hunt log: `{OUT_TXT.relative_to(ROOT).as_posix()}`\n")
    notes.append(f"- Perfect enum hits: {len(perfect)}\n")
    notes.append(f"- Strong membership hits: {len(mem_perfect)}\n\n")
    if best:
        notes.append("## Locked join path\n\n")
        notes.append("```json\n")
        notes.append(json.dumps(best, indent=2, default=str))
        notes.append("\n```\n\n")
        notes.append("## Extract wire-up (T002)\n\n")
        notes.append(
            "1. Discover FT `listAbs` + job list (existing).\n"
            "2. Apply locked join (`anchor` / `relToList` / `delta` / membership window).\n"
            "3. Remap raw codes via `enumMap` to "
            "`teamLeader|highlyInfluential|influential|other` and "
            "`core|secondaryA|other`.\n"
            "4. Captain/vice: resolve from GT captaincy markers once enum path confirmed "
            "(do not invent).\n"
            "5. Fill `player.dynamics.{hierarchy,socialGroup,captaincy}`.\n"
        )
    else:
        notes.append("## Result\n\nNo lockable hit on this save.\n")
    NOTES_PATH.write_text("".join(notes), encoding="utf-8")
    print(f"wrote {NOTES_PATH}")

    if best and best.get("score") == 1.0:
        raw_map = best.get("rawMap") or {
            int(k): v for k, v in (best.get("map") or {}).items() if str(k).isdigit()
        }
        kind = best.get("kind", "")
        lock = {
            "layout": "team-dynamics-v1",
            "status": "locked",
            "description": "Schalke FT Dynamics hierarchy/social from Career Save GT lock",
            "join": {k: v for k, v in best.items() if k != "rawMap"},
            "fields": {
                "hierarchy": {
                    "order": list(HIER_ORDER),
                    "encoding": "u8"
                    if "parallel" in kind or "delta" in kind
                    else "membership-list",
                    "enumMap": {
                        str(k): HIER_ORDER[v]
                        for k, v in raw_map.items()
                        if "hier" in kind or "hierarchy" in kind
                    }
                    or None,
                },
                "socialGroup": {
                    "order": list(SOC_ORDER),
                    "encoding": "u8"
                    if "parallel" in kind or "delta" in kind
                    else "membership-list",
                    "enumMap": {
                        str(k): SOC_ORDER[v]
                        for k, v in raw_map.items()
                        if "soc" in kind or "social" in kind
                    }
                    or None,
                },
                "captaincy": {
                    "values": ["captain", "viceCaptain"],
                    "status": "unlocked",
                    "note": "Wire after hierarchy/social path; GT has Tusjak captain / Suárez VC",
                },
            },
            "groundTruth": {
                "fixture": GT_PATH.name,
                "labeledPlayers": len(labeled),
                "hierarchyCounts": dict(Counter(p["hierarchy"] for p in labeled)),
                "socialCounts": dict(Counter(p["socialGroup"] for p in labeled)),
                "captaincy": {
                    "captain": "Josef Tusjak",
                    "viceCaptain": "Paco Suárez",
                },
            },
            "saveUsed": args.save.name,
            "extractUsed": Path(args.extract).name,
            "listAbs": list_abs,
            "repro": {
                "script": "scripts/spike-dynamics-layout-lock.py",
                "log": OUT_TXT.relative_to(ROOT).as_posix(),
                "notes": NOTES_PATH.relative_to(ROOT).as_posix(),
            },
            "notThis": [
                "Attr-only mentoring influence proxy",
                "Manual Dynamics UI labels (override-only after T003)",
            ],
        }
        LOCK_PATH.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {LOCK_PATH}")
    else:
        print("no lock artifact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
