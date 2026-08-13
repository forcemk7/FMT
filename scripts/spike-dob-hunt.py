#!/usr/bin/env python3
"""
Hunt DOB encodings near person double-UID using screenshot UIDs.

Input: tmp/fm-spike/dob-hunt-players.json
Save:  data/saves/*.fm
Out:   tmp/fm-spike/dob-hunt-results.txt
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "dob-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-hunt-results.txt"
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PERSON_HEAD = 512 * 1024 * 1024
RADIUS = 8192

EPOCHS = {
    "y1900": date(1900, 1, 1),
    "excel": date(1899, 12, 30),
    "unix": date(1970, 1, 1),
    "y0001": date(1, 1, 1),
}


def ensure_decomp() -> Path:
    if DECOMP.exists() and DECOMP.stat().st_size >= PERSON_HEAD // 2:
        return DECOMP
    print("decompressing save head…", flush=True)
    DECOMP.parent.mkdir(parents=True, exist_ok=True)
    with SAVE.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf." and head[25] == 3
        reader = zstd.ZstdDecompressor().stream_reader(f)
        written = 0
        with DECOMP.open("wb") as out:
            while written < PERSON_HEAD:
                chunk = reader.read(min(8 * 1024 * 1024, PERSON_HEAD - written))
                if not chunk:
                    break
                out.write(chunk)
                written += len(chunk)
        reader.close()
    return DECOMP


def collect_doubles(buf: mmap.mmap, uid: int, limit: int = 12) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(buf), PERSON_HEAD)
    j = buf.find(pat, 0, end)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = buf.find(pat, j + 1, end)
    return hits


def score_person_double(buf: mmap.mmap, dab: int) -> int:
    blob = bytes(buf[dab : dab + 128])
    score = 0
    if b"\x01\x01\x01" in blob[8:80]:
        score += 5
    if len(blob) > 8 and blob[8] in (1, 2):
        score += 1
    # Prefer records with 01 00 6c 07 date-type marker in trail
    if bytes.fromhex("01006c07") in blob:
        score += 3
    return score


def best_double(buf: mmap.mmap, doubles: list[int]) -> int | None:
    if not doubles:
        return None
    return sorted(doubles, key=lambda d: (-score_person_double(buf, d), d))[0]


def dob_patterns(dob_s: str) -> dict[str, bytes]:
    y, m, d = map(int, dob_s.split("-"))
    dob = date(y, m, d)
    pats: dict[str, bytes] = {
        "dmy": struct.pack("<BBH", d, m, y),
        "ymd": struct.pack("<HBB", y, m, d),
        "ymd_be": struct.pack(">HBB", y, m, d),
        "packed_dmy": struct.pack("<I", d | (m << 8) | (y << 16)),
        "year_u16": struct.pack("<H", y),
        "ymd_u32": struct.pack("<I", y * 10000 + m * 100 + d),
        "bits_y9m4d5": struct.pack("<H", ((y - 1900) << 9) | (m << 5) | d),
    }
    for ename, epoch in EPOCHS.items():
        days = (dob - epoch).days
        if 0 <= days <= 0xFFFFFFFF:
            pats[f"days_{ename}_u32"] = struct.pack("<I", days)
            pats[f"tag02_days_{ename}"] = b"\x02" + struct.pack("<I", days)
            pats[f"tag01_days_{ename}"] = b"\x01" + struct.pack("<I", days)
            pats[f"tag6c07_days_{ename}"] = bytes.fromhex("01006c07") + struct.pack(
                "<I", days
            )
    return pats


def scan_offsets(win: bytes, rel0: int, pat: bytes) -> list[int]:
    offs: list[int] = []
    start = 0
    while True:
        i = win.find(pat, start)
        if i < 0:
            break
        offs.append(i - rel0)
        start = i + 1
    return offs


def main() -> None:
    lines: list[str] = [
        f"save={SAVE.name}",
        f"players={len(PLAYERS)} (deduped from screenshots)",
        f"radius=±{RADIUS}",
        "",
    ]
    decomp = ensure_decomp()
    print(f"decomp={decomp} bytes={decomp.stat().st_size}", flush=True)

    # pattern -> player -> set(rel offsets from best double)
    by_pat: dict[str, dict[str, set[int]]] = defaultdict(dict)
    missing_double: list[str] = []

    with decomp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                uid = int(p["uid"])
                name = p["name"]
                doubles = collect_doubles(mm, uid)
                dab = best_double(mm, doubles)
                lines.append(
                    f"## {name} uid={uid} dob={p['dob']} doubles={len(doubles)} best={dab}"
                )
                if dab is None:
                    missing_double.append(name)
                    lines.append("  NO double-UID in PERSON_HEAD")
                    continue

                lo = max(0, dab - RADIUS)
                hi = min(len(mm), dab + RADIUS)
                win = bytes(mm[lo:hi])
                rel0 = dab - lo
                pats = dob_patterns(p["dob"])
                hits_here: dict[str, list[int]] = {}
                for k, pat in pats.items():
                    offs = scan_offsets(win, rel0, pat)
                    if offs:
                        hits_here[k] = offs[:16]
                        by_pat[k][name] = set(offs)

                if hits_here:
                    for k, offs in sorted(hits_here.items()):
                        lines.append(f"  {k}: {offs}")
                else:
                    lines.append("  (no classic DOB patterns in window)")

                # also note marker positions
                for mk, raw in {
                    "mark_01006c07": bytes.fromhex("01006c07"),
                    "mark_6c07": bytes.fromhex("6c07"),
                }.items():
                    offs = scan_offsets(win, rel0, raw)
                    if offs:
                        lines.append(f"  {mk}: {offs[:12]}")
        finally:
            mm.close()

    lines.append("\n## SHARED relative offsets (same offset for ALL players with a hit)")
    n_players = len(PLAYERS) - len(missing_double)
    for pat, per in sorted(by_pat.items()):
        if len(per) < max(3, n_players // 2):
            continue
        sets = list(per.values())
        shared = set.intersection(*sets) if sets else set()
        # also majority vote: offsets appearing for ≥70% of players that hit this pat
        ctr: Counter[int] = Counter()
        for s in sets:
            ctr.update(s)
        majority = sorted(
            [off for off, n in ctr.items() if n >= max(3, int(0.7 * len(per)))]
        )
        if shared or majority:
            lines.append(
                f"  {pat}: players={len(per)}/{n_players} shared={sorted(shared)[:20]} majority70={majority[:20]}"
            )

    lines.append("\n## candidate: fixed offset after 01 00 6c 07 near double")
    # For each player, find first 01 00 6c 07 after double, dump following 16 bytes
    with decomp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                uid = int(p["uid"])
                dab = best_double(mm, collect_doubles(mm, uid))
                if dab is None:
                    continue
                blob = bytes(mm[dab : dab + 256])
                mark = bytes.fromhex("01006c07")
                j = blob.find(mark)
                if j < 0:
                    lines.append(f"  {p['name']}: no 01 00 6c 07 in +256")
                    continue
                trail = blob[j : j + 24]
                lines.append(
                    f"  {p['name']} @{j}: {trail.hex(' ')}  dob={p['dob']}"
                )
        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8")[-4000:])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
