"""Dig Müller u16=38720 + hunt Seimen GK attr cards.

1) Fix: validate Müller on 38720 (missed by candidate max bug).
2) Score permutations / known orders against fixture.
3) Search Seimen: shaped 69B wider; also raw GK multiset near double.
4) Try alternate seal bytes around Seimen double.
"""

from __future__ import annotations

import itertools
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/attr-mull-seimen.txt")
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

MENTAL_ORDER = [
    "aggression",
    "anticipation",
    "bravery",
    "vision",
    "decisions",
    "determination",
    "composure",
    "leadership",
    "offTheBall",
    "positioning",
    "teamwork",
    "workRate",
    "flair",
    "concentration",
]
PHYS_ORDER = [
    "acceleration",
    "agility",
    "balance",
    "jumpingReach",
    "naturalFitness",
    "pace",
    "stamina",
    "strength",
]
TECHSET_ORDER = [
    "crossing",
    "dribbling",
    "finishing",
    "heading",
    "longShots",
    "firstTouch",
    "marking",
    "passing",
    "penaltyTaking",
    "freeKickTaking",
    "tackling",
    "technique",
    "longThrows",
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


def fx_vecs(name: str) -> dict:
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


def is_rec(b: bytes, i: int, b22: int = 0x07, b24: int = 0x9C) -> bool:
    if i + 69 > len(b):
        return False
    if b[i + 22] != b22 or b[i + 24] != b24:
        return False
    if b[i + 34] != 0 or b[i + 35] != 0:
        return False
    if b[i + 43] != 0x01:
        return False
    mid = sum(1 for x in b[i : i + 22] if 25 <= x <= 105)
    return mid >= 12


def disp(raw: bytes) -> list[int]:
    return [round(x / 5) for x in raw]


def score(got, expect, tol=1):
    ok = soft = n = 0
    for g, e in zip(got, expect):
        n += 1
        d = abs(g - e)
        if d <= tol:
            ok += 1
        else:
            soft += d - tol
    return ok, soft


def parse(rec: bytes) -> dict:
    return {
        "mental": disp(rec[0:14]),
        "physical": disp(rec[14:22]),
        "u16": struct.unpack_from("<H", rec, 36)[0],
        "techset": disp(rec[55:69]),
        "rec": rec,
    }


def find_u16_global(want: set[int]) -> dict[int, list[tuple[int, dict]]]:
    found: dict[int, list[tuple[int, dict]]] = defaultdict(list)
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
                            if is_rec(data, ri):
                                rec = data[ri : ri + 69]
                                if len(rec) == 69:
                                    found[u16].append((chunk_start + ri, parse(rec)))
                        start = j + 1
                abs_base += len(block)
                carry = data[-80:]
        finally:
            reader.close()
    # dedupe
    for u16, rows in list(found.items()):
        seen = set()
        uniq = []
        for a, p in rows:
            if a in seen:
                continue
            seen.add(a)
            uniq.append((a, p))
        found[u16] = uniq
    return found


def main() -> None:
    lines: list[str] = []
    mull = fx_vecs("Robert Müller")
    seim = fx_vecs("Dennis Seimen")
    band = fx_vecs("Patrick Bandeira")

    # ---- Müller 38720 ----
    lines.append("======== Müller u16=38720 global ========")
    rows_map = find_u16_global({38720, 40920, 41140})
    for u16, rows in sorted(rows_map.items()):
        lines.append(f"u16={u16} n={len(rows)}")

    mrows = rows_map.get(38720, [])
    best = None
    for abs_i, p in mrows:
        mok, ms = score(p["mental"], mull["mental"])
        pok, ps = score(p["physical"], mull["physical"])
        tok, ts = score(p["techset"], mull["techset"])
        total = mok + pok + tok
        soft = ms + ps + ts
        t = (total, soft, abs_i, mok, pok, tok, p)
        if best is None or t[:2] < (best[0] * -1, best[1]) and False:
            pass
        if best is None or (-total, soft) < (-best[0], best[1]):
            best = (total, soft, abs_i, mok, pok, tok, p)
    if best:
        total, soft, abs_i, mok, pok, tok, p = best
        lines.append(
            f"BEST Müller@38720: {total}/36 soft={soft} @{abs_i} "
            f"M{mok}/14 P{pok}/8 T{tok}/14"
        )
        lines.append(f"  got_m={p['mental']}")
        lines.append(f"  exp_m={mull['mental']}")
        lines.append(f"  got_p={p['physical']}")
        lines.append(f"  exp_p={mull['physical']}")
        lines.append(f"  got_t={p['techset']}")
        lines.append(f"  exp_t={mull['techset']}")
        # field-level diffs
        lines.append("  mental diffs:")
        for i, (g, e, n) in enumerate(zip(p["mental"], mull["mental"], MENTAL_ORDER)):
            if abs(g - e) > 1:
                lines.append(f"    +{i} {n}: got={g} exp={e} d={g-e:+d}")
        lines.append("  phys diffs:")
        for i, (g, e, n) in enumerate(zip(p["physical"], mull["physical"], PHYS_ORDER)):
            if abs(g - e) > 1:
                lines.append(f"    +{14+i} {n}: got={g} exp={e} d={g-e:+d}")
        lines.append("  tech diffs:")
        for i, (g, e, n) in enumerate(zip(p["techset"], mull["techset"], TECHSET_ORDER)):
            if abs(g - e) > 1:
                lines.append(f"    +{55+i} {n}: got={g} exp={e} d={g-e:+d}")

        # Try swap firstTouch <-> longThrows on tech
        t2 = list(p["techset"])
        t2[5], t2[12] = t2[12], t2[5]
        tok2, _ = score(t2, mull["techset"])
        lines.append(f"  after swap FT<->LT: T{tok2}/14  tech={t2}")

        # Try all phys permutations of last 4 (NF/Pace/Sta/Str region) — 24
        lines.append("  phys last4 perms (top5):")
        ranked = []
        base = p["physical"][:4]
        for perm in itertools.permutations(p["physical"][4:]):
            got = base + list(perm)
            ok, soft = score(got, mull["physical"], 1)
            ranked.append((ok, soft, got, perm))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        for ok, soft, got, perm in ranked[:5]:
            lines.append(f"    P{ok}/8 soft={soft} last4={list(perm)} full={got}")

        # Also: is this actually Band? score vs Band
        bm, _ = score(p["mental"], band["mental"])
        bp, _ = score(p["physical"], band["physical"])
        bt, _ = score(p["techset"], band["techset"])
        lines.append(f"  same card vs Band: M{bm}/14 P{bp}/8 T{bt}/14")

    # Multiset distance: maybe order wrong but values are Müller's
    if best:
        p = best[6]

        def bag_l1(got, expect):
            # optimal assignment cost of sorted
            return sum(abs(a - b) for a, b in zip(sorted(got), sorted(expect)))

        lines.append(
            f"  multiset L1 mental={bag_l1(p['mental'], mull['mental'])} "
            f"phys={bag_l1(p['physical'], mull['physical'])} "
            f"tech={bag_l1(p['techset'], mull['techset'])}"
        )
        lines.append(
            f"  sorted got_p={sorted(p['physical'])} exp_p={sorted(mull['physical'])}"
        )
        lines.append(
            f"  sorted got_t={sorted(p['techset'])} exp_t={sorted(mull['techset'])}"
        )

    # ---- Seimen: widen shaped search ----
    lines.append("\n======== Seimen shaped cards wider windows ========")
    for before, after in [(256 * 1024, 256 * 1024), (1024 * 1024, 64 * 1024)]:
        win = extract(DOUBLE["Dennis Seimen"], after, before=before)
        base = DOUBLE["Dennis Seimen"] - before
        hits = []
        for i in range(0, len(win) - 69):
            if is_rec(win, i):
                p = parse(win[i : i + 69])
                mok, _ = score(p["mental"], seim["mental"])
                pok, _ = score(p["physical"], seim["physical"])
                gok, _ = score(p["techset"][:13], seim["gk"])
                hits.append((mok + pok + gok, i, p))
        hits.sort(reverse=True)
        lines.append(f"window -{before}/+{after}: shaped={len(hits)}")
        for total, i, p in hits[:5]:
            mok, _ = score(p["mental"], seim["mental"])
            pok, _ = score(p["physical"], seim["physical"])
            gok, _ = score(p["techset"][:13], seim["gk"])
            lines.append(
                f"  @{base+i} u16={p['u16']} total~{total} M{mok}/14 P{pok}/8 G{gok}/13"
            )
            lines.append(f"    m={p['mental']} p={p['physical']} t={p['techset']}")

    # ---- Seimen: alternate seal bytes ----
    lines.append("\n======= Seimen alternate seals (b22,b24) near ±256KB =======")
    win = extract(DOUBLE["Dennis Seimen"], 256 * 1024, before=256 * 1024)
    base = DOUBLE["Dennis Seimen"] - 256 * 1024
    # count frequency of (b22,b24) among candidates with zero pads + 01 + attr-like front
    seal_hits: Counter = Counter()
    good_for_attr = []
    for i in range(0, len(win) - 69):
        if win[i + 34] or win[i + 35] or win[i + 43] != 0x01:
            continue
        mid = sum(1 for x in win[i : i + 22] if 25 <= x <= 105)
        if mid < 12:
            continue
        seal = (win[i + 22], win[i + 24])
        seal_hits[seal] += 1
        pment = disp(win[i : i + 14])
        pphys = disp(win[i + 14 : i + 22])
        ptech = disp(win[i + 55 : i + 69])
        mok, _ = score(pment, seim["mental"])
        pok, _ = score(pphys, seim["physical"])
        gok, _ = score(ptech[:13], seim["gk"])
        if mok + pok + gok >= 20:
            u16 = struct.unpack_from("<H", win, i + 36)[0]
            good_for_attr.append(
                (mok + pok + gok, base + i, seal, u16, mok, pok, gok, pment, pphys, ptech)
            )
    lines.append(f"attr-like rows (zero@34-35,01@43,mid>=12): {sum(seal_hits.values())}")
    lines.append(f"top seals: {seal_hits.most_common(12)}")
    good_for_attr.sort(reverse=True)
    lines.append(f"rows scoring >=20 vs Seimen fixture: {len(good_for_attr)}")
    for row in good_for_attr[:10]:
        total, abs_i, seal, u16, mok, pok, gok, m, p, t = row
        lines.append(
            f"  @{abs_i} seal={seal} u16={u16} M{mok}/14 P{pok}/8 G{gok}/13 total={total}"
        )
        lines.append(f"    m={m} p={p} t={t}")

    # ---- Seimen: search GK raw multiset as ÷5 bytes ----
    lines.append("\n======= Seimen GK multiset hunt (±2MB) =======")
    # display values → raw candidates typically d*5, d*5±1, d*5±2
    gk_disp = seim["gk"]
    phys_disp = seim["physical"]
    ment_disp = seim["mental"]

    def raw_opts(d: int) -> set[int]:
        return {max(1, d * 5 + k) for k in range(-2, 3)}

    gk_bags = [raw_opts(d) for d in gk_disp]
    # search contig 13–14 byte windows whose each byte ∈ corresponding bag OR any-order: loose first
    win = extract(DOUBLE["Dennis Seimen"], 2 * 1024 * 1024, before=2 * 1024 * 1024)
    base = DOUBLE["Dennis Seimen"] - 2 * 1024 * 1024
    # loose unordered: look for 13-byte window where sorted displays ≈ sorted gk
    gk_sorted = sorted(gk_disp)
    phys_sorted = sorted(phys_disp)
    ment_sorted = sorted(ment_disp)

    def soft_sorted(got_disp, expect_sorted, tol=1):
        gs = sorted(got_disp)
        return sum(1 for a, b in zip(gs, expect_sorted) if abs(a - b) <= tol)

    gk_hits = []
    phys_hits = []
    for i in range(0, len(win) - 14):
        g13 = disp(win[i : i + 13])
        okg = soft_sorted(g13, gk_sorted, 1)
        if okg >= 12:
            gk_hits.append((okg, base + i, g13, list(win[i : i + 13])))
        p8 = disp(win[i : i + 8])
        okp = soft_sorted(p8, phys_sorted, 1)
        if okp >= 8:
            # also check mental nearby?
            phys_hits.append((okp, base + i, p8))

    gk_hits.sort(reverse=True)
    phys_hits.sort(reverse=True)
    lines.append(f"GK multiset≥12/13 hits: {len(gk_hits)}")
    for okg, abs_i, g13, raw in gk_hits[:15]:
        rel = abs_i - DOUBLE["Dennis Seimen"]
        lines.append(f"  @{abs_i} rel={rel:+d} ok={okg}/13 disp={g13} raw={raw}")
        # check for 69B-shaped context
        for off in range(-55, 1):
            if abs_i + off < base:
                continue
            li = abs_i - base + off
            if 0 <= li <= len(win) - 69 and is_rec(win, li):
                lines.append(f"    in shaped@+{off} u16={struct.unpack_from('<H', win, li+36)[0]}")
            # any seal
            if 0 <= li <= len(win) - 69:
                if win[li + 34] == 0 and win[li + 35] == 0 and win[li + 43] == 1:
                    mid = sum(1 for x in win[li : li + 22] if 25 <= x <= 105)
                    if mid >= 10:
                        lines.append(
                            f"    attrish@+{off} seal=({win[li+22]},{win[li+24]}) "
                            f"u16={struct.unpack_from('<H', win, li+36)[0]}"
                        )

    lines.append(f"phys multiset 8/8 hits near Seimen window: {len(phys_hits)}")
    for okp, abs_i, p8 in phys_hits[:10]:
        lines.append(f"  @{abs_i} rel={abs_i-DOUBLE['Dennis Seimen']:+d} p={p8}")

    # Combined: mental+phys together in 69 layout relative offsets
    lines.append("\n======= combined ment+phys±1 at outfield offsets =======")
    # For each phys hit, check mental at -14
    combo = []
    for okp, abs_i, p8 in phys_hits:
        li = abs_i - base
        if li >= 14:
            m = disp(win[li - 14 : li])
            mok = soft_sorted(m, ment_sorted, 1)
            # also ordered score
            mok_ord, _ = score(m, ment_disp, 1)
            pok_ord, _ = score(p8, phys_disp, 1)
            if mok >= 12 and okp >= 7:
                combo.append((mok_ord + pok_ord, mok, okp, abs_i - 14, m, p8))
    combo.sort(reverse=True)
    lines.append(f"combo ment@-14+phys hits: {len(combo)}")
    for total, mok, pok, abs_i, m, p8 in combo[:12]:
        lines.append(
            f"  @{abs_i} bagM{mok}/14 bagP{pok}/8 ordTotal~{total} m={m} p={p8}"
        )
        # show tech/gk at +55 and +41 etc
        li = abs_i - base
        if li + 69 <= len(win):
            t = disp(win[li + 55 : li + 69])
            gok = soft_sorted(t[:13], sorted(gk_disp), 1)
            gok_ord, _ = score(t[:13], gk_disp, 1)
            lines.append(f"    +55 tech/gk? bag{gok}/13 ord{gok_ord}/13 t={t}")
            lines.append(
                f"    seal=({win[li+22]},{win[li+24]}) "
                f"u16={struct.unpack_from('<H', win, li+36)[0]} "
                f"b34={win[li+34]:02x}{win[li+35]:02x} b43={win[li+43]:02x}"
            )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
