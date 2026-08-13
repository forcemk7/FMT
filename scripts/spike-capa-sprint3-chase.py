#!/usr/bin/env python3
"""Sprint 3: chase Assan CAPA record id/ptr into person-linked regions."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint3-chase.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

ASSAN_UID = 2000188173
# From sprint2
RECS = [
    {"id": 653714, "ptr": 2002536756, "ca": 186, "pa": 190, "rec_at": 473312795},
    {"id": 672906, "ptr": 2002555948, "ca": 186, "pa": 190, "rec_at": 488012982},
]


def pick_bin() -> Path:
    for p in CANDIDATE_BINS:
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no ~2GB fmt-*.bin")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 200) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def dump(mm: mmap.mmap, off: int, before: int = 48, after: int = 64) -> str:
    lo = max(0, off - before)
    hi = min(len(mm), off + after)
    return f"@{off} " + bytes(mm[lo:hi]).hex(" ")


def nearest(targets: list[int], anchors: list[int], cap: int = 8):
    out = []
    for t in targets:
        if not anchors:
            break
        a = min(anchors, key=lambda x: abs(x - t))
        out.append((abs(t - a), t - a, t, a))
    out.sort()
    return out[:cap]


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint3 chase · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            uids = find_all(mm, struct.pack("<I", ASSAN_UID), limit=400)
            lines.append(f"Assan UID hits={len(uids)}")

            # person doubles: UID within 48 bytes of itself again
            doubles = []
            for u in uids:
                nxt = mm.find(struct.pack("<I", ASSAN_UID), u + 4, min(len(mm), u + 48))
                if nxt > 0:
                    doubles.append(u)
            lines.append(f"Assan person-double-ish hits={len(doubles)}")
            for d in doubles[:12]:
                lines.append(f"  dab@{d} " + dump(mm, d, 16, 32))

            for rec in RECS:
                lines.append("")
                lines.append(
                    f"## rec id={rec['id']} ptr={rec['ptr']} "
                    f"CA/PA={rec['ca']}/{rec['pa']} stored@{rec['rec_at']}"
                )
                id_hits = find_all(mm, struct.pack("<I", rec["id"]), limit=80)
                ptr_hits = find_all(mm, struct.pack("<I", rec["ptr"]), limit=80)
                lines.append(f"id occurrences={len(id_hits)} ptr occurrences={len(ptr_hits)}")

                lines.append("### id ↔ Assan UID nearest")
                for abs_d, rel, t, a in nearest(id_hits, uids):
                    lines.append(f"  id@{t} uid@{a} Δ={rel:+d} abs={abs_d}")
                    if abs_d <= 512_000:
                        lines.append("    " + dump(mm, t, 32, 48))

                lines.append("### ptr ↔ Assan UID nearest")
                for abs_d, rel, t, a in nearest(ptr_hits, uids):
                    lines.append(f"  ptr@{t} uid@{a} Δ={rel:+d} abs={abs_d}")
                    if abs_d <= 512_000:
                        lines.append("    " + dump(mm, t, 32, 48))

                lines.append("### id ↔ Assan double nearest")
                for abs_d, rel, t, a in nearest(id_hits, doubles or uids):
                    lines.append(f"  id@{t} dab@{a} Δ={rel:+d} abs={abs_d}")

                lines.append("### ptr ↔ Assan double nearest")
                for abs_d, rel, t, a in nearest(ptr_hits, doubles or uids):
                    lines.append(f"  ptr@{t} dab@{a} Δ={rel:+d} abs={abs_d}")

                # id hits that are NOT the CAPA record itself
                lines.append("### other id contexts (skip CAPA rec ±32)")
                shown = 0
                for ih in id_hits:
                    if abs(ih - rec["rec_at"]) < 32:
                        continue
                    lines.append("  " + dump(mm, ih, 40, 40))
                    shown += 1
                    if shown >= 12:
                        break

                lines.append("### other ptr contexts (skip twin inside CAPA rec)")
                shown = 0
                for ph in ptr_hits:
                    if abs(ph - rec["rec_at"]) < 32:
                        continue
                    lines.append("  " + dump(mm, ph, 40, 40))
                    shown += 1
                    if shown >= 12:
                        break

            # Bonus: scan ±256KB around closest Assan double for any CAPA-family magic
            lines.append("")
            lines.append("## CAPA magic near Assan doubles (±256KB)")
            magic = b"\x00\x40\x20\x00\x00\x00\x00"
            for d in doubles[:6]:
                lo = max(0, d - 256_000)
                hi = min(len(mm), d + 256_000)
                region = mm[lo:hi]
                # mm slice is bytes-like
                start = 0
                found = []
                while len(found) < 20:
                    j = region.find(magic, start)
                    if j < 0:
                        break
                    abs_off = lo + j
                    id_at = abs_off + 7
                    if id_at + 17 < len(mm):
                        rid = struct.unpack_from("<I", mm, id_at)[0]
                        ca = struct.unpack_from("<H", mm, id_at + 13)[0]
                        pa = struct.unpack_from("<H", mm, id_at + 15)[0]
                        found.append((abs_off - d, rid, ca, pa, abs_off))
                    start = j + 1
                lines.append(f"dab@{d}: {len(found)} magic in window")
                for rel, rid, ca, pa, abs_off in found[:10]:
                    lines.append(
                        f"  Δ={rel:+d} id={rid} ca/pa={ca}/{pa} @{abs_off}"
                    )

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
