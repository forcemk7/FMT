#!/usr/bin/env python3
"""T004B v3: confirm clubIds 916/2238/2249 + ASCII Millwood/Paderborn hunt."""

from __future__ import annotations

import mmap
import struct
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
OUT = ROOT / "tmp" / "fm-spike" / "spike-loan-ii-u19-v3.txt"


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 100) -> list[int]:
    out, pos = [], 0
    while len(out) < limit:
        j = mm.find(needle, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    return out


def scan_names_around(mm: mmap.mmap, club: int, needles: list[bytes]) -> dict[str, int]:
    """Count needle hits within ±512 of club×2 occurrences."""
    counts: Counter[str] = Counter()
    pair = struct.pack("<I", club) * 2
    for off in find_all(mm, pair, limit=60):
        window = mm[max(0, off - 512) : off + 512]
        for n in needles:
            if n in window:
                counts[n.decode("utf-8", errors="replace")] += 1
    # also single clubId
    single = struct.pack("<I", club)
    for off in find_all(mm, single, limit=80):
        window = mm[max(0, off - 256) : off + 256]
        for n in needles:
            label = n.decode("utf-8", errors="replace")
            if n in window:
                counts[label + "/single"] += 1
    return dict(counts)


def main() -> int:
    needles = [
        b"Augsburg",
        b"FC Augsburg",
        "Köln".encode("utf-8"),
        b"Koln",
        b"1. FC K",
        b"Paderborn",
        b"Essen",
        b"Rot-Weiss",
        b"Rot-Wei",
        b"Legia",
        b"Frankfurt",
        b"Oberhausen",
        b"Mainz",
    ]
    # utf-16 variants
    needles += [
        "Augsburg".encode("utf-16-le"),
        "Köln".encode("utf-16-le"),
        "Paderborn".encode("utf-16-le"),
        "Essen".encode("utf-16-le"),
        "Legia".encode("utf-16-le"),
    ]

    lines = ["# T004B spike-loan-ii-u19-v3", ""]
    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for cid, label in [
                (2238, "Manole cand Augsburg"),
                (916, "Braescu cand Koln"),
                (2249, "Ozturk cand Essen"),
                (1456, "Sipho Legia control"),
                (912, "Vlad cand Frankfurt"),
            ]:
                hits = scan_names_around(mm, cid, needles)
                lines.append(f"## club {cid} ({label})")
                lines.append(f"  nameHits={hits}")
                lines.append("")

            # Millwood: ASCII Paderborn near job/uid
            job, uid = 538884, 2002422274
            lines.append("## Millwood ASCII/UTF16 Paderborn proximity")
            for label, needle in [
                ("ascii", b"Paderborn"),
                ("utf16", "Paderborn".encode("utf-16-le")),
                ("SC Paderborn ascii", b"SC Paderborn"),
            ]:
                offs = find_all(mm, needle, limit=50)
                lines.append(f"  {label} hits={len(offs)}")
                # any near job?
                jb = struct.pack("<I", job)
                job_offs = find_all(mm, jb, limit=200)
                near = 0
                for jo in job_offs:
                    for no in offs:
                        if abs(jo - no) < 8192:
                            near += 1
                            break
                lines.append(f"    jobSitesWithNameIn8k={near}/{len(job_offs)}")
                # club dups near name
                clubs: Counter[int] = Counter()
                for no in offs[:40]:
                    for rel in range(-128, 256, 4):
                        abs_off = no + rel
                        if abs_off < 0 or abs_off + 8 > len(mm):
                            continue
                        a = struct.unpack_from("<I", mm, abs_off)[0]
                        b = struct.unpack_from("<I", mm, abs_off + 4)[0]
                        if a == b and 50 <= a <= 100_000:
                            clubs[a] += 1
                lines.append(f"    clubsNearName={clubs.most_common(8)}")

            # Does Millwood job ever sit back from ANY 64ff2x with pre4=0 within back 8..80?
            lines.append("")
            lines.append("## Millwood: any 64ff2x with job in back 8..80 + pre4=0")
            jb = struct.pack("<I", job)
            found = []
            for kind in range(0x20, 0x30):
                motif = bytes((0x64, 0xFF, kind))
                pos = 0
                while True:
                    j = mm.find(motif, pos)
                    if j < 0:
                        break
                    if j >= 4 and mm[j - 4 : j] == b"\x00\x00\x00\x00":
                        for back in range(8, 81):
                            start = j - back
                            if start >= 0 and struct.unpack_from("<I", mm, start)[0] == job:
                                a = struct.unpack_from("<I", mm, j + 21)[0]
                                b = struct.unpack_from("<I", mm, j + 25)[0]
                                found.append(
                                    {
                                        "kind": kind,
                                        "motifAt": j,
                                        "back": back,
                                        "dup21": a if a == b else None,
                                    }
                                )
                    pos = j + 1
            lines.append(f"  found={found}")

            # Same for Ozturk at back=49 detail
            lines.append("")
            lines.append("## Ozturk object detail @56472283")
            ozt = 56472283
            lines.append("  " + mm[ozt - 16 : ozt + 48].hex())
            lines.append(
                f"  loan@+21={struct.unpack_from('<I', mm, ozt+21)[0]} "
                f"dup={struct.unpack_from('<I', mm, ozt+21)[0]==struct.unpack_from('<I', mm, ozt+25)[0]}"
            )
        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
