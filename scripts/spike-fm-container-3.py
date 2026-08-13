"""Spike #3: walk nested tad. sections and hunt identity strings."""

from __future__ import annotations

import re
import struct
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "tmp" / "fm-spike" / "outer-partial.bin"


def walk_tad(data: bytes, limit: int = 40) -> None:
    # Observed: 03 01 'tad.' ...
    offs = [m.start() for m in re.finditer(rb"tad\.", data)]
    # Only count those preceded by 03 01 within 2 bytes
    real = []
    for off in offs:
        if off >= 2 and data[off - 2 : off] in (b"\x03\x01", b"\x02\x01", b"\x01\x01"):
            real.append(off - 2)
    print(f"tad-like records: {len(real)} (raw tad.={len(offs)})")
    for i, start in enumerate(real[:limit]):
        end = real[i + 1] if i + 1 < len(real) else min(len(data), start + 256)
        chunk = data[start:end]
        print(f"\n[{i}] @ {start} len~{end - start}")
        print("  head:", chunk[:48].hex(" "))
        print("  ascii:", "".join(chr(b) if 32 <= b < 127 else "." for b in chunk[:96]))
        # Parse heuristic: [u8 u8][tag4][???]
        tag = chunk[2:6]
        print("  tag:", tag)
        # Look for embedded cstrings nearby
        cs = []
        j = 6
        while j < min(len(chunk), 200):
            if 32 <= chunk[j] < 127:
                k = j
                while k < len(chunk) and 32 <= chunk[k] < 127:
                    k += 1
                if k - j >= 4:
                    cs.append(chunk[j:k].decode("ascii", "ignore"))
                j = k + 1
            else:
                j += 1
        if cs:
            print("  cstrs:", cs[:12])


def hunt_names(data: bytes) -> None:
    needles = [
        b"Schalke",
        b"KOENIG",
        b"Koenig",
        b"Konig",
        b"Bastian",
        b"Determination",
        b"Professionalism",
        b"Ambition",
        b"Loyalty",
        b"Pressure",
        b"Sportsmanship",
        b"Versatility",
        b"Important Matches",
        b"Dirtiness",
        b"Consistency",
        b"Injury Proneness",
        b"Adaptability",
    ]
    print("\n--- latin1 needles ---")
    for n in needles:
        print(n, data.find(n))

    print("\n--- utf16-le needles ---")
    for n in needles:
        u = n.decode("ascii").encode("utf-16-le")
        print(n, data.find(u))

    # Club-ish: look for "FC Schalke"
    for n in (b"FC Schalke", b"Schalke 04", b"Gelsenkirchen"):
        print("extra", n, data.find(n), data.find(n.decode().encode("utf-16-le")))


def summarize_layout(data: bytes) -> None:
    # First ~25k looked like metadata / patch list; then huge binary blob
    print("\n--- size histogram of tad sections ---")
    offs = []
    for m in re.finditer(rb"tad\.", data):
        if m.start() >= 2 and data[m.start() - 2] in (1, 2, 3):
            offs.append(m.start() - 2)
    sizes = []
    for i, s in enumerate(offs):
        e = offs[i + 1] if i + 1 < len(offs) else len(data)
        sizes.append(e - s)
    for i, (s, sz) in enumerate(zip(offs[:20], sizes[:20])):
        print(f"  tad[{i}] @{s} size={sz}")


def main() -> None:
    data = OUT.read_bytes()
    print("sample bytes:", len(data))
    walk_tad(data)
    summarize_layout(data)
    hunt_names(data)


if __name__ == "__main__":
    main()
