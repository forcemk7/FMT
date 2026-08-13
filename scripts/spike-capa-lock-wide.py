#!/usr/bin/env python3
"""Wider CAPA lock: find CA/PA u16le near UIDs (not only person-double windows).

Truth (FMRTE, this save):
  Assan   2000188173  CA=186 PA=190
  Kizza   2002185604  CA=165 PA=165
  Bandeira 2002234366 CA=184 PA=184
"""

from __future__ import annotations

import struct
import time
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "capa-lock-wide.txt"

TRUTH = {
    2000188173: ("Assan", 186, 190),
    2002185604: ("Kizza", 165, 165),
    2002234366: ("Bandeira", 184, 184),
}

RADIUS = 48_000  # bytes around each UID hit to keep


def log(s: str = "") -> None:
    print(s, flush=True)


def stream(path: Path):
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf." and head[25] == 3
        r = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = r.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            try:
                r.close()
            except zstd.ZstdError:
                pass


def find_all_in(data: bytes, needle: bytes, base: int) -> list[int]:
    out = []
    start = 0
    while True:
        j = data.find(needle, start)
        if j < 0:
            break
        out.append(base + j)
        start = j + 1
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    log(f"wide CAPA lock · {SAVE.name}")
    t0 = time.perf_counter()

    # Phase 1: collect UID hit abs offsets (cap per uid)
    uid_hits: dict[int, list[int]] = {u: [] for u in TRUTH}
    needles = {u: struct.pack("<I", u) for u in TRUTH}
    max_uid_hits = 40
    abs_base = 0
    carry = b""
    overlap = 8
    for block in stream(SAVE):
        data = carry + block
        base = abs_base - len(carry)
        for uid, nb in needles.items():
            if len(uid_hits[uid]) >= max_uid_hits:
                continue
            for off in find_all_in(data, nb, base):
                if len(uid_hits[uid]) < max_uid_hits:
                    # dedupe near duplicates
                    if not uid_hits[uid] or off - uid_hits[uid][-1] > 4:
                        uid_hits[uid].append(off)
        abs_base += len(block)
        carry = data[-overlap:]
        if all(len(uid_hits[u]) >= max_uid_hits for u in TRUTH):
            break

    for uid, (name, ca, pa) in TRUTH.items():
        log(f"  {name}: {len(uid_hits[uid])} uid hits")

    # Phase 2: second pass — for each UID hit, capture window and hunt CA/PA
    # Build target ranges to extract
    ranges: list[tuple[int, int, int]] = []  # (lo, hi, uid)
    for uid, hits in uid_hits.items():
        for h in hits:
            lo = max(0, h - RADIUS)
            hi = h + RADIUS
            ranges.append((lo, hi, uid))
    ranges.sort()

    # merge overlapping for same stream, but keep association via hits
    # Simpler: stream again and for each block, check any range overlap
    # Store raw windows keyed by (uid, hit_abs)
    windows: dict[tuple[int, int], bytearray] = {}
    for lo, hi, uid in ranges:
        # find nearest hit for this uid in [lo,hi]
        hit = min(
            (h for h in uid_hits[uid] if lo <= h < hi),
            key=lambda h: abs(h - (lo + hi) // 2),
            default=None,
        )
        if hit is None:
            continue
        windows[(uid, hit)] = bytearray(hi - lo)  # placeholder filled below

    abs_base = 0
    carry = b""
    overlap = 64
    need_bytes = {k: True for k in windows}
    for block in stream(SAVE):
        data = carry + block
        base = abs_base - len(carry)
        end = base + len(data)
        for (uid, hit), buf in windows.items():
            if not need_bytes[(uid, hit)]:
                continue
            lo = hit - RADIUS
            if lo < 0:
                # pad left conceptually — skip hits near start
                continue
            hi = hit + RADIUS
            # copy overlap of [base,end) into buf
            c0 = max(base, lo)
            c1 = min(end, hi)
            if c0 < c1:
                src0 = c0 - base
                dst0 = c0 - lo
                buf[dst0 : dst0 + (c1 - c0)] = data[src0 : src0 + (c1 - c0)]
            if end >= hi:
                need_bytes[(uid, hit)] = False
        abs_base += len(block)
        carry = data[-overlap:]
        if abs_base % (256 * 1024 * 1024) < 8 * 1024 * 1024:
            left = sum(1 for v in need_bytes.values() if v)
            log(f"  …{abs_base // (1024*1024)} MiB windows left={left}")
        if not any(need_bytes.values()):
            break

    log(f"windows filled {time.perf_counter()-t0:.1f}s · n={len(windows)}")

    lines = [
        "# Wide CA/PA lock",
        f"save={SAVE.name}",
        f"radius={RADIUS}",
        "",
    ]

    # For each player: distances from UID to CA and PA
    # Layout key: (ca_rel, pa_rel) where rel is vs UID
    layout_counter: Counter[tuple[int, int]] = Counter()
    layout_players: dict[tuple[int, int], set[str]] = defaultdict(set)
    # also ca-only / pa-only
    ca_rel_players: dict[int, set[str]] = defaultdict(set)
    pa_rel_players: dict[int, set[str]] = defaultdict(set)

    for (uid, hit), buf in windows.items():
        name, ca, pa = TRUTH[uid]
        uid_in_win = RADIUS  # by construction hit at RADIUS if lo=hit-RADIUS
        # verify
        if struct.unpack_from("<I", buf, uid_in_win)[0] != uid:
            # find uid
            nb = struct.pack("<I", uid)
            j = buf.find(nb)
            if j < 0:
                continue
            uid_in_win = j

        ca_b = struct.pack("<H", ca)
        pa_b = struct.pack("<H", pa)
        ca_pos = []
        pa_pos = []
        start = 0
        while True:
            j = buf.find(ca_b, start)
            if j < 0:
                break
            ca_pos.append(j - uid_in_win)
            start = j + 1
        start = 0
        while True:
            j = buf.find(pa_b, start)
            if j < 0:
                break
            pa_pos.append(j - uid_in_win)
            start = j + 1

        # keep small candidate set: |rel| < 20000, prefer closer
        ca_pos = [r for r in ca_pos if abs(r) < 20_000]
        pa_pos = [r for r in pa_pos if abs(r) < 20_000]

        for r in ca_pos:
            ca_rel_players[r].add(name)
        for r in pa_pos:
            pa_rel_players[r].add(name)

        for cr in ca_pos:
            for pr in pa_pos:
                # when ca==pa, require distinct positions OR same for equal pair
                if ca == pa and cr == pr:
                    layout_counter[(cr, pr)] += 1
                    layout_players[(cr, pr)].add(name)
                elif ca != pa and cr != pr:
                    layout_counter[(cr, pr)] += 1
                    layout_players[(cr, pr)].add(name)
                elif ca == pa and cr != pr:
                    # equal values at two slots — classic CA then PA
                    layout_counter[(cr, pr)] += 1
                    layout_players[(cr, pr)].add(name)

    lines.append("## CA-relative offsets shared by ≥2 players (top)")
    scored = sorted(
        ((r, names) for r, names in ca_rel_players.items() if len(names) >= 2),
        key=lambda t: (-len(t[1]), abs(t[0])),
    )[:40]
    for r, names in scored:
        lines.append(f"  ca_rel={r:+d} players={sorted(names)}")

    lines.append("")
    lines.append("## PA-relative offsets shared by ≥2 players (top)")
    scored = sorted(
        ((r, names) for r, names in pa_rel_players.items() if len(names) >= 2),
        key=lambda t: (-len(t[1]), abs(t[0])),
    )[:40]
    for r, names in scored:
        lines.append(f"  pa_rel={r:+d} players={sorted(names)}")

    lines.append("")
    lines.append("## (ca_rel, pa_rel) layouts covering all 3 players")
    full = [
        (cr, pr, layout_players[(cr, pr)], layout_counter[(cr, pr)])
        for (cr, pr) in layout_players
        if len(layout_players[(cr, pr)]) == 3
    ]
    full.sort(key=lambda t: (abs(t[0]) + abs(t[1]), abs(t[0])))
    name_to_capa = {n: (c, p) for (n, c, p) in TRUTH.values()}
    if not full:
        lines.append("  (none exact)")
        lines.append("")
        lines.append("## fuzzy: shared (pa−ca) byte distance")
        dist_cover: dict[int, set[str]] = defaultdict(set)
        dist_examples: dict[int, list[str]] = defaultdict(list)
        for (cr, pr), names in layout_players.items():
            d = pr - cr
            if abs(d) > 128:
                continue
            for name in names:
                ca_v, pa_v = name_to_capa[name]
                if d == 0 and ca_v != pa_v:
                    continue
                dist_cover[d].add(name)
                if len(dist_examples[d]) < 8:
                    dist_examples[d].append(f"{name}:ca@{cr:+d},pa@{pr:+d}")
        for d, names in sorted(dist_cover.items(), key=lambda t: (-len(t[1]), abs(t[0]))):
            if len(names) >= 2:
                lines.append(
                    f"  dist={d:+d} n={len(names)} {sorted(names)} | "
                    + "; ".join(dist_examples[d][:6])
                )
    else:
        for cr, pr, names, n in full[:30]:
            lines.append(
                f"  LOCK? ca@{cr:+d} pa@{pr:+d} (Δ={pr-cr:+d}) hits≈{n} {sorted(names)}"
            )

    lines.append("")
    lines.append("## Assan hex dumps around CA=186 and PA=190 near UID")
    dumped = 0
    for (uid, hit), buf in windows.items():
        if uid != 2000188173:
            continue
        dumped += 1
        if dumped > 3:
            break
        lines.append(f"  --- window hit={hit} ---")
        uid_in = RADIUS
        if len(buf) < uid_in + 4 or struct.unpack_from("<I", buf, uid_in)[0] != uid:
            nb = struct.pack("<I", uid)
            j = buf.find(nb)
            if j < 0:
                continue
            uid_in = j
        for label, val in (("CA", 186), ("PA", 190)):
            b = struct.pack("<H", val)
            start = 0
            shown = 0
            while shown < 4:
                j = buf.find(b, start)
                if j < 0:
                    break
                rel = j - uid_in
                if abs(rel) < 12_000:
                    lo = max(0, j - 8)
                    hx = bytes(buf[lo : j + 12]).hex(" ")
                    lines.append(f"  {label}@{rel:+d} {hx}")
                    shown += 1
                start = j + 1
    lines.append(f"\nelapsed={time.perf_counter()-t0:.1f}s")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    for line in lines:
        if (
            line.startswith("#")
            or line.startswith("##")
            or "LOCK" in line
            or line.startswith("  ca_rel=")
            or line.startswith("  pa_rel=")
            or line.startswith("  dist=")
            or line.startswith("save=")
        ):
            log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
