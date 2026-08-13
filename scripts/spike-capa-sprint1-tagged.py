#!/usr/bin/env python3
"""Sprint 1: lock tagged CA/PA records (02 + i16 CA + i16 PA) via mmap.

Uses an existing decompressed bin (no zstd). Filters ascending-run noise,
dumps clean Assan (186,190) contexts, then checks UID / *5 proximity.
"""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint1-tagged.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

ASSAN_UID = 2000188173
CA, PA = 186, 190
TAGGED = b"\x02" + struct.pack("<HH", CA, PA)
PAIR = struct.pack("<HH", CA, PA)
PAIR5 = struct.pack("<HH", CA * 5, PA * 5)
UIDB = struct.pack("<I", ASSAN_UID)


def pick_bin() -> Path:
    for p in CANDIDATE_BINS:
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no ~2GB fmt-*.bin in %TEMP%")


def find_all_mm(mm: mmap.mmap, needle: bytes, limit: int = 8000) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def in_ascending_run(mm: mmap.mmap, off: int) -> bool:
    lo = max(0, off - 16)
    hi = min(len(mm), off + 20)
    able = 0
    for i in range(lo, hi - 1, 2):
        v = struct.unpack_from("<H", mm, i)[0]
        if 1 <= v <= 200:
            able += 1
    return able >= 6


def hexdump(mm: mmap.mmap, off: int, before: int = 32, after: int = 48) -> str:
    lo = max(0, off - before)
    hi = min(len(mm), off + after)
    return f"@{off} rel0={off - lo} " + bytes(mm[lo:hi]).hex(" ")


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines: list[str] = [
        f"# CAPA sprint1 tagged · {bin_path.name} · {bin_path.stat().st_size} bytes",
        "",
    ]
    print(f"mmap {bin_path}…", flush=True)
    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            tagged = find_all_mm(mm, TAGGED)
            pairs = find_all_mm(mm, PAIR, limit=400)
            pair5 = find_all_mm(mm, PAIR5, limit=200)
            uids = find_all_mm(mm, UIDB, limit=400)

            clean = [o for o in tagged if not in_ascending_run(mm, o + 1)]
            noisy = len(tagged) - len(clean)

            lines.append(
                f"tagged 02|CA|PA hits={len(tagged)} clean={len(clean)} noisy_run={noisy}"
            )
            lines.append(
                f"raw pair hits(sampled)={len(pairs)} *5 hits={len(pair5)} "
                f"Assan UID hits={len(uids)}"
            )
            lines.append("")
            lines.append("## clean tagged contexts")
            for o in clean[:40]:
                lines.append(hexdump(mm, o))
                pre = bytes(mm[max(0, o - 24) : o])
                u32s = [
                    struct.unpack_from("<I", pre, i)[0]
                    for i in range(0, len(pre) - 3, 4)
                ]
                lines.append(f"  pre_u32={u32s}")

            lines.append("")
            lines.append("## clean tag ↔ Assan UID nearest Δ")
            for o in clean[:40]:
                if not uids:
                    break
                best = min((abs(u - o), u - o, u) for u in uids)
                lines.append(
                    f"  tag@{o} nearest UID Δ={best[1]:+d} "
                    f"(abs={best[0]}) uid@{best[2]}"
                )

            tag5 = b"\x02" + PAIR5
            tagged5 = [
                o for o in find_all_mm(mm, tag5) if not in_ascending_run(mm, o + 1)
            ]
            lines.append("")
            lines.append(f"## tagged *5 (02|{CA * 5}|{PA * 5}) clean={len(tagged5)}")
            for o in tagged5[:20]:
                lines.append(hexdump(mm, o))
                if uids:
                    best = min((abs(u - o), u - o, u) for u in uids)
                    lines.append(f"  nearest UID Δ={best[1]:+d}")

            lines.append("")
            lines.append("## byte consensus at offsets relative to tag (clean)")
            if clean:
                for rel in range(-24, 16):
                    counts: dict[int, int] = {}
                    for o in clean:
                        i = o + rel
                        if 0 <= i < len(mm):
                            b = mm[i]
                            counts[b] = counts.get(b, 0) + 1
                    top = sorted(counts.items(), key=lambda x: -x[1])[:3]
                    if top and top[0][1] >= max(2, len(clean) // 2):
                        lines.append(
                            f"  rel={rel:+d}: "
                            + ", ".join(f"0x{b:02x}×{c}" for b, c in top)
                            + f" /{len(clean)}"
                        )
        finally:
            mm.close()

    lines.append("")
    lines.append(f"elapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
