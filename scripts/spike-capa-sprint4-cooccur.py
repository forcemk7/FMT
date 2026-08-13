#!/usr/bin/env python3
"""Sprint 4: find any window where Assan UID co-occurs with CAPA record id."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint4-cooccur.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

ASSAN_UID = 2000188173
IDS = [653714, 672906]
WINDOWS = [256, 1024, 4096, 16384, 65536, 262144]


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


def dump(mm: mmap.mmap, a: int, b: int, pad: int = 24) -> str:
    lo = max(0, min(a, b) - pad)
    hi = min(len(mm), max(a, b) + pad + 4)
    return f"[{lo}:{hi}] " + bytes(mm[lo:hi]).hex(" ")


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint4 co-occur · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            uids = find_all(mm, struct.pack("<I", ASSAN_UID), limit=400)
            lines.append(f"Assan UID hits={len(uids)}")

            for rid in IDS:
                id_hits = find_all(mm, struct.pack("<I", rid), limit=100)
                lines.append("")
                lines.append(f"## id={rid} hits={len(id_hits)}")
                for w in WINDOWS:
                    pairs = []
                    for ih in id_hits:
                        for u in uids:
                            d = abs(ih - u)
                            if d <= w:
                                pairs.append((d, ih - u, ih, u))
                    pairs.sort()
                    # dedupe similar
                    uniq = []
                    seen = set()
                    for p in pairs:
                        key = (p[2], p[3])
                        if key in seen:
                            continue
                        seen.add(key)
                        uniq.append(p)
                    lines.append(f"  within ±{w}: {len(uniq)} unique (id,uid) pairs")
                    for d, rel, ih, u in uniq[:6]:
                        lines.append(f"    Δ={rel:+d} abs={d} id@{ih} uid@{u}")
                        if d <= 4096:
                            lines.append("      " + dump(mm, ih, u))

            # Bridge dump: closest known pair id@1021094766 ↔ uid@1021299880
            lines.append("")
            lines.append("## bridge dump id@1021094766 → uid@1021299880")
            a, b = 1021094766, 1021299880
            # sample every 8KB with annotations if id/uid present
            step = 4096
            for off in range(a - 64, b + 64, step):
                chunk = bytes(mm[off : off + 64])
                mark = ""
                if struct.pack("<I", 653714) in chunk:
                    mark += " [ID]"
                if struct.pack("<I", ASSAN_UID) in chunk:
                    mark += " [UID]"
                lines.append(f"  @{off}{mark} " + chunk.hex(" "))

            # Also: does Assan name UTF-16 appear near CAPA ids?
            lines.append("")
            lines.append("## Assan name UTF-16 near CAPA ids (±1MB)")
            # "Assan" in utf-16le
            name = "Assan".encode("utf-16le")
            name_hits = find_all(mm, name, limit=50)
            lines.append(f"name 'Assan' utf16 hits={len(name_hits)}")
            for rid in IDS:
                id_hits = find_all(mm, struct.pack("<I", rid), limit=100)
                best = None
                for nh in name_hits:
                    for ih in id_hits:
                        d = abs(nh - ih)
                        if best is None or d < best[0]:
                            best = (d, nh - ih, nh, ih)
                if best:
                    lines.append(
                        f"  id={rid} nearest name Δ={best[1]:+d} abs={best[0]} "
                        f"name@{best[2]} id@{best[3]}"
                    )

            # Structural: parse repeating rows at id@1021094766
            lines.append("")
            lines.append("## parse repeating rows around id@1021094766")
            base = 1021094766
            # look backward for row start pattern 59 00 f8 07 or 80 00 00 02
            region = bytes(mm[base - 128 : base + 256])
            lines.append("  region: " + region.hex(" "))
            # try stride detection: find all 653714 in ±2KB and gaps
            local_ids = []
            needle = struct.pack("<I", 653714)
            lo = base - 2048
            hi = base + 2048
            start = lo
            while True:
                j = mm.find(needle, start, hi)
                if j < 0:
                    break
                local_ids.append(j)
                start = j + 1
            lines.append(f"  id in ±2KB: {local_ids}")
            if len(local_ids) >= 2:
                gaps = [local_ids[i + 1] - local_ids[i] for i in range(len(local_ids) - 1)]
                lines.append(f"  gaps={gaps}")

            # At the closest UID, dump ±128 and search for any u32 in CAPA id range 650000-675000
            lines.append("")
            lines.append("## u32s near Assan UID@1021299880 that look like CAPA ids")
            u = 1021299880
            win = bytes(mm[u - 256 : u + 256])
            cands = []
            for i in range(0, len(win) - 3):
                v = struct.unpack_from("<I", win, i)[0]
                if 500000 <= v <= 800000:
                    cands.append((i - 256, v))
            lines.append(f"  candidates={cands[:40]}")
            lines.append("  ctx: " + win.hex(" "))

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
