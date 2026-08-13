#!/usr/bin/env python3
"""Sprint 9: dump structure around CA/PA u16 pairs found in person lookbacks."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint9-lookback-struct.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

PLAYERS = [
    ("Bandeira", 2002234366, 184, 184, -17762),
    ("Kizza", 2002185604, 165, 165, -10421),
    ("Assan", 2000188173, 186, 190, None),  # hunt
]


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


def early_dab(mm: mmap.mmap, uid: int) -> int | None:
    nb = struct.pack("<I", uid)
    for u in find_all(mm, nb, limit=300):
        if u > 500_000_000:
            continue
        if mm.find(nb, u + 4, min(len(mm), u + 48)) > 0:
            return u
    return None


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint9 lookback struct · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hits = []
            for name, uid, ca, pa, hint in PLAYERS:
                dab = early_dab(mm, uid)
                lines.append(f"## {name} uid={uid} dab={dab} truth={ca}/{pa}")
                if dab is None:
                    lines.append("  NO early dab")
                    continue
                pair = struct.pack("<HH", ca, pa)
                lo = max(0, dab - 48_000)
                hi = min(len(mm), dab + 2_000)
                blob = bytes(mm[lo:hi])
                rels = []
                start = 0
                while True:
                    j = blob.find(pair, start)
                    if j < 0:
                        break
                    rels.append(j - (dab - lo))
                    start = j + 1
                lines.append(f"  pair rels in ±48KB/ +2KB: {rels}")
                use = hint if hint is not None else (rels[0] if rels else None)
                if use is None:
                    lines.append("  no pair")
                    continue
                abs_off = dab + use
                # wide dump
                ctx = bytes(mm[abs_off - 64 : abs_off + 96])
                lines.append(f"  using rel={use:+d} abs={abs_off}")
                lines.append(f"  ctx-64..+96: {ctx.hex(' ')}")
                # decode fields around pair
                for back in range(1, 48):
                    pre = bytes(mm[abs_off - back : abs_off])
                    if pre.endswith(b"\x00\x40\x20\x00\x00\x00\x00") or pre[
                        -7:
                    ] == b"\x00\x40\x20\x00\x00\x00\x00":
                        lines.append(f"  CAPA magic ends {back} bytes before pair")
                    if len(pre) >= 1 and pre[-1] == 0x02:
                        # possible tag immediately before CA
                        lines.append(f"  byte before CA = 0x02 (back={back})")
                        break
                # bytes immediately before pair
                pre16 = bytes(mm[abs_off - 32 : abs_off])
                post32 = bytes(mm[abs_off + 4 : abs_off + 36])
                lines.append(f"  pre32: {pre16.hex(' ')}")
                lines.append(f"  post32: {post32.hex(' ')}")
                # u32s before
                u32s = [
                    struct.unpack_from("<I", mm, abs_off - 32 + i)[0]
                    for i in range(0, 32, 4)
                ]
                lines.append(f"  pre_u32: {u32s}")
                # distance to dab
                lines.append(f"  gap_to_dab={dab - abs_off}")
                hits.append((name, uid, dab, abs_off, use, ca, pa))

                # Is this inside a CAPA-family record? search magic backward up to 64
                magic = b"\x00\x40\x20\x00\x00\x00\x00"
                back_region = bytes(mm[max(0, abs_off - 64) : abs_off])
                mi = back_region.rfind(magic)
                if mi >= 0:
                    magic_abs = abs_off - 64 + mi
                    id_at = magic_abs + 7
                    rid = struct.unpack_from("<I", mm, id_at)[0]
                    lines.append(
                        f"  YES CAPA-family magic @{magic_abs} id={rid} "
                        f"pair_rel_to_magic={abs_off - magic_abs}"
                    )
                else:
                    lines.append("  no CAPA magic within -64 of pair")
                    # search further back 2KB
                    back2 = bytes(mm[max(0, abs_off - 2048) : abs_off])
                    mi2 = back2.rfind(magic)
                    if mi2 >= 0:
                        magic_abs = abs_off - len(back2) + mi2
                        rid = struct.unpack_from("<I", mm, magic_abs + 7)[0]
                        lines.append(
                            f"  CAPA magic within -2KB @{magic_abs} id={rid} "
                            f"Δ={abs_off - magic_abs}"
                        )

            # Compare shared pre-bytes across hits
            lines.append("")
            lines.append("## shared pre-byte consensus across players")
            if len(hits) >= 2:
                for rel in range(-40, 20):
                    vals = []
                    for name, uid, dab, abs_off, use, ca, pa in hits:
                        vals.append(mm[abs_off + rel])
                    if len(set(vals)) == 1:
                        lines.append(
                            f"  rel={rel:+d}: 0x{vals[0]:02x} shared by {len(hits)}"
                        )

            # Extraction rule candidate: from dab, rfind pair? No - need structure.
            # Instead: from dab lookback, find CAPA magic then read ca/pa at fixed +20
            lines.append("")
            lines.append("## extraction test: CAPA magics in lookback → ca/pa")
            for name, uid, dab, abs_off, use, ca, pa in hits:
                lo = max(0, dab - 48_000)
                region = bytes(mm[lo:dab])
                magic = b"\x00\x40\x20\x00\x00\x00\x00"
                found = []
                start = 0
                while len(found) < 30:
                    j = region.find(magic, start)
                    if j < 0:
                        break
                    abs_m = lo + j
                    id_at = abs_m + 7
                    rca = struct.unpack_from("<H", mm, id_at + 13)[0]
                    rpa = struct.unpack_from("<H", mm, id_at + 15)[0]
                    rid = struct.unpack_from("<I", mm, id_at)[0]
                    found.append((abs_m - dab, rid, rca, rpa))
                    start = j + 1
                match = [x for x in found if x[2] == ca and x[3] == pa]
                lines.append(
                    f"{name}: magics_in_lookback={len(found)} "
                    f"matching_truth={len(match)} → {match[:5]}"
                )
                # nearest magic to dab (any)
                if found:
                    nearest = max(found, key=lambda x: x[0])  # least negative
                    lines.append(f"  nearest-to-dab magic: {nearest}")

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
