#!/usr/bin/env python3
"""
Age hunt v2: fixed gap after single-UID, and Spearman-ish correlation
of byte-at-offset vs known age (to catch encodings that aren't raw age).
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "age-hunt-v2.txt"
PERSON_HEAD = 512 * 1024 * 1024
GAPS = list(range(0, 257))  # bytes after single UID to test for age_u8


def best_double(mm: mmap.mmap, uid: int) -> int | None:
    pat = struct.pack("<II", uid, uid)
    end = min(len(mm), PERSON_HEAD)
    hits: list[int] = []
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 12:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    if not hits:
        return None

    def score(dab: int) -> int:
        blob = bytes(mm[dab : dab + 160])
        s = 0
        if b"\x01\x01\x01" in blob[8:120]:
            s += 5
        if bytes.fromhex("01006c07") in blob:
            s += 3
        if len(blob) >= 35:
            pi = struct.unpack_from("<I", blob, 31)[0]
            if 0 < pi < 200_000:
                s += 4
        return s

    return sorted(hits, key=lambda d: (-score(d), d))[0]


def main() -> None:
    lines: list[str] = [f"players={len(PLAYERS)}", ""]
    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # --- A: after best double, score every offset by exact age match ---
            # (already done in v1) — also score age*10, age*100, 100-age, months≈age*12
            alts = {
                "age": lambda a: a,
                "age_x12": lambda a: a * 12,  # rough months lived (coarse)
                "100_minus_age": lambda a: 100 - a,
                "age_plus_16": lambda a: a + 16,  # occasional FM CA-ish padding
            }
            # only for values that fit u8
            radius = 512
            for aname, fn in alts.items():
                hits: Counter[int] = Counter()
                ok_n = 0
                for p in PLAYERS:
                    uid = int(p["uid"])
                    want = fn(int(p["age"]))
                    if not (0 <= want <= 255):
                        continue
                    dab = best_double(mm, uid)
                    if dab is None:
                        continue
                    ok_n += 1
                    lo = max(0, dab - radius)
                    hi = min(len(mm), dab + radius)
                    win = bytes(mm[lo:hi])
                    rel0 = dab - lo
                    for i, b in enumerate(win):
                        if b == want:
                            hits[i - rel0] += 1
                need = max(8, ok_n * 60 // 100)
                locked = [(o, c) for o, c in hits.most_common(15) if c >= need]
                lines.append(f"## alt {aname} u8 @±{radius} need≥{need}/{ok_n}")
                if locked:
                    for o, c in locked:
                        lines.append(f"  LOCK? rel={o:+d} {c}/{ok_n}")
                else:
                    for o, c in hits.most_common(5):
                        lines.append(f"  top rel={o:+d} {c}/{ok_n}")

            # --- B: fixed gap after SINGLE uid occurrence near best double ---
            # For each gap 0..256, count players where mm[dab+8+gap]==age
            # (record often continues after the 8-byte double)
            gap_hits: Counter[int] = Counter()
            for p in PLAYERS:
                uid = int(p["uid"])
                age = int(p["age"])
                dab = best_double(mm, uid)
                if dab is None:
                    continue
                for gap in GAPS:
                    pos = dab + 8 + gap
                    if 0 <= pos < len(mm) and mm[pos] == age:
                        gap_hits[gap] += 1
            lines.append("\n## age_u8 at double+8+gap")
            for gap, c in gap_hits.most_common(12):
                lines.append(f"  gap={gap:3d} players={c}/{len(PLAYERS)}")

            # --- C: correlation of byte vs age across players at each offset ---
            # Perfect identity: value==age for all. Near-linear: value ≈ k*age+b
            series: dict[int, list[tuple[int, int]]] = defaultdict(list)
            for p in PLAYERS:
                uid = int(p["uid"])
                age = int(p["age"])
                dab = best_double(mm, uid)
                if dab is None:
                    continue
                for off in range(-256, 257):
                    pos = dab + off
                    if 0 <= pos < len(mm):
                        series[off].append((age, mm[pos]))

            best_corr: list[tuple[float, int, str]] = []
            for off, pairs in series.items():
                if len(pairs) < 12:
                    continue
                ages = [a for a, _ in pairs]
                vals = [v for _, v in pairs]
                # exact match rate
                exact = sum(1 for a, v in pairs if a == v) / len(pairs)
                # pearson-ish
                ma = sum(ages) / len(ages)
                mv = sum(vals) / len(vals)
                num = sum((a - ma) * (v - mv) for a, v in pairs)
                da = sum((a - ma) ** 2 for a in ages) ** 0.5
                dv = sum((v - mv) ** 2 for v in vals) ** 0.5
                r = (num / (da * dv)) if da and dv else 0.0
                # also check vals == birth_year - 1900 etc via age link: birth approx 2039-age
                by = [2039 - a for a in ages]
                by_exact = sum(1 for y, v in zip(by, vals) if (y & 0xFF) == v) / len(pairs)
                score = max(exact, abs(r) * 0.5, by_exact)
                tag = f"exact={exact:.2f} r={r:+.2f} by1900ish={by_exact:.2f}"
                best_corr.append((score, off, tag))
            best_corr.sort(reverse=True)
            lines.append("\n## byte@offset vs age correlation (top 20)")
            for score, off, tag in best_corr[:20]:
                lines.append(f"  score={score:.3f} rel={off:+4d} {tag}")

            # --- D: scan entire head for uid_u32 then age within gap window, consensus gap ---
            # Expensive-ish but limited: find first 4 single-UID hits per player in head
            lines.append("\n## single-UID → age_u8 gap consensus (first 4 hits/player)")
            per_gap: Counter[int] = Counter()
            player_gap_support: dict[int, set[int]] = defaultdict(set)
            for p in PLAYERS:
                uid = int(p["uid"])
                age = int(p["age"])
                pat = struct.pack("<I", uid)
                hits: list[int] = []
                j = mm.find(pat, 0, min(len(mm), PERSON_HEAD))
                while j >= 0 and len(hits) < 4:
                    hits.append(j)
                    j = mm.find(pat, j + 1, min(len(mm), PERSON_HEAD))
                for h in hits:
                    for gap in range(0, 129):
                        pos = h + 4 + gap
                        if pos < len(mm) and mm[pos] == age:
                            player_gap_support[gap].add(uid)
                            per_gap[gap] += 1
            # rank by unique players supporting gap
            ranked = sorted(
                ((gap, len(uids)) for gap, uids in player_gap_support.items()),
                key=lambda t: (-t[1], t[0]),
            )
            for gap, n in ranked[:15]:
                lines.append(f"  gap={gap:3d} unique_players={n}/{len(PLAYERS)}")

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
