"""Solve Band 69B +0..+13 as the 14 mental attrs (phys@+14 already locked).

Uses assignment (Hungarian) with cost = display drift |round(b/5)-fixture|.
Also tests known column orders and reports best permutation.
"""

from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import zstandard as zstd

# Optional scipy for Hungarian; fallback to pure DFS for n=14 is too slow,
# so we use a simple min-cost matching via recursive backtracking with pruning
# OR pulp-less greedy+2-opt. Prefer scipy if available.

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/band69-mental-order.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}

# Best Band row (phys 8/8): from locked spike
REC_ABS = 264924148  # phys 8/8, u16=40920
# Also test original
REC_ABS_B = 264923389

MENTAL_NAMES = [
    "aggression",
    "anticipation",
    "bravery",
    "composure",
    "concentration",
    "decisions",
    "determination",
    "flair",
    "leadership",
    "offTheBall",
    "positioning",
    "teamwork",
    "vision",
    "workRate",
]

# Candidate fixed orders to try
ORDERS = {
    "screen_LthenR": MENTAL_NAMES[:],  # classic profile
    "screen_RthenL": MENTAL_NAMES[7:] + MENTAL_NAMES[:7],
    "alpha": sorted(MENTAL_NAMES),
    # common engine-ish: determination/leadership early?
    "det_lea_focus": [
        "determination",
        "leadership",
        "aggression",
        "anticipation",
        "bravery",
        "composure",
        "concentration",
        "decisions",
        "flair",
        "offTheBall",
        "positioning",
        "teamwork",
        "vision",
        "workRate",
    ],
    # save hyp from earlier: agg ant bra work det dec flair lea otb pos team vis com conc
    "hyp_A": [
        "aggression",
        "anticipation",
        "bravery",
        "workRate",
        "determination",
        "decisions",
        "flair",
        "leadership",
        "offTheBall",
        "positioning",
        "teamwork",
        "vision",
        "composure",
        "concentration",
    ],
    # Müller-friendly: early composure match
    "hyp_B": [
        "aggression",
        "anticipation",
        "bravery",
        "composure",
        "concentration",
        "decisions",
        "flair",
        "leadership",
        "determination",
        "offTheBall",
        "positioning",
        "teamwork",
        "vision",
        "workRate",
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


def hungarian(cost: list[list[int]]) -> list[int]:
    """Return col assigned to each row. Prefer scipy; else Jonker-Volgenant-lite DFS."""
    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment

        r, c = linear_sum_assignment(np.array(cost))
        assign = [-1] * len(cost)
        for i, j in zip(r, c):
            assign[int(i)] = int(j)
        return assign
    except Exception:
        pass
    # Fallback: greedy then 2-opt
    n = len(cost)
    used = set()
    assign = [-1] * n
    pairs = sorted(
        ((cost[i][j], i, j) for i in range(n) for j in range(n)),
        key=lambda t: t[0],
    )
    for _, i, j in pairs:
        if assign[i] < 0 and j not in used:
            assign[i] = j
            used.add(j)
        if len(used) == n:
            break
    improved = True
    while improved:
        improved = False
        for i in range(n):
            for k in range(i + 1, n):
                j, m = assign[i], assign[k]
                if cost[i][j] + cost[k][m] > cost[i][m] + cost[k][j]:
                    assign[i], assign[k] = m, j
                    improved = True
    return assign


def score_order(disp: list[int], names: list[str], fixture: dict[str, int], tol: int = 0) -> tuple[int, int]:
    soft = 0
    ok = 0
    for d, nm in zip(disp, names):
        fix = fixture[nm]
        diff = abs(d - fix)
        if diff <= tol:
            ok += 1
        else:
            soft += diff - tol
    return ok, soft


def main() -> None:
    lines: list[str] = []
    band = PLAYERS["Patrick Bandeira"]
    fixture = {k: band["attributes"]["mental"][k] for k in MENTAL_NAMES}
    # also Müller as cross-check if we find his row later
    mull = PLAYERS["Robert Müller"]
    mull_fix = {k: mull["attributes"]["mental"][k] for k in MENTAL_NAMES}

    for label, abs_rec in [("best_phys8", REC_ABS), ("orig", REC_ABS_B)]:
        rec = extract(abs_rec, 69)
        raw = list(rec[:14])
        disp = [round(b / 5) for b in raw]
        lines.append(f"\n======== {label} @{abs_rec} ========")
        lines.append(f"raw:  {raw}")
        lines.append(f"disp: {disp}")
        lines.append(f"fixture screen: {[fixture[n] for n in MENTAL_NAMES]}")

        # Known orders
        lines.append("-- fixed orders (tol=0 / tol=1) --")
        for oname, order in ORDERS.items():
            for tol in (0, 1):
                ok, soft = score_order(disp, order, fixture, tol)
                lines.append(f"  {oname} tol={tol}: ok={ok}/14 soft={soft}")

        # Hungarian assignment
        lines.append("-- Hungarian assignment to fixture mentals --")
        for tol_weight in (1,):
            cost = []
            for d in disp:
                row = []
                for nm in MENTAL_NAMES:
                    diff = abs(d - fixture[nm])
                    # heavy penalty beyond 2 so we prefer ±0/1/2
                    row.append(diff if diff <= 3 else 100 + diff)
                cost.append(row)
            assign = hungarian(cost)
            total = sum(cost[i][assign[i]] for i in range(14))
            ok1 = sum(1 for i in range(14) if abs(disp[i] - fixture[MENTAL_NAMES[assign[i]]]) <= 1)
            ok0 = sum(1 for i in range(14) if disp[i] == fixture[MENTAL_NAMES[assign[i]]])
            lines.append(f"  total_cost={total} exact={ok0}/14 within±1={ok1}/14")
            order = [MENTAL_NAMES[assign[i]] for i in range(14)]
            lines.append(f"  order: {order}")
            for i, nm in enumerate(order):
                lines.append(
                    f"    +{i}: disp={disp[i]} -> {nm} fix={fixture[nm]} "
                    f"raw={raw[i]} (d={abs(disp[i]-fixture[nm])})"
                )

        # Multiset check
        from collections import Counter

        lines.append(f"  disp multiset: {sorted(Counter(disp).items())}")
        lines.append(
            f"  fix  multiset: {sorted(Counter(fixture.values()).items())}"
        )

    # Cross-check: same Hungarian order on Band applied to Müller nearest high-mental rows
    lines.append("\n======== Does Band's solved order fit Müller nearby rows? ========")
    # Recompute order from best_phys8
    rec = extract(REC_ABS, 69)
    disp = [round(b / 5) for b in rec[:14]]
    cost = [[abs(d - fixture[nm]) if abs(d - fixture[nm]) <= 3 else 100 + abs(d - fixture[nm])
             for nm in MENTAL_NAMES] for d in disp]
    assign = hungarian(cost)
    band_order = [MENTAL_NAMES[assign[i]] for i in range(14)]
    lines.append(f"Band solved order: {band_order}")

    # pull Müller shaped heads from prior knowledge (~279873395)
    mull_recs = [279873395, 279873326, 279873257, 279873188]
    for abs_r in mull_recs:
        r = extract(abs_r, 69)
        d = [round(b / 5) for b in r[:14]]
        ok0, soft0 = score_order(d, band_order, mull_fix, 0)
        ok1, soft1 = score_order(d, band_order, mull_fix, 1)
        okS, softS = score_order(d, MENTAL_NAMES, mull_fix, 1)
        lines.append(
            f"  @{abs_r} band_order tol0={ok0}/14 soft={soft0}; tol1={ok1}/14; "
            f"screen_tol1={okS}/14 disp={d}"
        )

    # Try tiny swap improvements on screen order (adjacent swaps)
    lines.append("\n======== local swap improvements from screen order ========")
    best = (score_order(disp, MENTAL_NAMES, fixture, 1), MENTAL_NAMES[:])
    cur = MENTAL_NAMES[:]
    for _ in range(200):
        improved = False
        for i in range(13):
            nxt = cur[:]
            nxt[i], nxt[i + 1] = nxt[i + 1], nxt[i]
            sc = score_order(disp, nxt, fixture, 1)
            # maximize ok, minimize soft
            key = (sc[0], -sc[1])
            bkey = (best[0][0], -best[0][1])
            if key > bkey:
                best = (sc, nxt)
                cur = nxt
                improved = True
        if not improved:
            # random-ish: try any swap
            for i in range(14):
                for j in range(i + 1, 14):
                    nxt = cur[:]
                    nxt[i], nxt[j] = nxt[j], nxt[i]
                    sc = score_order(disp, nxt, fixture, 1)
                    key = (sc[0], -sc[1])
                    bkey = (best[0][0], -best[0][1])
                    if key > bkey:
                        best = (sc, nxt)
                        cur = nxt
                        improved = True
            if not improved:
                break
    lines.append(f"best after swaps: ok={best[0][0]}/14 soft={best[0][1]}")
    lines.append(f"order: {best[1]}")
    for i, nm in enumerate(best[1]):
        lines.append(
            f"  +{i}: {nm} save={disp[i]} fix={fixture[nm]} d={abs(disp[i]-fixture[nm])}"
        )

    # Tech: are +44.. any tech on 1-20 raw?
    lines.append("\n======== +43..+54 as possible HA / raw 1-20 ========")
    for abs_rec in (REC_ABS, REC_ABS_B):
        rec = extract(abs_rec, 69)
        lines.append(f"@{abs_rec} +43..54: {list(rec[43:55])}")
        lines.append(f"         /5: {[round(x/5,1) for x in rec[43:55]]}")

    lines.append(
        """
======== INTERPRETATION ========
If Hungarian within±1 is high but screen order is low, mental values live
at +0..+13 on 1-100 but column ORDER ≠ profile screen order.
If multiset differs a lot even ±1, these bytes are NOT pure mentals
(or fixture is badly stale).
"""
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
