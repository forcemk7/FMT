#!/usr/bin/env python3
"""Sprint 8: encodings of Bandeira CA/PA=184 inside attr-card lookback."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint8-bandeira-lookback.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

UID = 2002234366
VAL = 184
LOOKBACK = 20_000
LOOKAHEAD = 2_000

# Bandeira mental fingerprint from fixture (likely in 69-byte card)
MENTAL_FP = bytes([9, 17, 13, 13, 18, 16, 16, 13, 14, 11, 17, 12, 15, 15])


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


def best_doubles(mm: mmap.mmap, uid: int) -> list[int]:
    nb = struct.pack("<I", uid)
    hits = find_all(mm, nb, limit=200)
    dabs = []
    for u in hits:
        if u > 500_000_000:
            continue
        nxt = mm.find(nb, u + 4, min(len(mm), u + 48))
        if nxt > 0:
            dabs.append(u)
    return dabs


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint8 Bandeira lookback · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            dabs = best_doubles(mm, UID)
            lines.append(f"early doubles={dabs}")

            # locate mental fingerprint (attr card)
            fp_hits = find_all(mm, MENTAL_FP, limit=20)
            lines.append(f"mental fp hits={len(fp_hits)} → {fp_hits[:10]}")
            for fh in fp_hits[:5]:
                best = min((abs(d - fh), d - fh, d) for d in dabs) if dabs else None
                lines.append(
                    f"  fp@{fh} nearest dab Δ={best[1] if best else 'n/a'} "
                    f"abs={best[0] if best else 'n/a'}"
                )

            encodings = {
                "u16": struct.pack("<H", VAL),
                "i16": struct.pack("<h", VAL),
                "u32": struct.pack("<I", VAL),
                "u16x2": struct.pack("<HH", VAL, VAL),
                "u16x5": struct.pack("<HH", VAL * 5, VAL * 5),
                "f32": struct.pack("<f", float(VAL)),
                "u8x2": bytes([VAL, VAL]),
            }

            for dab in dabs[:3]:
                lo = max(0, dab - LOOKBACK)
                hi = min(len(mm), dab + LOOKAHEAD)
                blob = bytes(mm[lo:hi])
                lines.append("")
                lines.append(f"## dab@{dab} window [{lo}:{hi}]")
                for name, needle in encodings.items():
                    pos = []
                    start = 0
                    while len(pos) < 40:
                        j = blob.find(needle, start)
                        if j < 0:
                            break
                        pos.append(j - (dab - lo))  # rel to dab
                        start = j + 1
                    lines.append(f"  {name}: n={len(pos)} rels={pos[:25]}")
                    for rel in pos[:6]:
                        abs_off = dab + rel
                        ctx = bytes(mm[abs_off - 8 : abs_off + 16])
                        lines.append(f"    rel={rel:+d} ctx={ctx.hex(' ')}")

                # If mental fp in window, dump ±64 around it and mark 184s
                for fh in fp_hits:
                    if lo <= fh < hi:
                        lines.append(f"  mental fp in window @{fh} Δ={fh - dab:+d}")
                        lines.append(
                            "    "
                            + bytes(mm[fh - 32 : fh + 48]).hex(" ")
                        )

            # Cross: Assan mental unknown — instead check Kizza 165 near his dab
            lines.append("")
            lines.append("## Kizza 165 encodings near early doubles")
            k_uid = 2002185604
            k_dabs = best_doubles(mm, k_uid)
            lines.append(f"Kizza early doubles={k_dabs}")
            for dab in k_dabs[:2]:
                lo = max(0, dab - LOOKBACK)
                hi = min(len(mm), dab + LOOKAHEAD)
                blob = bytes(mm[lo:hi])
                for name, needle in {
                    "u16x2_165": struct.pack("<HH", 165, 165),
                    "u16_165": struct.pack("<H", 165),
                    "u32_165": struct.pack("<I", 165),
                    "f32_165": struct.pack("<f", 165.0),
                    "u16x5": struct.pack("<HH", 825, 825),
                }.items():
                    pos = []
                    start = 0
                    while len(pos) < 20:
                        j = blob.find(needle, start)
                        if j < 0:
                            break
                        pos.append(j - (dab - lo))
                        start = j + 1
                    lines.append(f"  dab@{dab} {name}: {pos[:15]}")

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
