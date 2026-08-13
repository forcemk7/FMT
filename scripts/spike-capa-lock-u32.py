#!/usr/bin/env python3
"""Lock CA/PA as u32le (and u16le) using Assan's unique 186/190 pair.

Then verify the same relative layout on Kizza (165/165) and Bandeira (184/184).
"""

from __future__ import annotations

import struct
import time
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "capa-lock-u32.txt"

PLAYERS = [
    (2000188173, "Assan", 186, 190),
    (2002185604, "Kizza", 165, 165),
    (2002234366, "Bandeira", 184, 184),
]


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


def find_all(data: bytes, needle: bytes, base: int) -> list[int]:
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
    lines = [f"# u32 CAPA lock · {SAVE.name}", ""]
    t0 = time.perf_counter()

    # --- Phase A: Assan-unique pair motifs (global) ---
    ca, pa = 186, 190
    motifs: list[tuple[str, bytes]] = []
    # adjacent u32
    motifs.append(("u32_ca_pa", struct.pack("<II", ca, pa)))
    motifs.append(("u32_pa_ca", struct.pack("<II", pa, ca)))
    # u32 with 4-byte gap
    for gap_name, gap in (
        ("u32_ca_z4_pa", b"\x00\x00\x00\x00"),
        ("u32_ca_ff4_pa", b"\xff\xff\xff\xff"),
    ):
        motifs.append((gap_name, struct.pack("<I", ca) + gap + struct.pack("<I", pa)))
    # u16 adjacent
    motifs.append(("u16_ca_pa", struct.pack("<HH", ca, pa)))
    motifs.append(("u16_pa_ca", struct.pack("<HH", pa, ca)))
    # u32 CA then PA with common FM type prefixes before club-style: unlikely
    # packed i16 signed same as u16 for these values
    # CA/PA in a larger struct: scan CA u32 hits and look for PA within +64

    assan_motif_hits: dict[str, list[int]] = {k: [] for k, _ in motifs}
    # Also collect ALL Assan CA u32 and PA u32 abs positions (capped)
    ca32 = struct.pack("<I", ca)
    pa32 = struct.pack("<I", pa)
    ca32_hits: list[int] = []
    pa32_hits: list[int] = []
    MAX_VAL = 5000

    abs_base = 0
    carry = b""
    # need enough overlap for longest motif (~12)
    overlap = 32
    for block in stream(SAVE):
        data = carry + block
        base = abs_base - len(carry)
        for name, needle in motifs:
            if len(assan_motif_hits[name]) < 200:
                for off in find_all(data, needle, base):
                    if len(assan_motif_hits[name]) < 200:
                        assan_motif_hits[name].append(off)
        if len(ca32_hits) < MAX_VAL:
            for off in find_all(data, ca32, base):
                if len(ca32_hits) < MAX_VAL:
                    ca32_hits.append(off)
        if len(pa32_hits) < MAX_VAL:
            for off in find_all(data, pa32, base):
                if len(pa32_hits) < MAX_VAL:
                    pa32_hits.append(off)
        abs_base += len(block)
        carry = data[-overlap:]

    lines.append("## Assan motif hit counts (global)")
    for name, _ in motifs:
        lines.append(f"  {name}: {len(assan_motif_hits[name])}")
    lines.append(f"  ca_u32 alone (capped): {len(ca32_hits)}")
    lines.append(f"  pa_u32 alone (capped): {len(pa32_hits)}")

    # CA→PA distance histogram for nearby pairs
    pa_set = pa32_hits  # sorted by construction
    dist_ctr: Counter[int] = Counter()
    pair_examples: dict[int, list[int]] = defaultdict(list)
    pi = 0
    for c in ca32_hits:
        # advance pa pointer
        while pi < len(pa_set) and pa_set[pi] < c - 64:
            pi += 1
        j = pi
        while j < len(pa_set) and pa_set[j] <= c + 64:
            d = pa_set[j] - c
            if d != 0:
                dist_ctr[d] += 1
                if len(pair_examples[d]) < 5:
                    pair_examples[d].append(c)
            j += 1
    lines.append("")
    lines.append("## Assan CA_u32 → PA_u32 distances within ±64 (top)")
    for d, n in dist_ctr.most_common(25):
        lines.append(f"  Δ={d:+d} count={n} ca_at={pair_examples[d]}")

    # --- Phase B: for each motif hit, check UID proximity ---
    # Collect Assan UID positions
    assan_uid = struct.pack("<I", 2000188173)
    uid_hits: list[int] = []
    abs_base = 0
    carry = b""
    for block in stream(SAVE):
        data = carry + block
        base = abs_base - len(carry)
        for off in find_all(data, assan_uid, base):
            uid_hits.append(off)
        abs_base += len(block)
        carry = data[-8:]

    lines.append(f"\n## Assan UID hits: {len(uid_hits)}")
    uid_sorted = uid_hits

    def nearest_uid(abs_off: int) -> tuple[int, int] | None:
        # binary search nearest
        import bisect

        i = bisect.bisect_left(uid_sorted, abs_off)
        cands = []
        if i < len(uid_sorted):
            cands.append(uid_sorted[i])
        if i > 0:
            cands.append(uid_sorted[i - 1])
        if not cands:
            return None
        best = min(cands, key=lambda u: abs(u - abs_off))
        return best, abs_off - best

    lines.append("")
    lines.append("## Motif hits with UID within ±32KB")
    for name, hits in assan_motif_hits.items():
        near = []
        for h in hits:
            nu = nearest_uid(h)
            if nu and abs(nu[1]) <= 32_768:
                near.append((h, nu[0], nu[1]))
        lines.append(f"  {name}: {len(near)}/{len(hits)} near UID")
        for h, u, rel in near[:8]:
            lines.append(f"    motif@{h} uid@{u} motif_rel_to_uid={rel:+d}")

    # For best Δ from phase A, check UID proximity of those CA positions
    lines.append("")
    lines.append("## Best CA→PA Δ with UID proximity")
    for d, n in dist_ctr.most_common(10):
        import bisect

        near_n = 0
        examples = []
        for c in ca32_hits:
            target = c + d
            i = bisect.bisect_left(pa_set, target)
            if i < len(pa_set) and pa_set[i] == target:
                nu = nearest_uid(c)
                if nu and abs(nu[1]) <= 32_768:
                    near_n += 1
                    if len(examples) < 6:
                        examples.append((c, nu[0], nu[1]))
        lines.append(f"  Δ={d:+d} uid_near={near_n} ex={examples}")

    # --- Phase C: verify layout on all three players ---
    # Hypothesis candidates from Assan’s near-UID motif_rel values.
    # We'll take every (encoding, rel) seen for Assan and test others.

    # Re-stream once more: for each player, find person doubles, dump ±512 for
    # any occurrence of their ca/pa as u32 within the ATTR lookback (14KB).
    lines.append("")
    lines.append("## Per-player: ca_u32 / pa_u32 relative to person double")

    # Collect double sites
    doubles: dict[int, list[int]] = {u: [] for u, *_ in PLAYERS}
    needles = {u: struct.pack("<I", u) for u, *_ in PLAYERS}
    abs_base = 0
    carry = b""
    overlap = 64
    for block in stream(SAVE):
        data = carry + block
        base = abs_base - len(carry)
        for uid, nb in needles.items():
            if len(doubles[uid]) >= 8:
                continue
            start = 0
            while len(doubles[uid]) < 8:
                # find in data relative
                j = data.find(nb, start)
                if j < 0:
                    break
                k = data.find(nb, j + 4, min(len(data), j + 48))
                if k > 0:
                    doubles[uid].append(base + j)
                start = j + 1
        abs_base += len(block)
        carry = data[-overlap:]

    # Extract 16KB before each double
    LOOK = 16_384
    AFTER = 256
    windows: dict[tuple[int, int], bytes] = {}
    # mark ranges
    targets = []
    for uid, sites in doubles.items():
        for s in sites:
            targets.append((s - LOOK, s + AFTER, uid, s))

    abs_base = 0
    carry = b""
    overlap = 64
    buffers: dict[tuple[int, int], bytearray] = {
        (uid, s): bytearray(LOOK + AFTER) for uid, sites in doubles.items() for s in sites
    }
    pending = {k: True for k in buffers}
    for block in stream(SAVE):
        data = carry + block
        base = abs_base - len(carry)
        end = base + len(data)
        for (uid, s), buf in buffers.items():
            if not pending[(uid, s)]:
                continue
            lo, hi = s - LOOK, s + AFTER
            if lo < 0:
                pending[(uid, s)] = False
                continue
            c0, c1 = max(base, lo), min(end, hi)
            if c0 < c1:
                buf[c0 - lo : c1 - lo] = data[c0 - base : c1 - base]
            if end >= hi:
                pending[(uid, s)] = False
        abs_base += len(block)
        carry = data[-overlap:]
        if not any(pending.values()):
            break

    # Analyze each double window
    # Record offsets of ca_u32 and pa_u32 relative to double (LOOK index)
    layout_ca: dict[int, Counter[int]] = defaultdict(Counter)  # rel -> count across players? per player first
    player_ca_rels: dict[str, Counter[int]] = {}
    player_pa_rels: dict[str, Counter[int]] = {}
    player_pair_rels: dict[str, Counter[tuple[int, int]]] = {}

    for uid, name, cava, pava in PLAYERS:
        ca_b = struct.pack("<I", cava)
        pa_b = struct.pack("<I", pava)
        ca_ctr: Counter[int] = Counter()
        pa_ctr: Counter[int] = Counter()
        pair_ctr: Counter[tuple[int, int]] = Counter()
        lines.append(f"\n### {name} doubles={len(doubles[uid])}")
        for s in doubles[uid]:
            buf = bytes(buffers[(uid, s)])
            # verify uid at LOOK
            if struct.unpack_from("<I", buf, LOOK)[0] != uid:
                lines.append(f"  skip bad window @{s}")
                continue
            # find all ca/pa
            ca_pos = []
            pa_pos = []
            start = 0
            while True:
                j = buf.find(ca_b, start)
                if j < 0:
                    break
                ca_pos.append(j - LOOK)
                start = j + 1
            start = 0
            while True:
                j = buf.find(pa_b, start)
                if j < 0:
                    break
                pa_pos.append(j - LOOK)
                start = j + 1
            for r in ca_pos:
                ca_ctr[r] += 1
            for r in pa_pos:
                pa_ctr[r] += 1
            for cr in ca_pos:
                for pr in pa_pos:
                    if cava == pava and cr == pr:
                        pair_ctr[(cr, pr)] += 1
                    elif cr != pr:
                        pair_ctr[(cr, pr)] += 1
            # hex dump closest ca and pa
            if ca_pos:
                cr = min(ca_pos, key=abs)
                j = LOOK + cr
                lines.append(
                    f"  closest CA@{cr:+d} {buf[max(0,j-8):j+16].hex(' ')}"
                )
            if pa_pos:
                pr = min(pa_pos, key=lambda r: abs(r) if r not in ca_pos or cava != pava else 10**9)
                # for equal, pick second occurrence if any
                cand = [r for r in pa_pos if cava != pava or True]
                if cava == pava and len(pa_pos) >= 2:
                    # pick pair with small separation
                    best = None
                    for a in pa_pos:
                        for b in pa_pos:
                            if 4 <= abs(b - a) <= 32:
                                if best is None or abs(a) + abs(b) < abs(best[0]) + abs(best[1]):
                                    best = (a, b)
                    if best:
                        lines.append(f"  equal-pair candidates ca/pa @{best[0]:+d}/{best[1]:+d}")
                pr = min(pa_pos, key=abs)
                j = LOOK + pr
                lines.append(
                    f"  closest PA@{pr:+d} {buf[max(0,j-8):j+16].hex(' ')}"
                )
        player_ca_rels[name] = ca_ctr
        player_pa_rels[name] = pa_ctr
        player_pair_rels[name] = pair_ctr
        lines.append(f"  top CA rels: {ca_ctr.most_common(8)}")
        lines.append(f"  top PA rels: {pa_ctr.most_common(8)}")
        lines.append(f"  top pairs: {pair_ctr.most_common(8)}")

    # Shared CA rel across players (exact)
    lines.append("\n## Shared CA u32 rel-to-double")
    all_names = [n for _, n, _, _ in PLAYERS]
    ca_union = set()
    for ctr in player_ca_rels.values():
        ca_union |= set(ctr)
    for rel in sorted(ca_union, key=abs):
        hit = [n for n in all_names if rel in player_ca_rels[n]]
        if len(hit) >= 2:
            lines.append(f"  ca@{rel:+d} {hit}")

    lines.append("\n## Shared PA u32 rel-to-double")
    pa_union = set()
    for ctr in player_pa_rels.values():
        pa_union |= set(ctr)
    for rel in sorted(pa_union, key=abs):
        hit = [n for n in all_names if rel in player_pa_rels[n]]
        if len(hit) >= 2:
            lines.append(f"  pa@{rel:+d} {hit}")

    # Shared pair delta
    lines.append("\n## Shared (ca_rel, pa_rel) exact")
    pair_union = set()
    for ctr in player_pair_rels.values():
        pair_union |= set(ctr)
    for pair in sorted(pair_union, key=lambda p: abs(p[0]) + abs(p[1])):
        hit = [n for n in all_names if pair in player_pair_rels[n]]
        if len(hit) == 3:
            cr, pr = pair
            lines.append(f"  LOCK ca@{cr:+d} pa@{pr:+d} Δ={pr-cr:+d} {hit}")
        elif len(hit) == 2:
            cr, pr = pair
            if abs(cr) < 16000 and abs(pr) < 16000:
                lines.append(f"  pair ca@{cr:+d} pa@{pr:+d} Δ={pr-cr:+d} {hit}")

    lines.append(f"\nelapsed={time.perf_counter()-t0:.1f}s")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    for line in lines:
        if any(
            line.startswith(p)
            for p in ("#", "##", "###", "  u32", "  u16", "  ca_", "  pa_", "  Δ=", "  LOCK", "  pair", "  motif", "  closest", "  top", "  equal", "  Assan")
        ) or "near UID" in line or line.startswith("  ca@") or line.startswith("  pa@"):
            log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
