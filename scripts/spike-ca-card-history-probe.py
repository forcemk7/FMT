#!/usr/bin/env python3
"""Probe: do multi CA cards before a person double look like attribute history?"""

from __future__ import annotations

import json
import mmap
import struct
import tempfile
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
ZSTD_MAGIC = bytes.fromhex("28b52ffd")
ATTR_LOOKBACK = 20_000

MENTAL = [
    "aggression",
    "anticipation",
    "bravery",
    "vision",
    "decisions",
    "determination",
    "flair",
    "leadership",
]


def disp(b: bytes) -> list[int]:
    return [round(x / 5) for x in b]


def is_attrish(buf: bytes, i: int) -> bool:
    if i + 69 > len(buf):
        return False
    if buf[i + 34] or buf[i + 35] or buf[i + 43] != 0x01:
        return False
    return sum(1 for x in buf[i : i + 22] if 25 <= x <= 105) >= 12


def collect_cards(window: bytes) -> list[tuple[int, bytes]]:
    out: list[tuple[int, bytes]] = []
    start = 0
    while True:
        z = window.find(b"\x00\x00", start)
        if z < 0 or z + 35 > len(window):
            break
        i = z - 34
        if i >= 0 and z == i + 34 and is_attrish(window, i):
            out.append((i, window[i : i + 69]))
            start = z + 69
        else:
            start = z + 1
    return out


def find_zstd_off(path: Path) -> int:
    """Match extract-first-team-fast probe: prefer offset 26, then magic hits."""
    size = path.stat().st_size
    with path.open("rb") as f:
        head = f.read(256)
    zstd_offsets = []
    start = 0
    while True:
        j = head.find(ZSTD_MAGIC, start)
        if j < 0:
            break
        zstd_offsets.append(j)
        start = j + 1
    for off in sorted({26, *zstd_offsets, 0, 16, 24, 28, 32}):
        if off >= min(len(head), size):
            continue
        try:
            with path.open("rb") as f:
                f.seek(off)
                reader = zstd.ZstdDecompressor().stream_reader(f)
                try:
                    chunk = reader.read(8 * 1024)
                finally:
                    reader.close()
            if chunk:
                return off
        except Exception:
            continue
    raise SystemExit("no usable zstd offset")


def decompress_to_mmap() -> tuple[Path, mmap.mmap]:
    zoff = find_zstd_off(SAVE)
    tmp_path = Path(tempfile.mkstemp(suffix=".bin")[1])
    out_bytes = 0
    with SAVE.open("rb") as f, tmp_path.open("wb") as out:
        f.seek(zoff)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    chunk = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    # FM containers can stop mid-stream with a trailer; keep what we have.
                    if out_bytes == 0:
                        raise
                    break
                if not chunk:
                    break
                out.write(chunk)
                out_bytes += len(chunk)
        finally:
            reader.close()
    fobj = tmp_path.open("r+b")
    mm = mmap.mmap(fobj.fileno(), 0, access=mmap.ACCESS_READ)
    # Keep file handle alive for the life of the mmap (Windows).
    return tmp_path, mm, fobj


def probe(mm: mmap.mmap, name: str, double_abs: int, lines: list[str]) -> None:
    lo = max(0, double_abs - ATTR_LOOKBACK)
    window = bytes(mm[lo:double_abs])
    cards = collect_cards(window)
    lines.append(f"\n=== {name} double@{double_abs} cards={len(cards)} ===")
    by_u16: dict[int, list[tuple[int, int, int, int, int]]] = defaultdict(list)
    # (gap, b23, u16, det, lea)
    rows = []
    for off, rec in cards:
        gap = len(window) - off
        u16 = struct.unpack_from("<H", rec, 36)[0]
        ment = disp(rec[0:14])
        det, lea = ment[5], ment[7]
        b23 = rec[23]
        rows.append((gap, b23, u16, det, lea, off))
        by_u16[u16].append((gap, b23, det, lea))

    rows.sort(key=lambda r: (-r[0], r[1]))  # farthest first, then b23
    lines.append("gap  b23   u16  det lea   (sorted far→near)")
    for gap, b23, u16, det, lea, _off in rows:
        band = "NEAR" if 1200 <= gap <= 14000 else "FAR "
        lines.append(f"{gap:5d} {b23:3d} {u16:5d} {det:3d} {lea:3d}  {band}")

    lines.append("per-u16 strip summary (gap-sorted det/lea sequence):")
    for u16, group in sorted(by_u16.items(), key=lambda kv: -len(kv[1])):
        group_sorted = sorted(group, key=lambda t: -t[0])  # far→near
        dets = [d for _g, _b, d, _l in group_sorted]
        leas = [l for _g, _b, _d, l in group_sorted]
        b23s = [b for _g, b, _d, _l in group_sorted]
        gaps = [g for g, _b, _d, _l in group_sorted]
        unique_det = len(set(dets))
        monotone_det = all(a <= b for a, b in zip(dets, dets[1:])) or all(
            a >= b for a, b in zip(dets, dets[1:])
        )
        lines.append(
            f"  u16={u16} n={len(group_sorted)} gaps={gaps[0]}..{gaps[-1]} "
            f"b23={b23s[0]}..{b23s[-1]} det={dets} lea={leas} "
            f"uniqueDet={unique_det} monotoneDet≈{monotone_det}"
        )


def main() -> None:
    verify = json.loads(
        (ROOT / "tmp/fm-spike/extract-ft-verify.json").read_text(encoding="utf-8-sig")
    )
    want = {
        2002166919: "Koné",
        2000175080: "Seimen",
        2002400283: "Gabor",
        2002234366: "Bandeira",
    }
    doubles = {}
    for pl in verify["players"]:
        uid = pl.get("uid")
        if uid in want and pl.get("doubleUidAbs"):
            doubles[uid] = (want[uid], pl["doubleUidAbs"])

    lines = [
        f"save={SAVE.name}",
        "Question: multiple 69B attr cards — history timeline or something else?",
    ]
    tmp_path, mm, fobj = decompress_to_mmap()
    try:
        for uid, (name, dab) in doubles.items():
            probe(mm, f"{name} ({uid})", dab, lines)
        out = ROOT / "tmp/fm-spike/ca-card-history-probe.txt"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(out)
        print("\n".join(lines[:120]))
    finally:
        try:
            mm.close()
        finally:
            try:
                fobj.close()
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except PermissionError:
                    pass


if __name__ == "__main__":
    main()
