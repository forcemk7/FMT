"""Lock corrected attr maps on Band + Müller + Seimen; locate Seimen GK block."""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/attr-model-locked.txt")
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
U16 = {
    "Dennis Seimen": 31020,
    "Patrick Bandeira": 40920,  # also 41140
    "Robert Müller": 38720,
}

# CORRECTED maps (Band+Müller+Seimen)
MENTAL_ORDER = [
    "aggression",
    "anticipation",
    "bravery",
    "vision",
    "decisions",
    "determination",
    "flair",  # was composure
    "leadership",
    "offTheBall",
    "positioning",
    "teamwork",
    "workRate",
    "composure",  # was flair
    "concentration",
]
PHYS_ORDER = [
    "acceleration",
    "agility",
    "balance",
    "pace",  # was jumpingReach
    "stamina",  # was naturalFitness
    "strength",  # was pace
    "jumpingReach",  # was stamina
    "naturalFitness",  # was strength
]
TECHSET_ORDER = [
    "crossing",
    "dribbling",
    "finishing",
    "heading",
    "longShots",
    "longThrows",  # was firstTouch
    "marking",
    "passing",
    "penaltyTaking",
    "freeKickTaking",
    "tackling",
    "technique",
    "firstTouch",  # was longThrows
    "corners",
]
GK_ORDER = [
    "aerialReach",
    "commandOfArea",
    "communication",
    "eccentricity",
    "firstTouch",
    "handling",
    "kicking",
    "oneOnOnes",
    "passing",
    "punchingTendency",
    "reflexes",
    "rushingOutTendency",
    "throwing",
]


def vecs(name: str) -> dict:
    a = PLAYERS[name]["attributes"]
    out = {
        "mental": [int(a["mental"][k]) for k in MENTAL_ORDER],
        "physical": [int(a["physical"][k]) for k in PHYS_ORDER],
    }
    if "setPieces" in a and "crossing" in a.get("technical", {}):
        tech = []
        for k in TECHSET_ORDER:
            src = a["technical"] if k in a["technical"] else a["setPieces"]
            tech.append(int(src[k]))
        out["techset"] = tech
    if "goalkeeping" in a:
        out["gk"] = [int(a["goalkeeping"][k]) for k in GK_ORDER]
        # also GK's sparse technical/set bits
        out["gk_tech"] = [
            int(a["technical"].get("freeKickTaking", -1)),
            int(a["technical"].get("penaltyTaking", -1)),
            int(a["technical"].get("technique", -1)),
        ]
    return out


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


def disp(b: bytes) -> list[int]:
    return [round(x / 5) for x in b]


def score(got, expect, tol=1):
    ok = soft = 0
    n = 0
    for g, e in zip(got, expect):
        if e < 0:
            continue
        n += 1
        d = abs(g - e)
        if d <= tol:
            ok += 1
        else:
            soft += d - tol
    return ok, soft, n


def is_attrish(b: bytes, i: int) -> bool:
    if i + 69 > len(b):
        return False
    if b[i + 34] or b[i + 35] or b[i + 43] != 0x01:
        return False
    return sum(1 for x in b[i : i + 22] if 25 <= x <= 105) >= 12


def find_u16(want: set[int], attrish_only: bool = True):
    found: dict[int, list[tuple[int, bytes]]] = defaultdict(list)
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
                for u16 in want:
                    pat = struct.pack("<H", u16)
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        if j >= 36:
                            ri = j - 36
                            if (not attrish_only) or is_attrish(data, ri):
                                rec = data[ri : ri + 69]
                                if len(rec) == 69:
                                    found[u16].append((chunk_start + ri, bytes(rec)))
                        start = j + 1
                abs_base += len(block)
                carry = data[-80:]
        finally:
            reader.close()
    for u16, rows in list(found.items()):
        seen = set()
        uniq = []
        for a, r in rows:
            if a in seen:
                continue
            seen.add(a)
            uniq.append((a, r))
        found[u16] = uniq
    return found


def main() -> None:
    lines: list[str] = []
    lines.append("CORRECTED Mental: " + ", ".join(MENTAL_ORDER))
    lines.append("CORRECTED Phys:   " + ", ".join(PHYS_ORDER))
    lines.append("CORRECTED Tech:   " + ", ".join(TECHSET_ORDER))
    lines.append("")

    rows = find_u16({31020, 38720, 40920, 41140})
    for u16, rs in sorted(rows.items()):
        lines.append(f"u16={u16} attrish rows={len(rs)}")

    # Validate each player against their u16 (+ Band 41140 secondary)
    assign = {
        "Dennis Seimen": [31020],
        "Patrick Bandeira": [40920, 41140],
        "Robert Müller": [38720],
    }

    for name, u16s in assign.items():
        fx = vecs(name)
        lines.append(f"\n######## {name} ########")
        for u16 in u16s:
            best = None
            for abs_i, rec in rows.get(u16, []):
                ment = disp(rec[0:14])
                phys = disp(rec[14:22])
                tech = disp(rec[55:69])
                mok, ms, mn = score(ment, fx["mental"])
                pok, ps, pn = score(phys, fx["physical"])
                if "techset" in fx:
                    tok, ts, tn = score(tech, fx["techset"])
                    total = mok + pok + tok
                    soft = ms + ps + ts
                    denom = mn + pn + tn
                    extra = f"T{tok}/{tn}"
                else:
                    gok, gs, gn = score(tech[:13], fx["gk"])
                    total = mok + pok + gok
                    soft = ms + ps + gs
                    denom = mn + pn + gn
                    extra = f"Gslot{gok}/{gn}"
                t = (total, soft, abs_i, mok, pok, ment, phys, tech, extra, denom, rec)
                if best is None or ( -t[0], t[1]) < (-best[0], best[1]):
                    best = t
            if not best:
                lines.append(f"  u16={u16}: no rows")
                continue
            total, soft, abs_i, mok, pok, ment, phys, tech, extra, denom, rec = best
            lines.append(
                f"  u16={u16} BEST {total}/{denom} ({100*total/denom:.0f}%) "
                f"soft={soft} @{abs_i} M{mok}/14 P{pok}/8 {extra}"
            )
            lines.append(f"    mental got={ment}")
            lines.append(f"    mental exp={fx['mental']}")
            lines.append(f"    phys   got={phys}")
            lines.append(f"    phys   exp={fx['physical']}")
            lines.append(f"    +55    got={tech}")
            if "techset" in fx:
                lines.append(f"    tech   exp={fx['techset']}")
            else:
                lines.append(f"    gk     exp={fx['gk']}")
            lines.append(
                f"    seal=({rec[22]},{rec[24]}) u16LE={struct.unpack_from('<H', rec, 36)[0]} "
                f"b23={rec[23]} mid={list(rec[25:34])}"
            )
            # dump mid/tail for GK hunt
            lines.append(f"    bytes+22..54: {list(rec[22:55])}")
            lines.append(f"    bytes+44..68: {list(rec[44:69])} disp={disp(rec[44:69])}")

    # ---- Seimen GK location hunt ----
    lines.append("\n======== Seimen GK placement relative to card ========")
    fx = vecs("Dennis Seimen")
    gk = fx["gk"]
    seimen_rows = rows.get(31020, [])
    # Take a Ment/Phys perfect-ish row near double
    near = [
        (abs_i, rec)
        for abs_i, rec in seimen_rows
        if abs(abs_i - DOUBLE["Dennis Seimen"]) < 20000
    ]
    lines.append(f"Seimen u16 rows near double (±20KB): {len(near)}")
    if not near:
        near = seimen_rows[:5]

    # For each card, scan offsets -200..+200 for ordered GK match (tol1)
    for abs_i, rec in near[:3]:
        lines.append(f"\n-- card @{abs_i} --")
        # expand window around card
        win = extract(abs_i, 400, before=200)
        base = abs_i - 200
        hits = []
        for off in range(0, len(win) - 13):
            got = disp(win[off : off + 13])
            ok, soft, n = score(got, gk, 1)
            if ok >= 11:
                hits.append((ok, soft, base + off, got, list(win[off : off + 13])))
        hits.sort(key=lambda t: (-t[0], t[1], abs(t[2] - abs_i)))
        lines.append(f"  GK ordered ≥11/13 near card: {len(hits)}")
        for ok, soft, a, got, raw in hits[:12]:
            lines.append(
                f"    @{a} rel_card={a-abs_i:+d} G{ok}/13 soft={soft} got={got}"
            )
            lines.append(f"      raw={raw}")

        # also try 14-byte including possible trailing set piece
        hits14 = []
        for off in range(0, len(win) - 14):
            got = disp(win[off : off + 14])
            ok, soft, n = score(got[:13], gk, 1)
            if ok >= 12:
                hits14.append((ok, soft, base + off, got))
        hits14.sort(key=lambda t: (-t[0], t[1], abs(t[2] - abs_i)))
        for ok, soft, a, got in hits14[:5]:
            lines.append(f"    14B @{a} rel={a-abs_i:+d} G{ok}/13 got14={got}")

    # Broader: search GK ordered multiset in ±64KB of Seimen double
    lines.append("\n======== Seimen GK ordered in dbl±64KB ========")
    win = extract(DOUBLE["Dennis Seimen"], 65536, before=65536)
    base = DOUBLE["Dennis Seimen"] - 65536
    hits = []
    for i in range(0, len(win) - 13):
        got = disp(win[i : i + 13])
        ok, soft, n = score(got, gk, 1)
        if ok >= 12:
            hits.append((ok, soft, base + i, got, list(win[i : i + 13])))
    hits.sort(key=lambda t: (-t[0], t[1]))
    lines.append(f"ordered G≥12/13: {len(hits)}")
    for ok, soft, a, got, raw in hits[:20]:
        lines.append(f"  @{a} rel={a-DOUBLE['Dennis Seimen']:+d} G{ok}/13 soft={soft}")
        lines.append(f"    got={got}")
        lines.append(f"    raw={raw}")
        # context: is this inside a 31020 card?
        for off in range(-60, 5):
            li = a - base + off
            if 0 <= li <= len(win) - 69 and is_attrish(win, li):
                u16 = struct.unpack_from("<H", win, li + 36)[0]
                if u16 == 31020 or off > -40:
                    lines.append(
                        f"    attrish@card+{off} u16={u16} seal=({win[li+22]},{win[li+24]})"
                    )

    # Try common GK internal orders (permutations of known groups)
    lines.append("\n======== GK order probe on +44..+68 and other slots ========")
    # sample one good Seimen card's full byte disp
    sample = None
    for abs_i, rec in near:
        ment = disp(rec[0:14])
        phys = disp(rec[14:22])
        mok, _, _ = score(ment, fx["mental"])
        pok, _, _ = score(phys, fx["physical"])
        if mok >= 13 and pok >= 7:
            sample = (abs_i, rec)
            break
    if sample is None and near:
        sample = near[0]
    if sample:
        abs_i, rec = sample
        lines.append(f"sample card @{abs_i}")
        lines.append(f"full69 disp={disp(rec)}")
        lines.append(f"raw69={list(rec)}")
        # score every 13-byte window inside rec against GK
        for i in range(0, 69 - 12):
            got = disp(rec[i : i + 13])
            ok, soft, _ = score(got, gk, 1)
            if ok >= 8:
                lines.append(f"  in-card +{i} G{ok}/13 soft={soft} {got}")
        # also try all permutations is impossible; try sorting bags only
        # Search nearby ±2KB for bags ≥12 unordered contiguous
        win = extract(abs_i, 2048, before=2048)
        base = abs_i - 2048
        bag_hits = []
        gk_sorted = sorted(gk)
        for i in range(len(win) - 13):
            got = disp(win[i : i + 13])
            ok = sum(1 for a, b in zip(sorted(got), gk_sorted) if abs(a - b) <= 1)
            if ok >= 12:
                # ordered score too
                ook, soft, _ = score(got, gk, 1)
                bag_hits.append((ok, ook, soft, base + i, got))
        bag_hits.sort(key=lambda t: (-t[1], -t[0], t[2], abs(t[3] - abs_i)))
        lines.append(f"bag≥12 near sample: {len(bag_hits)}")
        for ok, ook, soft, a, got in bag_hits[:15]:
            lines.append(
                f"  @{a} rel={a-abs_i:+d} bag{ok}/13 ord{ook}/13 soft={soft} {got}"
            )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
