#!/usr/bin/env python3
"""Discover Schalke II clubId from managed club alone (no hardcoded II id).

Paths tested:
  A) Catalog name-pair 'Schalke 04 II' → clubId at locked relative offset
  B) Parent clubId 920 co-located with II name / candidate ids
  C) Validate candidate against Ermin II job list / 0b02 team links
"""

from __future__ import annotations

import mmap
import struct
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "squad-ii-clubid-discover.txt"

PARENT = 920  # known from managed-club identity — allowed
JOB_II = 237871  # Ermin — for validation only, not for discovery
II_LIST_ABS = 57023793  # Ermin-containing list from prior sprint


def pick_bin() -> Path:
    for p in sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no bin")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 80) -> list[int]:
    out = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def read_lp32(mm: mmap.mmap, off: int) -> str | None:
    if off + 4 > len(mm):
        return None
    n = struct.unpack_from("<I", mm, off)[0]
    if not (2 <= n <= 64) or off + 4 + n > len(mm):
        return None
    raw = bytes(mm[off + 4 : off + 4 + n])
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not s or not s[0].isalpha():
        return None
    return s


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# II clubId discover · {bin_path.name}", f"parentClubId={PARENT}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # --- Path A: catalog short name → following u32s ---
            short = b"Schalke 04 II"
            hits = find_all(mm, short)
            lines.append(f"## A) '{short.decode()}' hits={len(hits)}")
            candidates: Counter[int] = Counter()
            for h in hits:
                # expect lp32 length prefix immediately before
                if h >= 4 and struct.unpack_from("<I", mm, h - 4)[0] == len(short):
                    # dump u32s after short name (+ optional long already before)
                    after = h + len(short)
                    u32s = [
                        struct.unpack_from("<I", mm, after + i)[0]
                        for i in range(0, 64, 4)
                        if after + i + 4 <= len(mm)
                    ]
                    lines.append(f"  @{h} after_u32={u32s[:12]}")
                    # plausible club ids: 1..1_000_000, not length-like, not ffffffff
                    for rel, v in enumerate(u32s):
                        if 1 <= v <= 1_000_000 and v not in (13, 16, 1, PARENT):
                            candidates[v] += 1
                            lines.append(f"    cand rel=+{rel*4} id={v}")

            # Also try long name
            long = b"FC Schalke 04 II"
            for h in find_all(mm, long):
                if h >= 4 and struct.unpack_from("<I", mm, h - 4)[0] == len(long):
                    after = h + len(long)
                    # often: long, short, then ids
                    short_try = read_lp32(mm, after)
                    lines.append(
                        f"  long@{h} next_lp={short_try!r} "
                        f"u32s={[struct.unpack_from('<I', mm, after + i)[0] for i in range(0, 48, 4)]}"
                    )

            lines.append(f"  candidate frequency: {candidates.most_common(15)}")

            # --- Path A2: learn offset from several German II catalog rows ---
            lines.append("")
            lines.append("## A2) cross-club II catalog layout (early <20MB)")
            ii_names = [
                b"Schalke 04 II",
                b"Kaiserslautern II",
                b"Eintracht Frankfurt II",
                b"Hansa Rostock II",
                b"Bayer Leverkusen II",
                b"Karlsruhe II",
                b"Borussia Dortmund II",
                b"Bayern Munich II",
            ]
            # For each, if lp-prefixed in early file, collect (rel→value) histogram
            rel_vals: dict[int, list[int]] = {}
            for name in ii_names:
                for h in find_all(mm, name, limit=5):
                    if h > 20_000_000:
                        continue
                    if h < 4 or struct.unpack_from("<I", mm, h - 4)[0] != len(name):
                        continue
                    after = h + len(name)
                    lines.append(f"  {name.decode()!r} @{h}")
                    for rel in range(0, 48, 4):
                        v = struct.unpack_from("<I", mm, after + rel)[0]
                        rel_vals.setdefault(rel, []).append(v)
                        if 1 <= v <= 500_000:
                            lines.append(f"    +{rel}: {v}")

            # --- Path B: parent 920 near II name ---
            lines.append("")
            lines.append("## B) parent clubId 920 within ±256 of II names")
            pb = struct.pack("<I", PARENT)
            for h in hits[:20]:
                lo, hi = max(0, h - 256), min(len(mm), h + 256)
                region = bytes(mm[lo:hi])
                pos = 0
                found = []
                while True:
                    j = region.find(pb, pos)
                    if j < 0:
                        break
                    found.append(j - (h - lo))
                    pos = j + 1
                if found:
                    lines.append(f"  name@{h}: 920 at rels={found}")

            # --- Path B2: typed refs 01 03 02 <id> near II name ---
            lines.append("")
            lines.append("## B2) 01 03 02 <u32> near early II name (club-ref motif)")
            for h in hits:
                if h > 20_000_000:
                    continue
                lo, hi = max(0, h - 128), min(len(mm), h + 192)
                start = lo
                while True:
                    j = mm.find(b"\x01\x03\x02", start, hi)
                    if j < 0:
                        break
                    cid = struct.unpack_from("<I", mm, j + 3)[0]
                    lines.append(f"  @{j} rel={j - h:+d} id={cid}")
                    start = j + 1

            # --- Path C: validate candidates vs Ermin list neighbourhood ---
            lines.append("")
            lines.append("## C) candidate ids near Ermin II job-list")
            lo, hi = II_LIST_ABS - 2000, II_LIST_ABS + 200
            for cid, n in candidates.most_common(20):
                nb = struct.pack("<I", cid)
                j = bytes(mm[lo:hi]).find(nb)
                if j >= 0:
                    lines.append(
                        f"  id={cid} FOUND near II list Δ={lo + j - II_LIST_ABS:+d} "
                        f"(freq={n})"
                    )

            # Also search 0b02 <tid_or_club> 02 <ermin uid>
            ermin_uid = 2002138129
            lines.append("")
            lines.append("## C2) 0b02 <id> 02 <ErminUid> — ids linked to Ermin")
            uidb = struct.pack("<I", ermin_uid)
            for off in find_all(mm, b"\x0b\x02", limit=5000):
                if off + 11 > len(mm):
                    continue
                if mm[off + 6] != 0x02:
                    continue
                if bytes(mm[off + 7 : off + 11]) != uidb:
                    continue
                ident = struct.unpack_from("<I", mm, off + 2)[0]
                lines.append(f"  0b02 id={ident} @{off}")

            # --- Path D: from parent short name, construct II and resolve ---
            lines.append("")
            lines.append("## D) discovery recipe from parent short name alone")
            parent_short = "Schalke 04"
            derived = f"{parent_short} II"
            dhits = find_all(mm, derived.encode("utf-8"))
            lines.append(f"  derived name {derived!r} hits={len(dhits)}")
            # Prefer early catalog hit with lp prefix + read first plausible id after name pair
            for h in dhits:
                if h > 30_000_000:
                    continue
                if h < 4 or struct.unpack_from("<I", mm, h - 4)[0] != len(derived):
                    continue
                # Walk: after short may be padding then ids — OR long name came first
                # Check if previous lp is long name containing short
                prev = None
                for back in range(8, 80):
                    po = h - 4 - back
                    if po < 0:
                        break
                    prev = read_lp32(mm, po)
                    if prev and (derived in prev or prev.endswith(" II")):
                        break
                    prev = None
                after = h + len(derived)
                # skip ff padding / small fields to first id in 100..200000
                pick = None
                for rel in range(0, 80, 4):
                    v = struct.unpack_from("<I", mm, after + rel)[0]
                    if 100 <= v <= 200_000 and v != PARENT:
                        pick = (rel, v)
                        break
                lines.append(
                    f"  catalog@{h} prevLong={prev!r} firstPlausibleId={pick}"
                )
                lines.append(
                    "  ctx: " + bytes(mm[h - 8 : h + 48]).hex(" ")
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
