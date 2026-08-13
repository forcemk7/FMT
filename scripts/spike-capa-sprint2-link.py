#!/usr/bin/env python3
"""Sprint 2: link tagged CA/PA records to person UIDs; verify 3-player truth.

Record family (from sprint1):
  .. ?? 00 40 20 00 00 00 00 <id:u32> <ptr:u32> <ptr:u32> 02 <CA:u16> <PA:u16> ...
"""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint2-link.txt"

CANDIDATE_BINS = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

TRUTH = {
    2000188173: ("Assan", 186, 190),
    2002185604: ("Kizza", 165, 165),
    2002234366: ("Bandeira", 184, 184),
}

# From sprint1 Assan-tagged records
SEED_IDS = [653202, 672906]

MAGIC = b"\x00\x40\x20\x00\x00\x00\x00"  # shared core before id


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


def parse_rec(mm: mmap.mmap, magic_at: int) -> dict | None:
    """magic_at points at 00 40 20 00 00 00 00; id starts at magic_at+7."""
    id_at = magic_at + 7
    if id_at + 4 + 8 + 1 + 4 > len(mm):
        return None
    rid = struct.unpack_from("<I", mm, id_at)[0]
    p1 = struct.unpack_from("<I", mm, id_at + 4)[0]
    p2 = struct.unpack_from("<I", mm, id_at + 8)[0]
    if p1 != p2:
        return None
    tag = mm[id_at + 12]
    ca = struct.unpack_from("<H", mm, id_at + 13)[0]
    pa = struct.unpack_from("<H", mm, id_at + 15)[0]
    if not (1 <= ca <= 200 and 1 <= pa <= 200):
        return None
    # optional following u16s
    rest = [
        struct.unpack_from("<H", mm, id_at + 17 + 2 * i)[0] for i in range(4)
    ]
    return {
        "magic_at": magic_at,
        "id_at": id_at,
        "id": rid,
        "ptr": p1,
        "tag": tag,
        "ca": ca,
        "pa": pa,
        "rest": rest,
        "pre_byte": mm[magic_at - 1] if magic_at > 0 else None,
    }


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint2 link · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            magics = find_all(mm, MAGIC)
            lines.append(f"magic hits={len(magics)}")
            recs = []
            for m in magics:
                r = parse_rec(mm, m)
                if r:
                    recs.append(r)
            lines.append(f"parsed CA/PA records={len(recs)}")

            # Index by (ca,pa) and by id
            by_pair: dict[tuple[int, int], list[dict]] = {}
            by_id: dict[int, list[dict]] = {}
            for r in recs:
                by_pair.setdefault((r["ca"], r["pa"]), []).append(r)
                by_id.setdefault(r["id"], []).append(r)

            lines.append("")
            lines.append("## truth pair hits in this family")
            for uid, (name, ca, pa) in TRUTH.items():
                hits = by_pair.get((ca, pa), [])
                lines.append(f"{name} ({ca},{pa}): {len(hits)} records")
                for r in hits[:8]:
                    lines.append(
                        f"  id={r['id']} tag={r['tag']} ptr={r['ptr']} "
                        f"pre=0x{r['pre_byte']:02x} rest={r['rest']} @{r['id_at']}"
                    )

            # UID hit lists
            uid_pos: dict[int, list[int]] = {}
            for uid in TRUTH:
                uid_pos[uid] = find_all(mm, struct.pack("<I", uid), limit=400)

            lines.append("")
            lines.append("## seed ids near Assan UID?")
            for sid in SEED_IDS:
                sidb = struct.pack("<I", sid)
                sid_hits = find_all(mm, sidb, limit=200)
                assan = uid_pos[2000188173]
                best = None
                for s in sid_hits:
                    for u in assan:
                        d = abs(s - u)
                        if best is None or d < best[0]:
                            best = (d, s - u, s, u)
                lines.append(
                    f"id={sid} occurrences={len(sid_hits)} "
                    f"nearest AssanUID Δ={best[1] if best else 'n/a'} "
                    f"(abs={best[0] if best else 'n/a'})"
                )
                # dump co-occurrence windows within 4KB
                near = 0
                for s in sid_hits:
                    if any(abs(s - u) <= 4096 for u in assan):
                        near += 1
                        u = min(assan, key=lambda x: abs(x - s))
                        lo = max(0, min(s, u) - 16)
                        hi = min(len(mm), max(s, u) + 24)
                        lines.append(
                            f"  co@{s} uid@{u} Δ={s - u:+d} "
                            + bytes(mm[lo:hi]).hex(" ")
                        )
                        if near >= 5:
                            break
                lines.append(f"  co-within-4KB count≈{near}+")

            # For each truth player: find records, then search record.id near that UID
            lines.append("")
            lines.append("## per-player: record.id ↔ UID proximity (±64KB)")
            for uid, (name, ca, pa) in TRUTH.items():
                hits = by_pair.get((ca, pa), [])
                ups = uid_pos[uid]
                lines.append(f"### {name} pair-recs={len(hits)} uid-hits={len(ups)}")
                linked = []
                for r in hits:
                    ridb = struct.pack("<I", r["id"])
                    # search id near each uid? too slow. Instead: find all id hits once
                    id_hits = find_all(mm, ridb, limit=80)
                    best = None
                    for ih in id_hits:
                        for u in ups:
                            d = abs(ih - u)
                            if best is None or d < best[0]:
                                best = (d, ih - u, ih, u, r)
                    if best and best[0] <= 65536:
                        linked.append(best)
                linked.sort(key=lambda t: t[0])
                if not linked:
                    lines.append("  no id↔UID within 64KB")
                    # show nearest anyway for first record
                    if hits:
                        r = hits[0]
                        id_hits = find_all(mm, struct.pack("<I", r["id"]), limit=80)
                        best = None
                        for ih in id_hits:
                            for u in ups:
                                d = abs(ih - u)
                                if best is None or d < best[0]:
                                    best = (d, ih - u, ih, u, r)
                        if best:
                            lines.append(
                                f"  closest overall: id={r['id']} "
                                f"Δ={best[1]:+d} abs={best[0]}"
                            )
                else:
                    for d, rel, ih, u, r in linked[:10]:
                        lines.append(
                            f"  LINK? id={r['id']} ca/pa={r['ca']}/{r['pa']} "
                            f"id@={ih} uid@={u} Δ={rel:+d}"
                        )

            # Tag histogram
            lines.append("")
            lines.append("## tag byte histogram (all parsed)")
            tags: dict[int, int] = {}
            for r in recs:
                tags[r["tag"]] = tags.get(r["tag"], 0) + 1
            for t, n in sorted(tags.items(), key=lambda x: -x[1])[:15]:
                lines.append(f"  tag=0x{t:02x} count={n}")

            # pre_byte histogram
            lines.append("")
            lines.append("## pre_byte (before 00 40 20) histogram")
            pres: dict[int, int] = {}
            for r in recs:
                if r["pre_byte"] is not None:
                    pres[r["pre_byte"]] = pres.get(r["pre_byte"], 0) + 1
            for b, n in sorted(pres.items(), key=lambda x: -x[1])[:15]:
                lines.append(f"  pre=0x{b:02x} count={n}")

        finally:
            mm.close()

    lines.append("")
    lines.append(f"elapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    # avoid Windows console encoding issues
    print(text.encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
