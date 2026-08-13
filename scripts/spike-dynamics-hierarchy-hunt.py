#!/usr/bin/env python3
"""
Hunt Dynamics hierarchy enums near FT listAbs using labeled ground truth.

Uses data/fixtures/dynamics-ground-truth-baseline-wip.json + tmp/probe-extract-out.json
against data/saves/dynamics-a.fm (or --save). Streams zstd; keeps only a window
around listAbs so we avoid a full 2GB mmap when possible.
"""

from __future__ import annotations

import argparse
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
OUT = ROOT / "tmp" / "fm-spike" / "dynamics-hierarchy-hunt.txt"
GT_PATH = ROOT / "data" / "fixtures" / "dynamics-ground-truth-baseline-wip.json"
PROBE_PATH = ROOT / "tmp" / "probe-extract-out.json"
DEFAULT_SAVE = ROOT / "data" / "saves" / "dynamics-a.fm"

HIER_ORDER = ("teamLeader", "highlyInfluential", "influential", "other")
HIER_CODE = {name: i for i, name in enumerate(HIER_ORDER)}


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


_CP437_CHARS = bytes(range(256)).decode("cp437")
_CP437_REV = {c: i for i, c in enumerate(_CP437_CHARS)}


def fix_mojibake(s: str) -> str:
    """Repair UTF-8 that was decoded as CP437 then re-encoded (redirect artifacts)."""
    try:
        repaired = bytes(_CP437_REV[c] for c in s).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return s
    if repaired == s:
        return s
    # Prefer repaired when it restores combining-latin letters
    if any(ord(c) > 127 for c in repaired):
        return repaired
    return s


def norm_name(s: str) -> str:
    import unicodedata

    s = fix_mojibake(s).replace("\u00df", "ss")
    s = "".join(
        c
        for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    return " ".join(s.casefold().split())


def load_labeled_roster() -> tuple[dict, list[dict]]:
    gt = json.loads(GT_PATH.read_text(encoding="utf-8-sig"))
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8-sig"))
    by_name: dict[str, dict] = {}
    for p in probe["players"]:
        by_name[norm_name(p["name"])] = p

    labeled: list[dict] = []
    missing: list[str] = []
    for row in gt["players"]:
        h = row.get("hierarchy")
        if h not in HIER_CODE:
            continue
        hit = by_name.get(norm_name(row["name"]))
        if not hit:
            missing.append(row["name"])
            continue
        labeled.append(
            {
                "name": row["name"],
                "hierarchy": h,
                "code": HIER_CODE[h],
                "uid": int(hit["uid"]),
                "jobId": int(hit["jobId"]),
                "socialGroup": row.get("socialGroup"),
                "captaincy": row.get("captaincy"),
            }
        )
    if missing:
        raise SystemExit(f"Unmapped ground-truth names: {missing}")
    return gt, labeled


def decompress_full(mod, save: Path) -> Path:
    zstd_off = int(mod.probe_container(save)["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-dyn-h-", suffix=".bin")
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


def score_u8_array(values: list[int], expected: list[int]) -> tuple[float, dict]:
    """Best remapping of observed distinct values → hierarchy codes."""
    if len(values) != len(expected):
        return -1.0, {}
    obs = sorted(set(values))
    if not (2 <= len(obs) <= 6):
        return -1.0, {}
    # Brute force assignments of obs → 0..3 (allow unused codes)
    from itertools import permutations

    codes = list(range(4))
    best = -1.0
    best_map: dict[int, int] = {}
    # Try mapping len(obs) observed symbols onto 4 codes (injective)
    if len(obs) > 4:
        return -1.0, {}
    for perm in permutations(codes, len(obs)):
        mapping = {obs[i]: perm[i] for i in range(len(obs))}
        mapped = [mapping[v] for v in values]
        hits = sum(1 for a, b in zip(mapped, expected) if a == b)
        score = hits / len(expected)
        # Prefer exact count signature too
        cnt = Counter(mapped)
        want = Counter(expected)
        count_bonus = sum(min(cnt[k], want[k]) for k in want) / len(expected)
        total = 0.7 * score + 0.3 * count_bonus
        if total > best:
            best = total
            best_map = mapping
    return best, best_map


def hunt_near_ids(
    mm: mmap.mmap,
    labeled: list[dict],
    list_abs: int,
    window: int,
    lines: list[str],
) -> None:
    lo = max(0, list_abs - window)
    hi = min(len(mm), list_abs + window)
    blob = mm[lo:hi]
    expected = [p["code"] for p in labeled]
    lines.append(f"Window @{lo}..{hi} ({hi - lo:,} bytes) around listAbs={list_abs}")

    # Collect uid/job hit positions (relative to blob)
    id_hits: dict[str, list[int]] = defaultdict(list)
    for p in labeled:
        for key, val in (("uid", p["uid"]), ("jobId", p["jobId"])):
            pat = struct.pack("<I", val)
            start = 0
            while True:
                j = blob.find(pat, start)
                if j < 0:
                    break
                id_hits[f"{key}:{val}"].append(j)
                start = j + 1

    lines.append(
        f"ID hits in window: "
        f"{sum(len(v) for v in id_hits.values())} across {len(id_hits)} keys"
    )

    # Candidate: contiguous u8 table of length N at offsets where many jobIds
    # sit nearby with a shared stride.
    n = len(labeled)
    candidates: list[tuple[float, int, int, dict, list[int]]] = []

    # Strategy A: for each player, look at bytes immediately after/before uid/job
    for delta in range(-64, 65):
        if delta == 0:
            continue
        values: list[int] = []
        abs_samples: list[int] = []
        ok = True
        for p in labeled:
            hits = id_hits.get(f"uid:{p['uid']}", []) + id_hits.get(
                f"jobId:{p['jobId']}", []
            )
            if not hits:
                ok = False
                break
            hit = min(hits, key=lambda h: abs((lo + h) - list_abs))
            off = hit + delta
            if off < 0 or off >= len(blob):
                ok = False
                break
            values.append(blob[off])
            abs_samples.append(lo + off)
        if not ok:
            continue
        score, mapping = score_u8_array(values, expected)
        if score >= 0.55:
            candidates.append(
                (score, abs_samples[0], delta, mapping, values)
            )

    # Strategy B: scan for length-N u8 runs whose value multiset matches counts
    want_counts = Counter(expected)
    # Soft: any 4-bin partition with same sizes after remap
    for i in range(0, len(blob) - n, 1):
        vals = list(blob[i : i + n])
        if max(vals) > 8:
            continue
        if len(set(vals)) < 2 or len(set(vals)) > 5:
            continue
        score, mapping = score_u8_array(vals, expected)
        if score >= 0.7:
            candidates.append((score, lo + i, None, mapping, vals))

    # Strategy C: stride tables — value at base + k*stride for ordered job list
    # Rebuild job order from probe via list at listAbs if present
    jobs = [p["jobId"] for p in labeled]
    # Try to find contiguous jobId list
    job_pat = b"".join(struct.pack("<I", j) for j in jobs[:6])
    job_list_at = blob.find(job_pat)
    lines.append(f"Partial job-list motif (first 6) in window: {job_list_at}")

    candidates.sort(key=lambda x: -x[0])
    lines.append("")
    lines.append(f"=== Top candidates (n={len(candidates)}) ===")
    seen = set()
    shown = 0
    for score, abs_off, delta, mapping, values in candidates:
        key = (round(score, 3), abs_off, delta, tuple(values))
        if key in seen:
            continue
        seen.add(key)
        cnt = Counter(values)
        lines.append(
            f"score={score:.3f} abs={abs_off} delta={delta} "
            f"map={mapping} counts={dict(cnt)}"
        )
        # Show mismatches
        mapped = [mapping.get(v, -1) for v in values]
        bad = [
            (labeled[i]["name"], HIER_ORDER[expected[i]], mapped[i], values[i])
            for i in range(n)
            if mapped[i] != expected[i]
        ]
        lines.append(f"  mismatches={len(bad)} sample={bad[:5]}")
        shown += 1
        if shown >= 40:
            break

    if shown == 0:
        lines.append("No candidates ≥0.55 — hierarchy may live outside ±window or not as u8.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", type=Path, default=DEFAULT_SAVE)
    ap.add_argument("--window", type=int, default=256 * 1024)
    args = ap.parse_args()

    gt, labeled = load_labeled_roster()
    anchors = gt.get("extractAnchors", {})
    list_abs = int(anchors.get("listAbs") or 0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"save={args.save}")
    lines.append(f"labeled={len(labeled)} listAbs={list_abs}")
    counts = Counter(p["hierarchy"] for p in labeled)
    lines.append(f"hierarchy counts={dict(counts)}")

    mod = load_extractor()
    print("decompress…", flush=True)
    tmp = decompress_full(mod, args.save)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                # Prefer live listAbs from this save if discoverable
                squads = mod.discover_squads(mm)
                tid = int(anchors.get("teamId") or 0)
                if tid in squads:
                    live_list, live_count, live_jobs = squads[tid]
                    lines.append(
                        f"live squad tid={tid} listAbs={live_list} "
                        f"countHeader={live_count} jobs={len(live_jobs)}"
                    )
                    list_abs = live_list
                hunt_near_ids(mm, labeled, list_abs, args.window, lines)
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8")[:12000])
    print(f"\n… full log {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
