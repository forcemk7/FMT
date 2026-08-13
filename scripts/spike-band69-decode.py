"""Hard-way decode: Band 69B hot records as 1-100 attrs (display = round(v/5)).

Goals:
1) Best L1 assignment of fixture groups to record prefix with tolerance
2) Structural signature → Seimen / Müller analogues near their doubles
3) Report locked map or precise mismatches
"""

from __future__ import annotations

import json
import struct
from itertools import permutations
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/band69-decode.txt")
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
BAND_REC0 = 264923389
STRIDE = 69
N_RECS = 5


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


def stream_blocks(chunk=8 * 1024 * 1024):
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = reader.read(chunk)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            reader.close()


def flat(p: dict) -> dict[str, int]:
    out = {}
    for g, attrs in p["attributes"].items():
        for k, v in attrs.items():
            out[f"{g}.{k}"] = int(v)
    return out


def groups(p: dict) -> dict[str, list[tuple[str, int]]]:
    a = flat(p)
    g: dict[str, list[tuple[str, int]]] = {}
    if "goalkeeping.aerialReach" in a:
        g["gk"] = [
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
        g["tech"] = [
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
        g["set"] = [
            (k, a[k])
            for k in [
                "setPieces.corners",
                "setPieces.freeKickTaking",
                "setPieces.longThrows",
                "setPieces.penaltyTaking",
            ]
        ]
    g["mental"] = [
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
    g["physical"] = [
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
    return g


def score_window(buf: bytes, off: int, pairs: list[tuple[str, int]], tol: int) -> tuple[int, list[str]]:
    """Return (l1_cost, per-field notes). Cost = sum max(0, |byte - expect*5| - tol)."""
    if off + len(pairs) > len(buf):
        return 10**9, []
    cost = 0
    notes = []
    for i, (name, disp) in enumerate(pairs):
        expect = disp * 5
        got = buf[off + i]
        diff = abs(got - expect)
        soft = max(0, diff - tol)
        cost += soft
        ok = "OK" if diff <= tol else f"d{diff}"
        notes.append(f"{name.split('.')[-1]}={disp} expect={expect} got={got} ({ok})")
    return cost, notes


def best_place(buf: bytes, pairs: list[tuple[str, int]], tol: int, max_off: int = 40) -> tuple[int, int, list[str]]:
    best = (10**9, -1, [])
    for off in range(0, min(max_off, len(buf) - len(pairs) + 1)):
        c, notes = score_window(buf, off, pairs, tol)
        if c < best[0]:
            best = (c, off, notes)
    return best


def main() -> None:
    lines: list[str] = []
    band = PLAYERS["Patrick Bandeira"]
    bg = groups(band)
    recs = [extract(BAND_REC0 + i * STRIDE, STRIDE) for i in range(N_RECS)]
    rec = recs[0]

    lines.append("======== Band rec0 structural map ========")
    lines.append(f"abs={BAND_REC0} stride={STRIDE}")
    lines.append(f"hex: {rec.hex(' ')}")
    # stable across snapshots
    stab = []
    for i in range(STRIDE):
        vals = {r[i] for r in recs}
        if len(vals) == 1:
            stab.append(i)
    lines.append(f"stable byte offs ({len(stab)}): {stab}")
    lines.append(f"varying: {[i for i in range(STRIDE) if i not in stab]}")

    # Mark regions
    lines.append("\nHypothesis regions:")
    lines.append("  +0..+21  candidate attr×100 stream")
    lines.append("  +22      const 0x07")
    lines.append("  +23      varies (snapshot id?)")
    lines.append("  +24      const 0x9c")
    lines.append("  +25..+33 varying mid")
    lines.append("  +34..+35 00 00")
    lines.append(f"  +36..+37 player const u16={struct.unpack_from('<H', rec, 36)[0]} (0x{struct.unpack_from('<H', rec, 36)[0]:04X})")
    lines.append("  +38..+42 pad + 01")
    lines.append(f"  +43..+54 small-run: {list(rec[43:55])}")
    lines.append(f"  +55..+68 tail: {list(rec[55:])}")

    lines.append("\n======== group placement (tol=0 and tol=2) ========")
    for tol in (0, 2):
        lines.append(f"\n--- tol=±{tol} on expect=disp*5 ---")
        for gname, pairs in bg.items():
            cost, off, notes = best_place(rec, pairs, tol)
            lines.append(f"  {gname}: best_off=+{off} L1_soft={cost}/{len(pairs)}")
            for n in notes:
                lines.append(f"    {n}")

    # Try concatenations of group orders
    lines.append("\n======== concatenated group-order search (tol=2) ========")
    names = list(bg.keys())
    best_combo = (10**9, "", -1, {})
    for order in permutations(names):
        pairs = []
        for g in order:
            pairs.extend(bg[g])
        for off in range(0, 23 - 0):  # keep attrs in first ~22-36 bytes
            if off + len(pairs) > 40:
                continue
            c, notes = score_window(rec, off, pairs, 2)
            if c < best_combo[0]:
                detail = {}
                pos = off
                for g in order:
                    detail[g] = pos
                    pos += len(bg[g])
                best_combo = (c, "+".join(order), off, detail)
    lines.append(
        f"best: order={best_combo[1]} off=+{best_combo[2]} softL1={best_combo[0]} layout={best_combo[3]}"
    )
    # dump that assignment
    if best_combo[1]:
        order = best_combo[1].split("+")
        pairs = []
        for g in order:
            pairs.extend(bg[g])
        _, notes = score_window(rec, best_combo[2], pairs, 2)
        ok_n = sum(1 for n in notes if "(OK)" in n)
        lines.append(f"  matched OK {ok_n}/{len(notes)}")
        for n in notes:
            lines.append(f"  {n}")

    # Physical alone at every offset with field diffs
    lines.append("\n======== physical alone all offsets tol=2 ========")
    for off in range(0, 25):
        c, notes = score_window(rec, off, bg["physical"], 2)
        ok = sum(1 for n in notes if "(OK)" in n)
        if ok >= 5 or c <= 10:
            lines.append(f"  +{off}: soft={c} ok={ok}/8")
            for n in notes:
                lines.append(f"    {n}")

    # Mental alone
    lines.append("\n======== mental alone offsets with ok>=10 ========")
    for off in range(0, 20):
        c, notes = score_window(rec, off, bg["mental"], 2)
        ok = sum(1 for n in notes if "(OK)" in n)
        if ok >= 8:
            lines.append(f"  +{off}: soft={c} ok={ok}/14")
            for n in notes:
                lines.append(f"    {n}")

    # --- Find analogues via structural signature ---
    # Stable across Band snaps: 07 at +22, 9c at +24, then later b4 a0 at +36
    # Better: search for Band phys triple 5a 55 50 and inspect; also player const u16
    band_u16 = struct.unpack_from("<H", rec, 36)[0]
    lines.append(f"\n======== analogue hunt (sig around 07 xx 9c … u16={band_u16}) ========")

    # Build distinctive needles per player: physical mid3 on 1-100
    needles = {}
    for name, p in PLAYERS.items():
        phys = groups(p)["physical"]
        # bal, jr, nf as ×5 exact (Band proved)
        bal = next(v for k, v in phys if k.endswith("balance"))
        jr = next(v for k, v in phys if k.endswith("jumpingReach"))
        nf = next(v for k, v in phys if k.endswith("naturalFitness"))
        needles[name] = bytes([bal * 5, jr * 5, nf * 5])
        lines.append(f"  {name} bal/jr/nf x5 needle={list(needles[name])}")

    hits: dict[str, list[int]] = {n: [] for n in needles}
    abs_base = 0
    carry = b""
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
                for name, pat in needles.items():
                    if len(hits[name]) >= 30:
                        continue
                    start = 0
                    while len(hits[name]) < 30:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        abs_hit = chunk_start + j
                        if abs_hit >= abs_base:
                            # require nearby 07 ?? 9c within -20..+10 of needle
                            lo = max(0, j - 20)
                            hi = min(len(data), j + 12)
                            win = data[lo:hi]
                            ok_sig = False
                            for k in range(len(win) - 2):
                                if win[k] == 0x07 and win[k + 2] == 0x9C:
                                    ok_sig = True
                                    break
                            if ok_sig:
                                hits[name].append(abs_hit)
                        start = j + 1
                abs_base += len(block)
                carry = data[-32:]
        finally:
            reader.close()

    for name, hs in hits.items():
        dbl = DOUBLE[name]
        lines.append(f"\n{name}: signatured bal/jr/nf hits={len(hs)}")
        for h in hs[:12]:
            rel = h - dbl
            # record start guess = needle - 16 (Band calibrated)
            r0 = h - 16
            blob = extract(r0, 69)
            u16 = struct.unpack_from("<H", blob, 36)[0] if len(blob) >= 38 else -1
            lines.append(
                f"  needle@{h} dbl_rel={rel:+d} rec?@{r0} +36_u16={u16} "
                f"head22={list(blob[:22])}"
            )
            # score physical at +14
            pg = groups(PLAYERS[name])["physical"]
            c0, n0 = score_window(blob, 14, pg, 2)
            ok0 = sum(1 for x in n0 if "(OK)" in x)
            c1, n1 = score_window(blob, 0, groups(PLAYERS[name])["mental"], 2)
            ok1 = sum(1 for x in n1 if "(OK)" in x)
            lines.append(f"    phys@+14 soft={c0} ok={ok0}/8; mental@+0 soft={c1} ok={ok1}/14")

    # Compare Band fixture display vs round(byte/5) if we assume mental@0 + phys@14
    lines.append("\n======== assumed layout mental@0 (14) + ??? + phys@14 (8) ========")
    lines.append("(Band: bytes 0-13 vs mental, 14-21 vs physical)")
    ment = bg["mental"]
    phys = bg["physical"]
    for i, (name, disp) in enumerate(ment):
        got = rec[i]
        lines.append(
            f"  M[{i}] {name.split('.')[-1]}: fixture={disp} byte={got} round/5={round(got/5)} raw/5={got/5:.2f}"
        )
    for i, (name, disp) in enumerate(phys):
        got = rec[14 + i]
        lines.append(
            f"  P[{i}] {name.split('.')[-1]}: fixture={disp} byte={got} round/5={round(got/5)} raw/5={got/5:.2f}"
        )

    # tech at negative offsets before record? extend left
    lines.append("\n======== 32 bytes BEFORE rec0 (tech candidate?) ========")
    pre = extract(BAND_REC0, 0, before=40)
    lines.append(f"pre40: {list(pre)}")
    if "tech" in bg:
        for off in range(0, 30):
            # off relative to pre start = BAND_REC0-40
            c, notes = score_window(pre + rec, off, bg["tech"], 2)
            ok = sum(1 for n in notes if "(OK)" in n)
            if ok >= 6:
                lines.append(f"  tech in pre+rec @abs_off {BAND_REC0-40+off}: ok={ok}/10 soft={c}")
                for n in notes:
                    lines.append(f"    {n}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
