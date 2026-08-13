"""Hunt Band technical (+ set-piece) attrs near 69B strip and double-UID.

Tries screen-order packs at ×1 and ×5, fuzzy ±1/±2 display, and
sliding density of tech×5 values inside/near the 69B cluster.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/band69-tech-hunt.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}

BAND = "Patrick Bandeira"
DBL = 264934792
# Known 69B cluster around Band (from locked spike)
CLUSTER_LO = 264923320
CLUSTER_HI = 264924400
STRIDE = 69

TECH_KEYS = [
    "crossing",
    "dribbling",
    "finishing",
    "firstTouch",
    "heading",
    "longShots",
    "marking",
    "passing",
    "tackling",
    "technique",
]
SET_KEYS = ["corners", "freeKickTaking", "longThrows", "penaltyTaking"]

# Candidate tech orders
TECH_ORDERS = {
    "screen": TECH_KEYS[:],
    "alpha": sorted(TECH_KEYS),
    # drop finishing early / defensive bias
    "def_bias": [
        "marking",
        "tackling",
        "heading",
        "passing",
        "firstTouch",
        "technique",
        "crossing",
        "dribbling",
        "longShots",
        "finishing",
    ],
    "ment_adj": [  # often listed after mentals in dumps
        "crossing",
        "dribbling",
        "finishing",
        "heading",
        "longShots",
        "marking",
        "passing",
        "tackling",
        "technique",
        "firstTouch",
    ],
}


def extract(abs_target: int, length: int, before: int = 0) -> bytes:
    start = abs_target - before
    end = abs_target + length
    abs_base = 0
    carry = b""
    buf = bytearray()
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                chunk_start = abs_base - len(carry)
                if chunk_start < end and abs_base + len(block) > start:
                    already = len(buf)
                    want = start + already
                    lo = max(0, start - chunk_start, want - chunk_start)
                    hi = min(len(data), end - chunk_start)
                    if lo < hi:
                        buf.extend(data[lo:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= before + length:
                    break
        finally:
            reader.close()
    return bytes(buf)


def vals(group: str, keys: list[str]) -> list[int]:
    a = PLAYERS[BAND]["attributes"][group]
    return [int(a[k]) for k in keys]


def find_fuzzy(buf: bytes, expect: list[int], scale: int, tol: int) -> list[int]:
    """expect = display values; match scale*expect with per-byte ±tol."""
    n = len(expect)
    out = []
    targets = [v * scale for v in expect]
    for i in range(len(buf) - n + 1):
        if all(abs(buf[i + j] - targets[j]) <= tol for j in range(n)):
            out.append(i)
    return out


def density_x5(buf: bytes, displays: list[int], win: int = 32) -> list[tuple[int, int]]:
    """Score windows by how many bytes equal some display*5 (±1)."""
    targets = set()
    for d in displays:
        for t in range(d * 5 - 1, d * 5 + 2):
            if 0 <= t <= 255:
                targets.add(t)
    scored = []
    for i in range(0, max(0, len(buf) - win)):
        score = sum(1 for b in buf[i : i + win] if b in targets)
        if score >= 8:
            scored.append((score, i))
    scored.sort(reverse=True)
    return scored[:20]


def score_order(buf: bytes, off: int, expect: list[int], scale: int, tol: int) -> tuple[int, int]:
    if off + len(expect) > len(buf):
        return 0, 10**9
    ok = 0
    soft = 0
    for j, d in enumerate(expect):
        got = buf[off + j]
        exp = d * scale
        if scale == 1:
            # compare as display directly
            diff = abs(got - d)
        else:
            diff = abs(round(got / scale) - d) if scale == 5 else abs(got - exp)
            # also allow raw ±tol on ×5
            diff_raw = abs(got - exp)
            diff = min(diff, diff_raw) if scale == 5 else diff
        if scale == 5:
            diff = abs(got - exp)
        if diff <= tol:
            ok += 1
        else:
            soft += diff - tol
    return ok, soft


def main() -> None:
    lines: list[str] = []
    tech = vals("technical", TECH_KEYS)
    sett = vals("setPieces", SET_KEYS)
    lines.append(f"Band tech display: {dict(zip(TECH_KEYS, tech))}")
    lines.append(f"Band set  display: {dict(zip(SET_KEYS, sett))}")
    lines.append(f"tech×5: {[v*5 for v in tech]}")
    lines.append(f"set×5:  {[v*5 for v in sett]}")

    # Window: cluster and past double
    before = DBL - (CLUSTER_LO - 2000)
    after = 8000
    zone = extract(DBL, after, before=before)
    z0 = DBL - before
    lines.append(f"\nzone abs=[{z0}..{z0+len(zone)}) len={len(zone)}")

    # Exact / fuzzy packs for each order
    lines.append("\n======== pack search in zone ========")
    for oname, keys in TECH_ORDERS.items():
        expect = vals("technical", keys)
        for scale in (1, 5):
            for tol in (0, 1, 2):
                hits = find_fuzzy(zone, expect, scale, tol)
                if hits:
                    abs_hits = [z0 + h for h in hits[:8]]
                    lines.append(
                        f"  {oname}|x{scale}|tol={tol}: n={len(hits)} first={abs_hits}"
                    )
                    for h in hits[:3]:
                        chunk = zone[h : h + 10]
                        lines.append(f"    @{z0+h}: {list(chunk)}")

    # set alone / tech+set
    lines.append("\n======== set / tech+set ========")
    for scale in (1, 5):
        for tol in (0, 1, 2):
            hits = find_fuzzy(zone, sett, scale, tol)
            if hits:
                lines.append(f"  set|x{scale}|tol={tol}: n={len(hits)} @{[z0+h for h in hits[:6]]}")
        combo = tech + sett
        hits = find_fuzzy(zone, combo, scale, 2)
        lines.append(f"  tech+set|x{scale}|tol=2: n={len(hits)} first={[z0+h for h in hits[:4]]}")
        combo2 = sett + tech
        hits = find_fuzzy(zone, combo2, scale, 2)
        lines.append(f"  set+tech|x{scale}|tol=2: n={len(hits)} first={[z0+h for h in hits[:4]]}")

    # Inside each 69B row: scan all offsets for best tech placement
    lines.append("\n======== tech placement inside Band 69B rows ========")
    for abs_rec in range(CLUSTER_LO, CLUSTER_HI, STRIDE):
        rec = extract(abs_rec, STRIDE)
        if len(rec) < 69 or rec[22] != 0x07 or rec[24] != 0x9C:
            continue
        best = []
        for oname, keys in TECH_ORDERS.items():
            expect = vals("technical", keys)
            for scale in (1, 5):
                for off in range(0, 69 - len(expect) + 1):
                    ok, soft = score_order(rec, off, expect, scale, tol=2 if scale == 5 else 0)
                    if ok >= 7:
                        best.append((ok, soft, oname, scale, off))
        best.sort(key=lambda t: (-t[0], t[1]))
        if best:
            lines.append(f"@{abs_rec}: top {best[:5]}")
            ok, soft, oname, scale, off = best[0]
            expect = vals("technical", TECH_ORDERS[oname])
            got = list(rec[off : off + 10])
            lines.append(f"  best {oname}|x{scale}|+{off} ok={ok} soft={soft} got={got}")

    # Look just AFTER the 22-byte attr head / after +54 tail for tech
    lines.append("\n======== adjacent bytes to 69B head/tail ========")
    rec0 = extract(264923389, 200, before=40)
    lines.append(f"pre40+rec69+post: focusing tech density")
    # region around one record
    dens = density_x5(rec0, tech, win=16)
    lines.append(f"tech×5 density in pre+rec window top: {dens[:10]}")
    for score, off in dens[:5]:
        abs_o = 264923389 - 40 + off
        chunk = rec0[off : off + 16]
        lines.append(f"  score={score} @{abs_o}: {list(chunk)} /5={[round(b/5) for b in chunk]}")

    # Wider: ±64KB density peaks
    lines.append("\n======== ±64KB density peaks for tech×5 values ========")
    wide = extract(DBL, 65536, before=65536)
    dens = density_x5(wide, tech, win=16)
    for score, off in dens[:12]:
        abs_o = DBL - 65536 + off
        chunk = wide[off : off + 16]
        # also try score screen order at this off
        ok5, soft5 = score_order(wide, off, tech, 5, 2)
        lines.append(
            f"  dens={score} @{abs_o} rel={abs_o-DBL:+d} ok_screen×5={ok5}/10 "
            f"raw={list(chunk)} disp={[round(b/5) for b in chunk]}"
        )

    # Distinctive tech fingerprint: finishing=7, penalty=5, crossing=8 (low)
    lines.append("\n======== distinctive low-tech fingerprints ========")
    # finishing×5=35, penalties×5=25, crossing×5=40 — rare combo near marking=85
    needles = [
        ("fin_pen", bytes([35, 25])),
        ("cro_fin", bytes([40, 35])),
        ("fin_ft", bytes([35, 60])),
        ("mar_pas_tack", bytes([85, 65, 70])),
        ("pas_tack_tec", bytes([65, 70, 75])),
        ("mar_pas_tack_tec", bytes([85, 65, 70, 75])),
    ]
    for label, pat in needles:
        # fuzzy ±1
        hits = []
        for i in range(len(wide) - len(pat)):
            if all(abs(wide[i + j] - pat[j]) <= 1 for j in range(len(pat))):
                hits.append(DBL - 65536 + i)
        lines.append(f"  {label} ±1: n={len(hits)} first={hits[:8]}")
        for h in hits[:3]:
            rel = h - DBL
            ctx = extract(h, 24, before=8)
            lines.append(f"    @{h} rel={rel:+d} ctx={list(ctx)}")

    # Double-UID body again as tech×5?
    lines.append("\n======== double-UID body[+54..] vs tech×5 ========")
    body = extract(DBL, 200)[54:120]
    lines.append(f"body: {list(body)}")
    for oname, keys in TECH_ORDERS.items():
        expect = vals("technical", keys)
        for off in range(0, len(body) - 10 + 1):
            ok, soft = score_order(body, off, expect, 5, 2)
            if ok >= 6:
                lines.append(f"  {oname} @body+{off}: ok={ok}/10 soft={soft} got={list(body[off:off+10])}")

    lines.append(
        """
======== NOTES ========
If tech packs are absent near the 69B mental+phys card, technicals
likely live in a sibling table (or packed differently). Distinctive
low finishing/penalties help reject false highs.
"""
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
