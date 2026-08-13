#!/usr/bin/env python3
"""Sprint 11: Assan/Muller CAPA via all UID sites + nearest MAGIC rule."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint11-assan-muller.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

MAGIC = b"\x08\x02\x40\x30\x04\x00\x00\x00"
LOOKBACK = 64_000

PLAYERS = [
    ("Assan", 2000188173, 186, 190),
    ("Muller", 2002266341, None, None),
    ("Seimen", 2000175080, None, None),
    ("Kizza", 2002185604, 165, 165),  # control
]


def pick_bin() -> Path:
    for p in CANDIDATE_BINS:
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no ~2GB fmt-*.bin")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 500) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def parse(mm: mmap.mmap, at: int) -> dict | None:
    if at + 31 > len(mm) or bytes(mm[at : at + 8]) != MAGIC:
        return None
    rid = struct.unpack_from("<I", mm, at + 8)[0]
    p1 = struct.unpack_from("<I", mm, at + 12)[0]
    p2 = struct.unpack_from("<I", mm, at + 16)[0]
    if p1 != p2 or mm[at + 20] != 0x02:
        return None
    x, y, z, ca, pa = struct.unpack_from("<HHHHH", mm, at + 21)
    if not (1 <= ca <= 200 and 1 <= pa <= 200):
        return None
    return {"at": at, "id": rid, "ca": ca, "pa": pa, "xyz": (x, y, z)}


def nearest_capa(mm: mmap.mmap, anchor: int) -> dict | None:
    lo = max(0, anchor - LOOKBACK)
    best = None
    start = lo
    while True:
        j = mm.find(MAGIC, start, anchor)
        if j < 0:
            break
        b = parse(mm, j)
        if b and (best is None or b["at"] > best["at"]):
            best = b
        start = j + 1
    return best


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint11 · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for name, uid, tca, tpa in PLAYERS:
                hits = [h for h in find_all(mm, struct.pack("<I", uid)) if h < 800_000_000]
                lines.append(f"## {name} uid={uid} truth={tca}/{tpa} uid_hits_early={len(hits)}")

                # Score anchors: prefer double-UID sites
                nb = struct.pack("<I", uid)
                doubles = []
                singles = []
                for h in hits:
                    if mm.find(nb, h + 4, min(len(mm), h + 48)) > 0:
                        doubles.append(h)
                    else:
                        singles.append(h)

                results = []
                for label, anchors in (("double", doubles), ("single", singles[:40])):
                    for a in anchors:
                        b = nearest_capa(mm, a)
                        if not b:
                            continue
                        gap = a - b["at"]
                        truth = tca is not None and b["ca"] == tca and b["pa"] == tpa
                        results.append((truth, gap, label, a, b))

                # Prefer truth matches, then smallest gap
                results.sort(key=lambda r: (not r[0], r[1]))
                lines.append(f"  anchors_with_capa={len(results)} (showing top 12)")
                for truth, gap, label, a, b in results[:12]:
                    mark = " <<TRUTH" if truth else ""
                    lines.append(
                        f"  {label}@{a} → ca/pa={b['ca']}/{b['pa']} "
                        f"id={b['id']:#x} gap={gap}{mark}"
                    )

                # Also: direct search for truth pair near any uid hit
                if tca is not None:
                    pair = struct.pack("<HH", tca, tpa)
                    close = []
                    for a in hits:
                        lo = max(0, a - LOOKBACK)
                        j = bytes(mm[lo:a]).rfind(pair)
                        if j >= 0:
                            close.append((a - (lo + j), a, lo + j))
                    close.sort()
                    lines.append(f"  truth-pair near UID: {close[:8]}")

        finally:
            mm.close()

    lines.append("")
    lines.append(f"elapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
