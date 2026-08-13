"""Decode Bandeira's -11k hot-zone 69B records; try full attr×5 assignment.
Also search each double-UID ±64KB for longest run of that player's attr×5 hits.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/attr-hotzone.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}
DOUBLE = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}

# known Band hot hits
BAND_HITS = [264923405, 264923474, 264923543, 264923612, 264923681]


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


def flat(p: dict) -> dict[str, int]:
    out = {}
    for g, attrs in p["attributes"].items():
        for k, v in attrs.items():
            out[f"{g}.{k}"] = int(v)
    return out


def screen_orders(p: dict) -> dict[str, list[tuple[str, int]]]:
    """Common FM screen attribute orders."""
    a = flat(p)
    orders = {}
    if "goalkeeping.aerialReach" in a:
        orders["gk"] = [
            (k, a[k])
            for k in [
                "goalkeeping.aerialReach",
                "goalkeeping.commandOfArea",
                "goalkeeping.communication",
                "goalkeeping.eccentricity",
                "goalkeeping.firstTouch",
                "goalkeeping.handling",
                "goalkeeping.kicking",
                "goalkeeping.oneOnOnes",
                "goalkeeping.passing",
                "goalkeeping.punchingTendency",
                "goalkeeping.reflexes",
                "goalkeeping.rushingOutTendency",
                "goalkeeping.throwing",
            ]
        ]
    else:
        orders["tech"] = [
            (k, a[k])
            for k in [
                "technical.crossing",
                "technical.dribbling",
                "technical.finishing",
                "technical.firstTouch",
                "technical.heading",
                "technical.longShots",
                "technical.marking",
                "technical.passing",
                "technical.tackling",
                "technical.technique",
            ]
        ]
        orders["set"] = [
            (k, a[k])
            for k in [
                "setPieces.corners",
                "setPieces.freeKickTaking",
                "setPieces.longThrows",
                "setPieces.penaltyTaking",
            ]
        ]
    orders["mental"] = [
        (k, a[k])
        for k in [
            "mental.aggression",
            "mental.anticipation",
            "mental.bravery",
            "mental.composure",
            "mental.concentration",
            "mental.decisions",
            "mental.determination",
            "mental.flair",
            "mental.leadership",
            "mental.offTheBall",
            "mental.positioning",
            "mental.teamwork",
            "mental.vision",
            "mental.workRate",
        ]
    ]
    orders["physical"] = [
        (k, a[k])
        for k in [
            "physical.acceleration",
            "physical.agility",
            "physical.balance",
            "physical.jumpingReach",
            "physical.naturalFitness",
            "physical.pace",
            "physical.stamina",
            "physical.strength",
        ]
    ]
    return orders


def find_pack(buf: bytes, vals: list[int], scale: int) -> list[int]:
    needle = bytes(v * scale for v in vals)
    out = []
    start = 0
    while True:
        j = buf.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def assign_x5(window: bytes, attrs: dict[str, int]) -> list[tuple[int, str, int]]:
    """Greedy: for each byte that equals some attr*5 uniquely, record it."""
    inv: dict[int, list[str]] = {}
    for k, v in attrs.items():
        inv.setdefault(v * 5, []).append(k)
    hits = []
    for i, b in enumerate(window):
        if b in inv:
            hits.append((i, inv[b][0] if len(inv[b]) == 1 else f"amb:{inv[b]}", b // 5))
    return hits


def main() -> None:
    lines: list[str] = []

    # Dump 5 Band records aligned on stride 69 with needle at +16 relative in ctx
    lines.append("======== Band 69B hot records ========")
    # From ctx, needle bal/jr/nf starts after 16-byte prefix in the shown ctx;
    # record start guess: hit - 16
    for abs_hit in BAND_HITS:
        rec_start = abs_hit - 16
        rec = extract(rec_start, 69)
        lines.append(f"\nrec@{rec_start} (needle@+16):")
        lines.append(f"  hex: {rec.hex(' ')}")
        lines.append(f"  u8:  {list(rec)}")
        # interpret as possible x5 stream
        x5 = [b / 5 for b in rec]
        lines.append(f"  /5:  {[f'{x:.1f}' if x!=int(x) else str(int(x)) for x in x5]}")

    band = PLAYERS["Patrick Bandeira"]
    orders = screen_orders(band)
    attrs = flat(band)
    # Search 20KB before double for each screen-order pack x1 and x5
    dbl = DOUBLE["Patrick Bandeira"]
    zone = extract(dbl, 2000, before=20000)
    lines.append("\n======== Band screen-order packs in dbl-20KB..+2KB ========")
    for label, pairs in orders.items():
        vals = [v for _, v in pairs]
        for scale in (1, 5):
            offs = find_pack(zone, vals, scale)
            lines.append(
                f"  {label}|x{scale} vals={vals} hits={len(offs)} "
                f"abs={[dbl - 20000 + o for o in offs[:8]]}"
            )
            for o in offs[:3]:
                abs_o = dbl - 20000 + o
                ctx = zone[max(0, o - 8) : o + len(vals) * scale + 8]
                lines.append(f"    @{abs_o} ctx={ctx.hex(' ')}")

    # Full mental+physical+tech concatenated x5?
    lines.append("\n======== Band combined group packs ========")
    for combo in (
        ["tech", "mental", "physical"],
        ["mental", "physical"],
        ["tech", "set", "mental", "physical"],
        ["physical", "mental", "tech"],
    ):
        vals = []
        for g in combo:
            vals.extend(v for _, v in orders[g])
        for scale in (1, 5):
            offs = find_pack(zone, vals, scale)
            lines.append(
                f"  {'+'.join(combo)}|x{scale} len={len(vals)} hits={len(offs)} "
                f"first={[dbl - 20000 + o for o in offs[:5]]}"
            )

    # For each player: longest x5 assignment density in ±64KB of double-UID
    lines.append("\n======== per-player x5 density near double-UID ========")
    for name, dbl in DOUBLE.items():
        p = PLAYERS[name]
        attrs = flat(p)
        win = extract(dbl, 65536, before=65536)
        # sliding density: count x5-matching bytes in 64-byte windows
        x5set = {v * 5 for v in attrs.values()}
        best = (0, -1)  # score, offset
        scores = []
        for i in range(0, len(win) - 64):
            score = sum(1 for b in win[i : i + 64] if b in x5set)
            if score > best[0]:
                best = (score, i)
            if score >= 12:
                scores.append((score, i))
        scores.sort(reverse=True)
        lines.append(f"\n{name}: best_64B_x5_hits={best[0]} at rel_dbl={best[1]-65536:+d}")
        for score, i in scores[:8]:
            abs_i = dbl - 65536 + i
            rel = abs_i - dbl
            chunk = win[i : i + 64]
            assigned = assign_x5(chunk, attrs)
            lines.append(f"  score={score} @{abs_i} rel={rel:+d}")
            lines.append(f"    hex={chunk.hex(' ')}")
            # show unique attributed labels
            labels = [f"+{o}:{lab}={val}" for o, lab, val in assigned[:20]]
            lines.append(f"    map={labels}")

        # exact physical x5 pack near dbl?
        phys = [v for _, v in screen_orders(p)["physical"]]
        for scale in (1, 5):
            offs = find_pack(win, phys, scale)
            lines.append(
                f"  physical|x{scale} hits={len(offs)} "
                f"rel={[dbl - 65536 + o - dbl for o in offs[:10]]}"
            )

    # Seimen GK pack near double
    lines.append("\n======== Seimen GK packs near double ========")
    seimen = PLAYERS["Dennis Seimen"]
    dbl = DOUBLE["Dennis Seimen"]
    win = extract(dbl, 65536, before=65536)
    for label, pairs in screen_orders(seimen).items():
        vals = [v for _, v in pairs]
        for scale in (1, 5):
            offs = find_pack(win, vals, scale)
            lines.append(
                f"  {label}|x{scale} hits={len(offs)} rel={[o - 65536 for o in offs[:8]]}"
            )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # avoid win console encoding issues
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
