#!/usr/bin/env python3
"""Sprint 5: inventory Assan person-double windows for CAPA record ids / join keys."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint5-double-inv.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

ASSAN_UID = 2000188173
CAPA_IDS = {653714, 672906}
# also scan a few Kizza/Bandeira CAPA ids for presence near their doubles later
OTHER = {
    2002185604: {587006, 587835, 588375, 588441, 589152, 659146, 669236, 671391},
    2002234366: {645587, 657238, 658351, 674566},
}


def pick_bin() -> Path:
    for p in CANDIDATE_BINS:
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no ~2GB fmt-*.bin")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 400) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def doubles(mm: mmap.mmap, uid: int) -> list[int]:
    hits = find_all(mm, struct.pack("<I", uid), limit=400)
    out = []
    nb = struct.pack("<I", uid)
    for u in hits:
        nxt = mm.find(nb, u + 4, min(len(mm), u + 48))
        if nxt > 0:
            out.append(u)
    return out


def inventory(mm: mmap.mmap, dab: int, radius: int, want: set[int]) -> list[str]:
    lines = []
    lo = max(0, dab - radius)
    hi = min(len(mm), dab + radius)
    found = []
    for off in range(lo, hi - 3):
        v = struct.unpack_from("<I", mm, off)[0]
        if v in want:
            found.append((off - dab, off, v))
    lines.append(f"  hits of target ids in ±{radius}: {len(found)}")
    for rel, off, v in found[:30]:
        lines.append(f"    Δ={rel:+d} val={v} @{off}")
    # also list interesting u32s near dab: 1000..2e6 excluding uid
    nearby = []
    for off in range(max(0, dab - 128), min(len(mm), dab + 256) - 3):
        v = struct.unpack_from("<I", mm, off)[0]
        if v == ASSAN_UID:
            continue
        if 1000 <= v <= 2_000_000 or 2_000_000_000 <= v <= 2_100_000_000:
            nearby.append((off - dab, v))
    lines.append("  interesting u32 near dab (±128/+256):")
    for rel, v in nearby[:60]:
        lines.append(f"    Δ={rel:+d} {v}")
    lines.append(
        "  hex dab-64..+192: "
        + bytes(mm[max(0, dab - 64) : min(len(mm), dab + 192)]).hex(" ")
    )
    return lines


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint5 double inventory · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            dabs = doubles(mm, ASSAN_UID)
            # keep early doubles only (person blobs, not string-table noise >2e9)
            early = [d for d in dabs if d < 500_000_000]
            lines.append(f"Assan doubles total={len(dabs)} early={len(early)} → {early}")

            for dab in early:
                lines.append("")
                lines.append(f"## Assan dab@{dab}")
                for radius in (2048, 16384, 65536):
                    lines.extend(inventory(mm, dab, radius, CAPA_IDS))
                    if radius < 65536:
                        # inventory already dumps hex only once usefully; skip repeat hex
                        pass

            # Cross-check: for each other player, do ANY of their CAPA ids appear in ±64KB of an early double?
            lines.append("")
            lines.append("## cross-player: CAPA id in ±64KB of early person double?")
            for uid, ids in OTHER.items():
                dabs2 = [d for d in doubles(mm, uid) if d < 500_000_000]
                lines.append(f"uid={uid} early_doubles={dabs2[:8]}")
                any_hit = False
                for dab in dabs2[:6]:
                    lo, hi = max(0, dab - 65536), min(len(mm), dab + 65536)
                    for off in range(lo, hi - 3, 1):
                        # too slow if we scan byte-by-byte for all - use find per id
                        break
                    for cid in ids:
                        nb = struct.pack("<I", cid)
                        start = lo
                        while True:
                            j = mm.find(nb, start, hi)
                            if j < 0:
                                break
                            lines.append(
                                f"  HIT id={cid} dab@{dab} Δ={j - dab:+d}"
                            )
                            any_hit = True
                            start = j + 1
                if not any_hit:
                    lines.append("  (no hits)")

            # Alternative join: CAPA table is dense — measure stride between consecutive records
            lines.append("")
            lines.append("## CAPA table stride sample (Assan neighborhood)")
            magic = b"\x08\x00\x40\x20\x00\x00\x00\x00"
            # find magics near Assan CAPA records
            for center in (473312795, 488012982):
                lo, hi = center - 5000, center + 5000
                offs = []
                start = max(0, lo)
                while len(offs) < 40:
                    j = mm.find(magic, start, min(len(mm), hi))
                    if j < 0:
                        break
                    offs.append(j)
                    start = j + 1
                gaps = [offs[i + 1] - offs[i] for i in range(len(offs) - 1)]
                lines.append(f"around @{center}: n={len(offs)} gaps={gaps[:20]}")
                # parse ca/pa for first few
                for o in offs[:8]:
                    id_at = o + 8
                    rid = struct.unpack_from("<I", mm, id_at)[0]
                    ca = struct.unpack_from("<H", mm, id_at + 13)[0]
                    pa = struct.unpack_from("<H", mm, id_at + 15)[0]
                    lines.append(f"  @{o} id={rid} ca/pa={ca}/{pa}")

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
