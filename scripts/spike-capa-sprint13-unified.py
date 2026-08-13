#!/usr/bin/env python3
"""Sprint 13: unified CAPA core = ptr×2 | 02 | x y z | CA PA; nearest-to-dab."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint13-unified.txt"

BIN = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

LOOKBACK = 48_000
TRUTH = [
    ("Assan", 2000188173, 186, 190),
    ("Kizza", 2002185604, 165, 165),
    ("Bandeira", 2002234366, 184, 184),
    ("Muller", 2002266341, None, None),
    ("Seimen", 2000175080, None, None),
]


def pick() -> Path:
    for p in BIN:
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no bin")


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


def early_dab(mm: mmap.mmap, uid: int) -> list[int]:
    nb = struct.pack("<I", uid)
    out = []
    for u in find_all(mm, nb, limit=300):
        if u > 800_000_000:
            continue
        if mm.find(nb, u + 4, min(len(mm), u + 48)) > 0:
            out.append(u)
    return out


def scan_cores(mm: mmap.mmap, lo: int, hi: int) -> list[dict]:
    """Find twin-ptr CAPA cores in [lo, hi)."""
    out = []
    # stride 1 — ok for 48KB
    for off in range(lo, hi - 19):
        p1 = struct.unpack_from("<I", mm, off)[0]
        p2 = struct.unpack_from("<I", mm, off + 4)[0]
        if p1 != p2 or p1 < 0x01000000:
            continue
        if mm[off + 8] != 0x02:
            continue
        x, y, z, ca, pa = struct.unpack_from("<HHHHH", mm, off + 9)
        if not (1 <= ca <= 200 and 1 <= pa <= 200):
            continue
        # prefer ptrs that look like FM object ids (high byte often 0x77)
        high = (p1 >> 24) & 0xFF
        id_before = struct.unpack_from("<I", mm, off - 4)[0] if off >= 4 else None
        out.append(
            {
                "at": off,
                "ptr": p1,
                "high": high,
                "id": id_before,
                "ca": ca,
                "pa": pa,
                "xyz": (x, y, z),
            }
        )
    return out


def main() -> int:
    path = pick()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint13 unified · {path.name}", ""]
    print(f"mmap {path.name}…", flush=True)

    with path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for name, uid, tca, tpa in TRUTH:
                dabs = early_dab(mm, uid)
                lines.append(f"## {name} uid={uid} truth={tca}/{tpa} dabs={dabs}")
                best_overall = None
                for dab in dabs:
                    lo = max(0, dab - LOOKBACK)
                    cores = scan_cores(mm, lo, dab)
                    # Prefer high=0x77 twin ptrs (seen in all three truths)
                    ranked = sorted(
                        cores,
                        key=lambda c: (
                            0 if c["high"] == 0x77 else 1,
                            -(c["at"]),  # nearest dab
                        ),
                    )
                    lines.append(f"  dab@{dab}: cores={len(cores)}")
                    shown = 0
                    for c in ranked:
                        if shown >= 8:
                            break
                        # only show 0x77 or truth match
                        is_truth = (
                            tca is not None and c["ca"] == tca and c["pa"] == tpa
                        )
                        if c["high"] != 0x77 and not is_truth:
                            continue
                        mark = " <<TRUTH" if is_truth else ""
                        lines.append(
                            f"    Δ={c['at'] - dab:+d} ca/pa={c['ca']}/{c['pa']} "
                            f"id={c['id']} ptr={c['ptr']:#x} hi={c['high']:02x}{mark}"
                        )
                        shown += 1
                        if best_overall is None or (
                            is_truth
                            and (
                                best_overall.get("truth") is not True
                                or c["at"] > best_overall["at"]
                            )
                        ):
                            best_overall = {**c, "truth": is_truth, "dab": dab}
                        elif best_overall.get("truth") is not True and c["high"] == 0x77:
                            if c["at"] > best_overall["at"]:
                                best_overall = {
                                    **c,
                                    "truth": is_truth,
                                    "dab": dab,
                                }

                    # EXTRACT rule A: nearest hi=0x77 core
                    hi77 = [c for c in cores if c["high"] == 0x77]
                    if hi77:
                        nearest = max(hi77, key=lambda c: c["at"])
                        ok = (
                            tca is None
                            or (nearest["ca"] == tca and nearest["pa"] == tpa)
                        )
                        lines.append(
                            f"  RULE nearest-hi77: ca/pa={nearest['ca']}/{nearest['pa']} "
                            f"gap={dab - nearest['at']} ok={ok}"
                        )

                if best_overall:
                    lines.append(
                        f"  BEST: ca/pa={best_overall['ca']}/{best_overall['pa']} "
                        f"truth={best_overall.get('truth')} dab={best_overall['dab']}"
                    )

        finally:
            mm.close()

    lines.append(f"\nelapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
