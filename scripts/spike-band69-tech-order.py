"""Lock Band 69B +55..+68 as tech + set-pieces (14 bytes = 10+4)."""

from __future__ import annotations

import json
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/band69-tech-order.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}

REC_ABS = [
    264924148,
    264923389,
    264923458,
    264923665,
]

TECH = [
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
SETP = ["corners", "freeKickTaking", "longThrows", "penaltyTaking"]
ALL14 = TECH + SETP

# hypothesized order from density decode
HYP = [
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


def hungarian(cost):
    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment

        r, c = linear_sum_assignment(np.array(cost))
        a = [-1] * len(cost)
        for i, j in zip(r, c):
            a[int(i)] = int(j)
        return a
    except Exception:
        n = len(cost)
        used = set()
        a = [-1] * n
        for _, i, j in sorted((cost[i][j], i, j) for i in range(n) for j in range(n)):
            if a[i] < 0 and j not in used:
                a[i] = j
                used.add(j)
        return a


def fixture_map(p) -> dict[str, int]:
    out = {}
    for k in TECH:
        out[k] = int(p["attributes"]["technical"][k])
    for k in SETP:
        out[k] = int(p["attributes"]["setPieces"][k])
    return out


def score(disp, order, fix, tol=1):
    ok = sum(1 for d, nm in zip(disp, order) if abs(d - fix[nm]) <= tol)
    soft = sum(max(0, abs(d - fix[nm]) - tol) for d, nm in zip(disp, order))
    return ok, soft


def main() -> None:
    lines: list[str] = []
    band = PLAYERS["Patrick Bandeira"]
    fix = fixture_map(band)
    lines.append(f"fixture: {fix}")

    for abs_rec in REC_ABS:
        rec = extract(abs_rec, 69)
        raw = list(rec[55:69])
        disp = [round(b / 5) for b in raw]
        lines.append(f"\n======== @{abs_rec} +55..+68 ========")
        lines.append(f"raw:  {raw}")
        lines.append(f"disp: {disp}")

        # hyp
        for tol in (0, 1):
            ok, soft = score(disp, HYP, fix, tol)
            lines.append(f"  HYP tol={tol}: ok={ok}/14 soft={soft}")

        # screen tech then set
        for tol in (0, 1):
            ok, soft = score(disp, ALL14, fix, tol)
            lines.append(f"  tech+set screen tol={tol}: ok={ok}/14 soft={soft}")

        # Hungarian
        cost = [
            [
                abs(d - fix[nm]) if abs(d - fix[nm]) <= 3 else 100 + abs(d - fix[nm])
                for nm in ALL14
            ]
            for d in disp
        ]
        asg = hungarian(cost)
        order = [ALL14[asg[i]] for i in range(14)]
        ok0 = sum(disp[i] == fix[order[i]] for i in range(14))
        ok1 = sum(abs(disp[i] - fix[order[i]]) <= 1 for i in range(14))
        lines.append(f"  Hungarian: exact={ok0}/14 ±1={ok1}/14")
        lines.append(f"  order: {order}")
        for i, nm in enumerate(order):
            lines.append(
                f"    +{55+i}: {nm} save={disp[i]} fix={fix[nm]} "
                f"raw={raw[i]} d={abs(disp[i]-fix[nm])}"
            )

    # Cross-check Müller row if phys-ish (may be wrong player)
    lines.append("\n======== HYP on Müller nearby row +55 ========")
    mull = PLAYERS["Robert Müller"]
    # Müller has same tech/set keys
    mf = fixture_map(mull)
    for abs_rec in (279873395, 279873326):
        rec = extract(abs_rec, 69)
        disp = [round(b / 5) for b in rec[55:69]]
        ok0, soft0 = score(disp, HYP, mf, 0)
        ok1, soft1 = score(disp, HYP, mf, 1)
        lines.append(f"@{abs_rec} hyp tol0={ok0}/14 soft={soft0}; tol1={ok1}/14 disp={disp}")
        lines.append(f"  fix_as_hyp={[mf[n] for n in HYP]}")

    # Confirm tails identical structure across Band cluster
    lines.append("\n======== Band cluster tails (disp) ========")
    for abs_rec in range(264923320, 264924400, 69):
        rec = extract(abs_rec, 69)
        if len(rec) < 69 or rec[22] != 0x07:
            continue
        disp = [round(b / 5) for b in rec[55:69]]
        ok, soft = score(disp, HYP, fix, 1)
        lines.append(f"@{abs_rec} ok={ok}/14 soft={soft} disp={disp}")

    lines.append(
        """
======== LOCK CANDIDATE ========
+55..+68 (14 bytes, 1-100): technical + set pieces

HYP order:
  +55 crossing
  +56 dribbling
  +57 finishing
  +58 heading
  +59 longShots
  +60 firstTouch
  +61 marking
  +62 passing
  +63 penaltyTaking
  +64 freeKickTaking
  +65 tackling
  +66 technique
  +67 longThrows
  +68 corners

(Note: not screen order — heading before firstTouch; set-pieces interleaved.)
"""
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
