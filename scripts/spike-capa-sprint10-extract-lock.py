#!/usr/bin/env python3
"""Sprint 10: lock player CAPA extract via 08 02 40 30 blocks in dab lookback."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint10-extract-lock.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

MAGIC = b"\x08\x02\x40\x30\x04\x00\x00\x00"
LOOKBACK = 48_000

# Truth may be stale vs this 22.11 bin; still useful as signal.
TRUTH = [
    ("Assan", 2000188173, 186, 190),
    ("Kizza", 2002185604, 165, 165),
    ("Bandeira", 2002234366, 184, 184),
    ("Muller", 2002266341, None, None),  # FT player, discover CA/PA
    ("Seimen", 2000175080, None, None),
]

# From prior RE
INTERNAL = {
    2000175080: 0x0001BB6D,  # Seimen
    2002234366: 0x0005191C,  # Bandeira
    2002266341: 0x00059603,  # Muller
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


def early_dabs(mm: mmap.mmap, uid: int) -> list[int]:
    nb = struct.pack("<I", uid)
    out = []
    for u in find_all(mm, nb, limit=300):
        if u > 500_000_000:
            continue
        if mm.find(nb, u + 4, min(len(mm), u + 48)) > 0:
            out.append(u)
    return out


def parse_block(mm: mmap.mmap, magic_at: int) -> dict | None:
    # MAGIC(8) + id(4) + ptr(4)+ptr(4) + tag(1) + x,y,z(6) + ca,pa(4) = 31
    if magic_at + 31 > len(mm):
        return None
    if bytes(mm[magic_at : magic_at + 8]) != MAGIC:
        return None
    rid = struct.unpack_from("<I", mm, magic_at + 8)[0]
    p1 = struct.unpack_from("<I", mm, magic_at + 12)[0]
    p2 = struct.unpack_from("<I", mm, magic_at + 16)[0]
    tag = mm[magic_at + 20]
    x, y, z, ca, pa = struct.unpack_from("<HHHHH", mm, magic_at + 21)
    return {
        "at": magic_at,
        "id": rid,
        "ptr": p1,
        "ptr_ok": p1 == p2,
        "tag": tag,
        "x": x,
        "y": y,
        "z": z,
        "ca": ca,
        "pa": pa,
    }


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint10 extract lock · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            lines.append(f"layout: {MAGIC.hex(' ')} | id | ptr×2 | tag | x y z | CA PA")
            lines.append("")

            for name, uid, tca, tpa in TRUTH:
                dabs = early_dabs(mm, uid)
                lines.append(f"## {name} uid={uid} truth={tca}/{tpa} dabs={dabs}")
                for dab in dabs:
                    lo = max(0, dab - LOOKBACK)
                    region = mm[lo:dab]
                    blocks = []
                    start = 0
                    while True:
                        j = region.find(MAGIC, start)
                        if j < 0:
                            break
                        b = parse_block(mm, lo + j)
                        if b and b["ptr_ok"] and b["tag"] == 0x02:
                            if 1 <= b["ca"] <= 200 and 1 <= b["pa"] <= 200:
                                blocks.append(b)
                        start = j + 1
                    lines.append(f"  dab@{dab}: player-CAPA blocks={len(blocks)}")
                    for b in blocks:
                        mark = ""
                        if tca is not None and b["ca"] == tca and b["pa"] == tpa:
                            mark = " <<TRUTH"
                        intl = INTERNAL.get(uid)
                        if intl is not None and (
                            b["id"] == intl or b["id"] == intl - 1 or b["id"] == intl + 1
                        ):
                            mark += f" <<INTERNAL~{intl:#x}"
                        lines.append(
                            f"    Δ={b['at'] - dab:+d} id={b['id']}({b['id']:#x}) "
                            f"ca/pa={b['ca']}/{b['pa']} xyz={b['x']},{b['y']},{b['z']}"
                            f"{mark}"
                        )
                    # Prefer nearest-to-dab block as extract candidate
                    if blocks:
                        nearest = max(blocks, key=lambda b: b["at"])
                        lines.append(
                            f"  EXTRACT? nearest ca/pa={nearest['ca']}/{nearest['pa']} "
                            f"id={nearest['id']:#x} gap={dab - nearest['at']}"
                        )

            # Global sanity: how many such blocks exist?
            lines.append("")
            lines.append("## global MAGIC count (capped)")
            n = 0
            start = 0
            while n < 20000:
                j = mm.find(MAGIC, start)
                if j < 0:
                    break
                n += 1
                start = j + 1
            lines.append(f"magic hits (cap 20k)={n}")

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
