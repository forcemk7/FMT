#!/usr/bin/env python3
"""Targeted diff dynamics-a vs dynamics-b (Seimen FT → II)."""

from __future__ import annotations

import importlib.util
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE_A = ROOT / "data" / "saves" / "dynamics-a.fm"
SAVE_B = ROOT / "data" / "saves" / "dynamics-b.fm"
OUT = ROOT / "tmp" / "fm-spike" / "dynamics-ab-diff.txt"
SEIMEN_UID = 2000175080


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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-dyn-", suffix=".bin")
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


def diff_window(a: bytes, b: bytes, base: int) -> list[tuple[int, int]]:
    n = min(len(a), len(b))
    runs: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        while i < n and a[i] != b[i]:
            i += 1
        runs.append((base + start, i - start))
    return runs


def sample(mm: mmap.mmap, off: int, before=32, after=64) -> str:
    lo = max(0, off - before)
    hi = min(len(mm), off + after)
    return " ".join(f"{x:02x}" for x in mm[lo:hi])


def all_squads(mod, mm: mmap.mmap) -> dict[int, dict]:
    squads = mod.discover_squads(mm)
    out: dict[int, dict] = {}
    for tid, (list_abs, count, jobs) in squads.items():
        if not (8 <= len(jobs) <= 45):
            continue
        employment = mod.resolve_job_uids_batch(mm, jobs)
        players = []
        for job in jobs:
            uid = employment.get(job)
            if uid is None:
                continue
            players.append(
                {
                    "jobId": job,
                    "uid": uid,
                    "name": mod.resolve_name(mm, uid) or f"uid:{uid}",
                }
            )
        out[tid] = {
            "listAbs": list_abs,
            "countHeader": count,
            "jobs": jobs,
            "players": players,
            "hasSeimen": any(p["uid"] == SEIMEN_UID for p in players),
        }
    return out


def ft_pick(mod, squads: dict[int, dict], mm: mmap.mmap) -> int | None:
    raw = {tid: (s["listAbs"], s["countHeader"], s["jobs"]) for tid, s in squads.items()}
    ft_like = [tid for tid, s in squads.items() if 15 <= len(s["jobs"]) <= 40] or list(
        squads.keys()
    )
    spans = [(0, min(len(mm), 400 * 1024 * 1024))]
    if len(mm) > mod.EMPLOYMENT_TAIL:
        spans.append((len(mm) - mod.EMPLOYMENT_TAIL, len(mm)))
    hits = mod.scan_manager_hits(mm, ft_like, windows=spans)
    return mod.pick_tid(raw, hits)


def uid_windows(mm: mmap.mmap, uid: int, window: int = 512) -> list[tuple[int, int]]:
    pat = struct.pack("<I", uid)
    seen: set[tuple[int, int]] = set()
    pos = 0
    while True:
        j = mm.find(pat, pos)
        if j < 0:
            break
        lo = max(0, j - window)
        hi = min(len(mm), j + 4 + window)
        key = (lo // 256, hi // 256)
        if key not in seen:
            seen.add(key)
        pos = j + 1
    return sorted((lo, hi - lo) for lo, hi in ((max(0, j - window), min(len(mm), j + 4 + window)) for j in _uid_positions(mm, uid)))


def _uid_positions(mm: mmap.mmap, uid: int) -> list[int]:
    pat = struct.pack("<I", uid)
    out: list[int] = []
    pos = 0
    while True:
        j = mm.find(pat, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    pat2 = b"\x00\x02" + pat
    pos = 0
    while True:
        j = mm.find(pat2, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    return sorted(set(out))


def main() -> int:
    mod = load_extractor()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print("decompress A...")
    tmp_a = decompress(mod, SAVE_A)
    print("decompress B...")
    tmp_b = decompress(mod, SAVE_B)
    lines: list[str] = []
    try:
        with tmp_a.open("rb") as fa, tmp_b.open("rb") as fb:
            ma = mmap.mmap(fa.fileno(), 0, access=mmap.ACCESS_READ)
            mb = mmap.mmap(fb.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                lines.append(f"A {len(ma):,} bytes  B {len(mb):,} bytes")
                squads_a = all_squads(mod, ma)
                squads_b = all_squads(mod, mb)
                ft_a = ft_pick(mod, squads_a, ma)
                ft_b = ft_pick(mod, squads_b, mb)
                lines.append(f"FT tid A={ft_a} B={ft_b}")

                seimen_squads_a = [tid for tid, s in squads_a.items() if s["hasSeimen"]]
                seimen_squads_b = [tid for tid, s in squads_b.items() if s["hasSeimen"]]
                lines.append(f"Seimen squads A={seimen_squads_a}")
                lines.append(f"Seimen squads B={seimen_squads_b}")

                for label, squads, tid in (
                    ("A", squads_a, ft_a),
                    ("B", squads_b, ft_b),
                ):
                    if tid is None or tid not in squads:
                        continue
                    s = squads[tid]
                    lines.append(
                        f"{label} FT listAbs={s['listAbs']} n={len(s['players'])} seimen={s['hasSeimen']}"
                    )

                # Windows to diff
                windows: list[tuple[int, int, str]] = []
                for tid, s in squads_a.items():
                    la = s["listAbs"]
                    windows.append((la - 8192, 16384, f"listAbs tid={tid} A"))
                for tid, s in squads_b.items():
                    la = s["listAbs"]
                    windows.append((la - 8192, 16384, f"listAbs tid={tid} B"))
                if len(ma) > mod.EMPLOYMENT_TAIL:
                    tail = len(ma) - mod.EMPLOYMENT_TAIL
                    windows.append((tail, mod.EMPLOYMENT_TAIL, "employment tail"))
                for lo, ln in uid_windows(ma, SEIMEN_UID, 768):
                    windows.append((lo, ln, "seimen uid A"))
                for lo, ln in uid_windows(mb, SEIMEN_UID, 768):
                    windows.append((lo, ln, "seimen uid B"))

                # Merge overlapping windows
                windows.sort()
                merged: list[tuple[int, int, str]] = []
                for lo, ln, tag in windows:
                    if merged and lo <= merged[-1][0] + merged[-1][1] + 64:
                        prev_lo, prev_ln, prev_tag = merged[-1]
                        end = max(prev_lo + prev_ln, lo + ln)
                        merged[-1] = (prev_lo, end - prev_lo, prev_tag + "+" + tag)
                    else:
                        merged.append((lo, ln, tag))

                lines.append("")
                lines.append(f"=== Targeted window diffs ({len(merged)} windows) ===")
                all_runs: list[tuple[int, int, str]] = []
                for lo, ln, tag in merged:
                    lo = max(0, lo)
                    hi = min(len(ma), len(mb), lo + ln)
                    if hi <= lo:
                        continue
                    runs = diff_window(bytes(ma[lo:hi]), bytes(mb[lo:hi]), lo)
                    if runs:
                        lines.append(f"\n-- {tag} @{lo} len={hi-lo} ({len(runs)} runs) --")
                        for off, rlen in sorted(runs, key=lambda x: -x[1])[:12]:
                            all_runs.append((off, rlen, tag))
                            lines.append(f"  @{off} len={rlen}")
                            lines.append(f"    A: {sample(ma, off)}")
                            lines.append(f"    B: {sample(mb, off)}")

                lines.append("")
                lines.append("=== Largest targeted runs ===")
                for off, rlen, tag in sorted(all_runs, key=lambda x: -x[1])[:25]:
                    lines.append(f"@{off} len={rlen} ({tag})")
                    lines.append(f"  A: {sample(ma, off, 48, 80)}")
                    lines.append(f"  B: {sample(mb, off, 48, 80)}")

            finally:
                ma.close()
                mb.close()
    finally:
        tmp_a.unlink(missing_ok=True)
        tmp_b.unlink(missing_ok=True)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = OUT.read_text(encoding="utf-8")
    print(text[:15000])
    if len(text) > 15000:
        print(f"... see {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
