#!/usr/bin/env python3
"""Sprint 6: match Bandeira attrs / UID inside CAPA (184,184) records."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint6-bandeira.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

UID = 2002234366
CA = PA = 184
# Distinctive attr bytes from fixture (1-20)
FINGERPRINTS = [
    bytes([17, 16, 15, 14, 13]),  # common ordered clusters unlikely
    bytes([18, 17, 16]),  # conc/bal heavy player
    bytes([8, 15, 7, 12, 16]),  # tech start-ish crossing..heading variant
    bytes([9, 17, 13, 13, 18, 16, 16]),  # mental aggression..det
    bytes([16, 17, 18, 17, 16, 17, 16, 17]),  # physical block
]

MAGIC = b"\x00\x40\x20\x00\x00\x00\x00"


def pick_bin() -> Path:
    for p in CANDIDATE_BINS:
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no ~2GB fmt-*.bin")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 50_000) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def parse_capa(mm: mmap.mmap, magic_at: int) -> dict | None:
    id_at = magic_at + 7
    if id_at + 17 >= len(mm):
        return None
    rid = struct.unpack_from("<I", mm, id_at)[0]
    p1 = struct.unpack_from("<I", mm, id_at + 4)[0]
    p2 = struct.unpack_from("<I", mm, id_at + 8)[0]
    if p1 != p2:
        return None
    tag = mm[id_at + 12]
    ca = struct.unpack_from("<H", mm, id_at + 13)[0]
    pa = struct.unpack_from("<H", mm, id_at + 15)[0]
    if ca != CA or pa != PA:
        return None
    return {"magic_at": magic_at, "id_at": id_at, "id": rid, "ptr": p1, "tag": tag}


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint6 Bandeira · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # Collect (184,184) CAPA records (cap magic scan)
            recs = []
            for m in find_all(mm, MAGIC, limit=80_000):
                r = parse_capa(mm, m)
                if r:
                    recs.append(r)
            lines.append(f"(184,184) CAPA records={len(recs)}")

            uidb = struct.pack("<I", UID)
            uid_hits = find_all(mm, uidb, limit=200)
            lines.append(f"Bandeira UID hits={len(uid_hits)}")

            for r in recs:
                lines.append("")
                lines.append(f"## rec id={r['id']} ptr={r['ptr']} @{r['id_at']}")
                # window: from magic through ~1200 bytes (variable record)
                lo = r["magic_at"]
                hi = min(len(mm), lo + 1400)
                blob = bytes(mm[lo:hi])
                lines.append(f"  head: " + blob[:80].hex(" "))

                # UID inside record?
                rels = []
                start = 0
                while True:
                    j = blob.find(uidb, start)
                    if j < 0:
                        break
                    rels.append(j)
                    start = j + 1
                lines.append(f"  UID inside +1400: {rels}")

                # nearest UID globally
                best = min((abs(u - r["id_at"]), u - r["id_at"], u) for u in uid_hits)
                lines.append(f"  nearest UID Δ={best[1]:+d} abs={best[0]} @{best[2]}")

                # fingerprint hits in blob
                for i, fp in enumerate(FINGERPRINTS):
                    pos = []
                    start = 0
                    while True:
                        j = blob.find(fp, start)
                        if j < 0:
                            break
                        pos.append(j)
                        start = j + 1
                    if pos:
                        lines.append(f"  fp[{i}] {fp.hex()} at {pos[:8]}")

                # score: count of known attr values as consecutive 1-20 runs
                # dump bytes after CA/PA (offset id_at+17 relative to magic = 7+17=24)
                post = blob[24:120]
                lines.append(f"  post-CA/PA: " + post.hex(" "))
                # interpret as u8 attrs: find longest run of bytes in 1..20
                best_run = (0, 0)
                run_s = None
                for i, b in enumerate(post):
                    if 1 <= b <= 20:
                        if run_s is None:
                            run_s = i
                    else:
                        if run_s is not None:
                            ln = i - run_s
                            if ln > best_run[0]:
                                best_run = (ln, run_s)
                            run_s = None
                if run_s is not None:
                    ln = len(post) - run_s
                    if ln > best_run[0]:
                        best_run = (ln, run_s)
                if best_run[0]:
                    s = best_run[1]
                    chunk = list(post[s : s + best_run[0]])
                    lines.append(f"  best 1-20 run len={best_run[0]} @{s}: {chunk}")

            # Also: search physical fingerprint globally near Bandeira doubles
            lines.append("")
            lines.append("## physical fingerprint near Bandeira UID")
            phys = bytes([16, 17, 18, 17, 16, 17, 16, 17])
            phys_hits = find_all(mm, phys, limit=50)
            lines.append(f"phys fingerprint hits={len(phys_hits)}")
            for ph in phys_hits[:20]:
                best = min((abs(u - ph), u - ph, u) for u in uid_hits)
                # also check if CAPA magic precedes within 200 bytes
                pre = bytes(mm[max(0, ph - 200) : ph])
                has_magic = MAGIC in pre
                has_capa = struct.pack("<HH", 184, 184) in pre
                lines.append(
                    f"  phys@{ph} nearest UID Δ={best[1]:+d} abs={best[0]} "
                    f"magic_pre200={has_magic} ca184_pre200={has_capa}"
                )
                if best[0] <= 20000 or has_magic:
                    lines.append(
                        "    ctx: "
                        + bytes(mm[max(0, ph - 64) : ph + 32]).hex(" ")
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
