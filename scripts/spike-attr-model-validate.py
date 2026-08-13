"""Find UniqueID → 69B card u16 for Band/Mull/Seimen, then validate attr model.

Strategy:
1) Collect all shaped 69B records' (abs, u16, phys_disp[8], tech_disp[14], mental_disp[14])
   in a single pass (or large extracts near each double + global u16 samples).
2) For each player, score every card against fixture attrs:
   - phys order LOCKED
   - tech+set HYP LOCKED
   - mental HYP (Band Hungarian)
3) Best-scoring cards → that player's u16; require consistency across snapshots.
4) Also search: u16 appearing near UniqueID / personIndex / double-UID.
"""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/attr-model-validate.txt")
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
IDX = {
    "Dennis Seimen": 1790,
    "Patrick Bandeira": 1198,
    "Robert Müller": 1233,
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

# GK attrs (for Seimen) — if techset fails, try GK block in same slot
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


def fixture_vecs(name: str) -> dict[str, list[int]]:
    p = PLAYERS[name]
    a = p["attributes"]
    ment = [int(a["mental"][k]) for k in MENTAL_ORDER]
    phys = [int(a["physical"][k]) for k in PHYS_ORDER]
    out = {"mental": ment, "physical": phys}
    # Outfield: full tech + setPieces. GK: goalkeeping (+ optional set-ish tech).
    if "setPieces" in a and "crossing" in a.get("technical", {}):
        tech = []
        for k in TECHSET_ORDER:
            if k in a["technical"]:
                tech.append(int(a["technical"][k]))
            else:
                tech.append(int(a["setPieces"][k]))
        out["techset"] = tech
    if "goalkeeping" in a:
        out["gk"] = [int(a["goalkeeping"][k]) for k in GK_ORDER]
        while len(out["gk"]) < 14:
            out["gk"].append(-1)
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


def is_rec(b: bytes, i: int) -> bool:
    if i + 69 > len(b):
        return False
    if b[i + 22] != 0x07 or b[i + 24] != 0x9C:
        return False
    if b[i + 34] != 0 or b[i + 35] != 0:
        return False
    if b[i + 43] != 0x01:
        return False
    mid = sum(1 for x in b[i : i + 22] if 25 <= x <= 105)
    return mid >= 12


def disp14(raw: bytes) -> list[int]:
    return [round(x / 5) for x in raw]


def score_vec(got: list[int], expect: list[int], tol: int = 1) -> tuple[int, int]:
    """Return (ok_count, soft_l1). expect may contain -1 to skip."""
    ok = 0
    soft = 0
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
    return ok, soft


def parse_rec(rec: bytes) -> dict:
    return {
        "mental": disp14(rec[0:14]),
        "physical": disp14(rec[14:22]),
        "u16": struct.unpack_from("<H", rec, 36)[0],
        "techset": disp14(rec[55:69]),
        "raw55": list(rec[55:69]),
    }


def main() -> None:
    lines: list[str] = []
    fixtures = {n: fixture_vecs(n) for n in PLAYERS}

    # --- Pass 1: shaped cards in ±96KB of each double ---
    lines.append("======== shaped cards near doubles (±96KB) ========")
    by_player_hits: dict[str, list[tuple]] = defaultdict(list)
    # (abs, u16, ment_ok, phys_ok, tech_ok, gk_ok, ment_soft, parsed)

    for name, dbl in DOUBLE.items():
        win = extract(dbl, 98304, before=98304)
        base = dbl - 98304
        fx = fixtures[name]
        found = 0
        for i in range(0, len(win) - 69):
            if not is_rec(win, i):
                continue
            found += 1
            rec = win[i : i + 69]
            p = parse_rec(rec)
            mok, msoft = score_vec(p["mental"], fx["mental"], 1)
            pok, psoft = score_vec(p["physical"], fx["physical"], 1)
            tok, tsoft = (0, 99)
            gok, gsoft = (0, 99)
            if "techset" in fx:
                tok, tsoft = score_vec(p["techset"], fx["techset"], 1)
            if "gk" in fx:
                # try first 13 of techset slot as GK
                gok, gsoft = score_vec(p["techset"][:13], fx["gk"][:13], 1)
            abs_i = base + i
            by_player_hits[name].append(
                (abs_i, p["u16"], mok, pok, tok, gok, msoft, psoft, tsoft, p)
            )
        lines.append(f"{name}: shaped in window={found}")

    for name in PLAYERS:
        hits = by_player_hits[name]
        # rank: prioritize phys+tech (or gk), then mental
        def key(t):
            abs_i, u16, mok, pok, tok, gok, msoft, psoft, tsoft, p = t
            attr_ok = pok + max(tok, gok) + mok
            soft = psoft + min(tsoft, gsoft) + msoft
            return (-attr_ok, soft, abs(abs_i - DOUBLE[name]))

        hits.sort(key=key)
        lines.append(f"\n## {name} top scored cards")
        # also aggregate by u16
        u16_scores: dict[int, list] = defaultdict(list)
        for h in hits:
            u16_scores[h[1]].append(h)
        best_u16 = sorted(
            u16_scores.items(),
            key=lambda kv: (
                -max(x[3] + max(x[4], x[5]) + x[2] for x in kv[1]),
                min(x[7] + min(x[8], 99) + x[6] for x in kv[1]),
            ),
        )
        lines.append(f"  distinct u16s={len(u16_scores)}")
        for u16, rows in best_u16[:8]:
            best = min(rows, key=key)
            abs_i, _, mok, pok, tok, gok, *_ = best
            lines.append(
                f"  u16={u16} n_rows={len(rows)} best@{abs_i} "
                f"ment={mok}/14 phys={pok}/8 tech={tok}/14 gk={gok}/13"
            )
        for h in hits[:6]:
            abs_i, u16, mok, pok, tok, gok, msoft, psoft, tsoft, p = h
            lines.append(
                f"  @{abs_i} rel={abs_i-DOUBLE[name]:+d} u16={u16} "
                f"M{mok}/14 P{pok}/8 T{tok}/14 G{gok}/13"
            )
            lines.append(f"    mental={p['mental']}")
            lines.append(f"    phys  ={p['physical']}")
            lines.append(f"    tech  ={p['techset']}")

    # --- Pass 2: for Band known u16s, scan whole save; for candidates, verify ---
    lines.append("\n======== global u16 confirmation (Band known + top candidates) ========")
    # pick candidate u16 per player from best aggregate
    candidates: dict[str, int] = {}
    for name in PLAYERS:
        hits = by_player_hits[name]
        if not hits:
            continue
        u16_scores = defaultdict(list)
        for h in hits:
            u16_scores[h[1]].append(h)

        def ukey(kv):
            rows = kv[1]
            return -max(x[3] + max(x[4], x[5]) + x[2] for x in rows)

        best_u = max(u16_scores.items(), key=ukey)[0]
        candidates[name] = best_u
        lines.append(f"{name}: candidate u16={best_u}")

    # Force Band to known good if candidate wrong
    # From prior: 41140 / 40920
    if candidates.get("Patrick Bandeira") not in (41140, 40920):
        lines.append(
            f"  NOTE: Band candidate {candidates.get('Patrick Bandeira')} ≠ prior 41140/40920"
        )

    # Single-pass gather all records for candidate u16s
    want = set(candidates.values())
    # also include Band priors
    want.update([41140, 40920])
    found_rows: dict[int, list[tuple[int, dict]]] = defaultdict(list)

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
                # scan for rec starts: look for 07 ?? 9c pattern at +22
                # cheaper: find u16 at potential +36
                for u16 in list(want):
                    pat = struct.pack("<H", u16)
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        if j >= 36:
                            ri = j - 36
                            abs_ri = chunk_start + ri
                            if abs_ri >= abs_base - 0 and is_rec(data, ri):
                                rec = data[ri : ri + 69]
                                if len(rec) == 69:
                                    found_rows[u16].append((chunk_start + ri, parse_rec(rec)))
                        start = j + 1
                abs_base += len(block)
                carry = data[-80:]
        finally:
            reader.close()

    for u16, rows in found_rows.items():
        # dedupe abs
        seen = set()
        uniq = []
        for a, p in rows:
            if a in seen:
                continue
            seen.add(a)
            uniq.append((a, p))
        found_rows[u16] = uniq
        lines.append(f"u16={u16}: global shaped rows={len(uniq)}")

    # --- Pass 3: score each candidate u16 fully against each player ---
    lines.append("\n======== MODEL VALIDATION ========")
    lines.append("Mental order: " + ", ".join(MENTAL_ORDER))
    lines.append("Phys order:   " + ", ".join(PHYS_ORDER))
    lines.append("Tech/set:     " + ", ".join(TECHSET_ORDER))

    assignment: dict[str, int] = {}
    for name, fx in fixtures.items():
        lines.append(f"\n### {name}")
        ranked = []
        for u16, rows in found_rows.items():
            if not rows:
                continue
            # take median-ish / best row
            scored = []
            for abs_i, p in rows:
                mok, msoft = score_vec(p["mental"], fx["mental"], 1)
                pok, psoft = score_vec(p["physical"], fx["physical"], 1)
                if "techset" in fx:
                    tok, tsoft = score_vec(p["techset"], fx["techset"], 1)
                    total_ok = mok + pok + tok
                    total_n = 14 + 8 + 14
                    soft = msoft + psoft + tsoft
                    detail = f"M{mok}/14 P{pok}/8 T{tok}/14"
                else:
                    gok, gsoft = score_vec(p["techset"][:13], fx["gk"][:13], 1)
                    # mental+phys+gk
                    total_ok = mok + pok + gok
                    total_n = 14 + 8 + 13
                    soft = msoft + psoft + gsoft
                    detail = f"M{mok}/14 P{pok}/8 G{gok}/13"
                scored.append((total_ok, soft, abs_i, detail, p))
            scored.sort(key=lambda t: (-t[0], t[1]))
            best = scored[0]
            avg_ok = sum(t[0] for t in scored) / len(scored)
            ranked.append((best[0], best[1], avg_ok, u16, len(rows), best[2], best[3], best[4]))
        ranked.sort(key=lambda t: (-t[0], t[1], -t[2]))
        for total_ok, soft, avg_ok, u16, n, abs_i, detail, p in ranked[:5]:
            lines.append(
                f"  u16={u16} n={n} best_ok={total_ok} soft={soft} avg_ok={avg_ok:.1f} "
                f"@{abs_i} {detail}"
            )
            lines.append(f"    mental={p['mental']}")
            lines.append(f"    phys  ={p['physical']}")
            lines.append(f"    tech  ={p['techset']}")
            lines.append(f"    expect_m={fx['mental']}")
            lines.append(f"    expect_p={fx['physical']}")
            if "techset" in fx:
                lines.append(f"    expect_t={fx['techset']}")
            else:
                lines.append(f"    expect_g={fx['gk'][:13]}")
        if ranked:
            assignment[name] = ranked[0][3]
            best_ok = ranked[0][0]
            denom = 14 + 8 + (14 if "techset" in fx else 13)
            lines.append(
                f"  => ASSIGN u16={assignment[name]}  "
                f"best {best_ok}/{denom} ({100*best_ok/denom:.0f}%)"
            )

    # --- Pass 4: u16 near UniqueID? ---
    lines.append("\n======== u16 proximity to UniqueID / personIndex / double ========")
    for name, u16 in assignment.items():
        pat = struct.pack("<H", u16)
        uid = struct.pack("<I", PLAYERS[name]["uid"])
        idx = struct.pack("<I", IDX[name])
        dbl = DOUBLE[name]
        zone = extract(dbl, 2048, before=2048)
        lines.append(f"{name} u16={u16}:")
        lines.append(f"  u16 in dbl±2KB: {zone.find(pat)}")
        # wider name of extracts around uid hits is expensive; check double±64KB
        zone2 = extract(dbl, 65536, before=65536)
        positions = []
        start = 0
        while len(positions) < 5:
            j = zone2.find(pat, start)
            if j < 0:
                break
            positions.append(dbl - 65536 + j)
            start = j + 1
        lines.append(f"  u16 hits in dbl±64KB (first5): {positions}")

    lines.append("\n======== SUMMARY ASSIGNMENT ========")
    for name, u16 in assignment.items():
        lines.append(f"  {name}: u16={u16}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
