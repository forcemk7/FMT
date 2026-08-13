#!/usr/bin/env python3
"""Sprint 7: join Assan person-index (115401) to CAPA ids; classify CAPA as player vs staff."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint7-index-join.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

ASSAN_UID = 2000188173
PERSON_IDX = 115401  # from dab@159849949 immediately before Assan UID double
CAPA_IDS = [653714, 672906]


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


def dump(mm: mmap.mmap, off: int, before: int = 32, after: int = 48) -> str:
    lo = max(0, off - before)
    hi = min(len(mm), off + after)
    return f"@{off} " + bytes(mm[lo:hi]).hex(" ")


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint7 index join · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            idx_hits = find_all(mm, struct.pack("<I", PERSON_IDX), limit=200)
            lines.append(f"personIdx {PERSON_IDX} hits={len(idx_hits)}")

            for cid in CAPA_IDS:
                c_hits = find_all(mm, struct.pack("<I", cid), limit=100)
                lines.append("")
                lines.append(f"## CAPA id={cid} hits={len(c_hits)}")
                # co-occur with person idx
                for w in (64, 256, 1024, 4096, 16384, 65536):
                    pairs = []
                    for ih in idx_hits:
                        for ch in c_hits:
                            d = abs(ih - ch)
                            if d <= w:
                                pairs.append((d, ch - ih, ch, ih))
                    pairs.sort()
                    uniq = []
                    seen = set()
                    for p in pairs:
                        k = (p[2], p[3])
                        if k in seen:
                            continue
                        seen.add(k)
                        uniq.append(p)
                    lines.append(f"  co-occur ±{w}: {len(uniq)}")
                    for d, rel, ch, ih in uniq[:5]:
                        lines.append(f"    Δ={rel:+d} capa@{ch} idx@{ih}")
                        if d <= 1024:
                            lines.append("      " + dump(mm, min(ch, ih), 16, d + 32))

            # Inspect ASCII nation/club field across Assan CAPA records
            lines.append("")
            lines.append("## Assan CAPA post fields decoded")
            for cid, rec_at in ((653714, 473312795), (672906, 488012982)):
                # id_at from sprint2; post starts id_at+17
                # From earlier dumps, magic is 12 bytes before id for 00 40 20 form
                # Use search: find id at known CAPA site
                id_at = mm.find(struct.pack("<I", cid), rec_at - 8, rec_at + 8)
                if id_at < 0:
                    id_at = rec_at
                post = bytes(mm[id_at + 17 : id_at + 60])
                ca = struct.unpack_from("<H", mm, id_at + 13)[0]
                pa = struct.unpack_from("<H", mm, id_at + 15)[0]
                rep = struct.unpack_from("<H", post, 0)[0]
                a = struct.unpack_from("<H", post, 2)[0]
                b = struct.unpack_from("<H", post, 4)[0]
                c = struct.unpack_from("<H", post, 6)[0]
                # bytes 8.. : ff ?, ascii?
                lines.append(
                    f"id={cid} ca/pa={ca}/{pa} rep={rep} a={a} b={b} c={c} "
                    f"post={post.hex(' ')}"
                )
                # try ascii extract
                ascii_bits = "".join(
                    chr(x) if 32 <= x < 127 else "." for x in post
                )
                lines.append(f"  ascii: {ascii_bits}")

            # Hypothesis: CAPA table is ALL persons (players+staff) ordered by id.
            # Sample id→ca/pa density and whether ids are unique.
            lines.append("")
            lines.append("## CAPA id uniqueness / monotonicity sample")
            magic = b"\x00\x40\x20\x00\x00\x00\x00"
            sample = []
            start = 470_000_000
            end = 490_000_000
            pos = start
            while len(sample) < 30 and pos < end:
                j = mm.find(magic, pos, end)
                if j < 0:
                    break
                id_at = j + 7
                rid = struct.unpack_from("<I", mm, id_at)[0]
                p1 = struct.unpack_from("<I", mm, id_at + 4)[0]
                p2 = struct.unpack_from("<I", mm, id_at + 8)[0]
                ca = struct.unpack_from("<H", mm, id_at + 13)[0]
                pa = struct.unpack_from("<H", mm, id_at + 15)[0]
                if p1 == p2 and 1 <= ca <= 200 and 1 <= pa <= 200:
                    sample.append((rid, ca, pa, j))
                pos = j + 1
            lines.append(f"sample n={len(sample)}")
            for rid, ca, pa, j in sample:
                lines.append(f"  id={rid} ca/pa={ca}/{pa} @{j}")
            ids = [s[0] for s in sample]
            if ids:
                lines.append(
                    f"  monotonic_nondec={all(ids[i] <= ids[i+1] for i in range(len(ids)-1))}"
                )
                lines.append(f"  unique={len(ids)==len(set(ids))}")

            # Search personIdx as u32 next to Assan UID in other sites
            lines.append("")
            lines.append("## personIdx beside Assan UID (±32)")
            uids = find_all(mm, struct.pack("<I", ASSAN_UID), limit=300)
            idxb = struct.pack("<I", PERSON_IDX)
            n = 0
            for u in uids:
                win = bytes(mm[max(0, u - 32) : u + 36])
                if idxb in win:
                    n += 1
                    if n <= 8:
                        lines.append("  " + dump(mm, u, 40, 40))
            lines.append(f"  total UID sites with idx within ±32: {n}")

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
