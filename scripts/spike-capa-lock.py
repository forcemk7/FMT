#!/usr/bin/env python3
"""Lock CA/PA encoding from FMRTE ground truth (one decompress).

Assan Ouédraogo 2000188173  CA=186 PA=190
Sam Kizza       2002185604  CA=165 PA=165
Patrick Bandeira 2002234366 CA=184 PA=184
"""

from __future__ import annotations

import struct
import time
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "capa-lock.txt"

TRUTH = {
    2000188173: ("Assan Ouédraogo", 186, 190),
    2002185604: ("Sam Kizza", 165, 165),
    2002234366: ("Patrick Bandeira", 184, 184),
}

WIN_B, WIN_A = 256, 160
MAX_DOUBLES = 6


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


def collect() -> dict[int, list[tuple[int, bytes]]]:
    needles = {u: struct.pack("<I", u) for u in TRUTH}
    found: dict[int, list[tuple[int, bytes]]] = {u: [] for u in TRUTH}
    need = {u: MAX_DOUBLES for u in TRUTH}
    abs_base = 0
    carry = b""
    overlap = WIN_B + WIN_A + 96
    for block in stream(SAVE):
        data = carry + block
        for uid, nb in needles.items():
            if need[uid] <= 0:
                continue
            start = 0
            while need[uid] > 0:
                j = data.find(nb, start)
                if j < 0:
                    break
                k = data.find(nb, j + 4, min(len(data), j + 48))
                if k > 0:
                    lo, hi = j - WIN_B, k + WIN_A
                    if lo >= 0 and hi <= len(data):
                        abs_off = abs_base - len(carry) + j
                        found[uid].append((abs_off, data[lo:hi]))
                        need[uid] -= 1
                start = j + 1
        abs_base += len(block)
        carry = data[-overlap:]
        if all(n <= 0 for n in need.values()):
            break
        if abs_base % (128 * 1024 * 1024) < 8 * 1024 * 1024:
            left = sum(1 for n in need.values() if n > 0)
            log(f"  …{abs_base // (1024*1024)} MiB, open={left}")
    return found


def encodings(ca: int, pa: int) -> list[tuple[str, bytes]]:
    """Candidate packed forms for the known pair."""
    out: list[tuple[str, bytes]] = []
    # i16 / u16 adjacent
    out.append(("i16le_ca_pa", struct.pack("<hh", ca, pa)))
    out.append(("u16le_ca_pa", struct.pack("<HH", ca, pa)))
    out.append(("i16le_pa_ca", struct.pack("<hh", pa, ca)))
    out.append(("u16le_pa_ca", struct.pack("<HH", pa, ca)))
    # with 2-byte gap
    out.append(("i16le_ca_xx_pa", struct.pack("<h", ca) + b"\x00\x00" + struct.pack("<h", pa)))
    # u8
    out.append(("u8_ca_pa", bytes([ca, pa])))
    out.append(("u8_pa_ca", bytes([pa, ca])))
    # i16 with common type tags between (guess)
    for tag in (b"\x00\x00", b"\x01\x00", b"\x02\x00", b"\xff\xff"):
        out.append((f"i16_ca_tag{tag.hex()}_pa", struct.pack("<h", ca) + tag + struct.pack("<h", pa)))
    return out


def find_all(hay: bytes, needle: bytes) -> list[int]:
    out = []
    start = 0
    while True:
        j = hay.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    log(f"CAPA lock · {SAVE.name}")
    t0 = time.perf_counter()
    wins = collect()
    log(f"collect {time.perf_counter()-t0:.1f}s")

    lines = ["# CA/PA lock from FMRTE truth", f"save={SAVE.name}", ""]
    # Per-player: which encodings appear, at which offset vs first UID
    layout_hits: dict[tuple[str, int], set[int]] = defaultdict(set)
    layout_detail: dict[tuple[str, int], list[str]] = defaultdict(list)

    for uid, (name, ca, pa) in TRUTH.items():
        sites = wins.get(uid) or []
        lines.append(f"## {name} uid={uid} CA={ca} PA={pa} doubles={len(sites)}")
        if not sites:
            lines.append("  NO doubles")
            continue
        encs = encodings(ca, pa)
        # Also search for ca and pa alone as i16
        for abs_off, win in sites:
            uid_rel = WIN_B  # by construction
            for kind, needle in encs:
                for j in find_all(win, needle):
                    rel = j - uid_rel
                    layout_hits[(kind, rel)].add(uid)
                    layout_detail[(kind, rel)].append(
                        f"{name}@abs={abs_off}+{rel}"
                    )
            # lone ca / pa positions (for structure dump)
            ca_b = struct.pack("<h", ca)
            pa_b = struct.pack("<h", pa)
            for j in find_all(win, ca_b):
                rel = j - uid_rel
                if -200 <= rel <= 120:
                    # dump 16 bytes around
                    lo = max(0, j - 4)
                    hx = win[lo : j + 8].hex(" ")
                    lines.append(f"  ca@rel={rel:+d} ctx={hx}")
            for j in find_all(win, pa_b):
                rel = j - uid_rel
                if -200 <= rel <= 120 and pa != ca:
                    lo = max(0, j - 4)
                    hx = win[lo : j + 8].hex(" ")
                    lines.append(f"  pa@rel={rel:+d} ctx={hx}")
        # summarize encodings for this player
        player_layouts = {
            (k, r)
            for (k, r), uids in layout_hits.items()
            if uid in uids
        }
        # only keep if hit in ≥1 site — already
        best = Counter()
        for abs_off, win in sites:
            for kind, needle in encs:
                for j in find_all(win, needle):
                    best[(kind, j - WIN_B)] += 1
        for (kind, rel), n in best.most_common(15):
            lines.append(f"  ENC {kind} off={rel:+d} sites={n}/{len(sites)}")
        lines.append("")

    lines.append("## layouts shared by ALL three players")
    shared = [
        (k, r, layout_hits[(k, r)])
        for (k, r) in layout_hits
        if len(layout_hits[(k, r)]) == 3
    ]
    shared.sort(key=lambda t: (abs(t[1]), t[0]))
    if not shared:
        lines.append("  (none at identical relative offset)")
        # try same kind, offsets within ±8 of each other across players
        lines.append("")
        lines.append("## near-aligned same-kind layouts (fuzzy ±8)")
        by_kind: dict[str, list[tuple[int, set[int]]]] = defaultdict(list)
        for (kind, rel), uids in layout_hits.items():
            by_kind[kind].append((rel, uids))
        for kind, items in by_kind.items():
            # cluster by offset
            for rel, uids in sorted(items, key=lambda x: x[0]):
                if len(uids) < 2:
                    continue
                cluster = [
                    (r2, u2)
                    for r2, u2 in items
                    if abs(r2 - rel) <= 8
                ]
                cover = set()
                for _, u2 in cluster:
                    cover |= u2
                if len(cover) == 3:
                    offs = sorted({r for r, _ in cluster})
                    lines.append(
                        f"  {kind} offs≈{offs} cover=3 detail="
                        + "; ".join(layout_detail[(kind, r)][0] for r in offs[:3] if (kind, r) in layout_detail)
                    )
    else:
        for kind, rel, uids in shared:
            lines.append(f"  LOCK? {kind} off={rel:+d} players={len(uids)}")
            for d in layout_detail[(kind, rel)][:6]:
                lines.append(f"    {d}")

    # Also: search pair as separate finds with fixed distance between ca and pa
    lines.append("")
    lines.append("## CA→PA fixed distances common to all three")
    # For each player, set of (rel_ca, dist) where dist is byte gap to pa
    player_dists: dict[int, set[tuple[int, int]]] = {}
    for uid, (name, ca, pa) in TRUTH.items():
        ds: set[tuple[int, int]] = set()
        ca_b = struct.pack("<h", ca)
        pa_b = struct.pack("<h", pa)
        for _, win in wins.get(uid) or []:
            ca_pos = find_all(win, ca_b)
            pa_pos = find_all(win, pa_b)
            for c in ca_pos:
                for p in pa_pos:
                    dist = p - c
                    if dist == 0 and ca == pa:
                        # same location — treat as adjacent equal
                        ds.add((c - WIN_B, 0))
                        continue
                    if 2 <= abs(dist) <= 64 and (c - WIN_B) >= -200:
                        ds.add((c - WIN_B, dist))
        player_dists[uid] = ds
        lines.append(f"  {name}: {len(ds)} (rel_ca, dist) candidates")

    # intersection on dist only (rel may drift), then check rel congruence
    dist_sets = []
    for uid in TRUTH:
        dist_sets.append({d for _, d in player_dists[uid]})
    common_dists = set.intersection(*dist_sets) if dist_sets else set()
    lines.append(f"  common distances: {sorted(common_dists)[:40]}")

    for dist in sorted(common_dists, key=abs)[:20]:
        # for each player, modal rel_ca at this dist
        rels = []
        for uid, (name, ca, pa) in TRUTH.items():
            rs = [r for r, d in player_dists[uid] if d == dist]
            if not rs:
                continue
            # prefer near 0
            rs.sort(key=abs)
            rels.append((name, rs[0], rs[:5]))
        if len(rels) == 3:
            lines.append(f"  dist={dist:+d} → " + "; ".join(f"{n} ca@{r:+d} (alts={a})" for n, r, a in rels))

    lines.append(f"\nelapsed={time.perf_counter()-t0:.1f}s")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    for line in lines:
        if (
            line.startswith("#")
            or line.startswith("##")
            or "LOCK" in line
            or line.startswith("  common")
            or line.startswith("  dist=")
            or line.startswith("  ENC")
            or line.startswith("save=")
        ):
            log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
