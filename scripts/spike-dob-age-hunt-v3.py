#!/usr/bin/env python3
"""
DOB/age hunt v3 — decode-everything + age-in-days + cross-player day deltas.

Focus: trail after 01 00 6c 07 near best person double, plus fixed-offset
consensus for ageDays / birth encodings around the double.
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-age-hunt-v3.txt"
PERSON_HEAD = 512 * 1024 * 1024
MARK = bytes.fromhex("01006c07")
GAME = date(2039, 7, 1)
EPOCHS = {
    "y1900": date(1900, 1, 1),
    "excel": date(1899, 12, 30),
    "unix": date(1970, 1, 1),
    "y2000": date(2000, 1, 1),
    "y0001": date(1, 1, 1),
    "fm_1950": date(1950, 1, 1),
}


def collect_doubles(mm: mmap.mmap, uid: int, limit: int = 12) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(mm), PERSON_HEAD)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def best_double(mm: mmap.mmap, doubles: list[int]) -> int | None:
    if not doubles:
        return None

    def score(dab: int) -> int:
        blob = bytes(mm[dab : dab + 160])
        s = 0
        if b"\x01\x01\x01" in blob[8:120]:
            s += 5
        if MARK in blob:
            s += 3
        if len(blob) >= 35:
            pi = struct.unpack_from("<I", blob, 31)[0]
            if 0 < pi < 200_000:
                s += 4
        return s

    return sorted(doubles, key=lambda d: (-score(d), d))[0]


def player_meta(p: dict) -> dict:
    y, m, d = map(int, p["dob"].split("-"))
    dob = date(y, m, d)
    age = int(p["age"])
    meta = {
        "name": p["name"],
        "uid": int(p["uid"]),
        "dob": dob,
        "age": age,
        "age_days": (GAME - dob).days,
        "y": y,
        "m": m,
        "d": d,
        "ymd": y * 10000 + m * 100 + d,
        "packed_dmy": d | (m << 8) | (y << 16),
        "bits_y9m4d5": ((y - 1900) << 9) | (m << 5) | d,
        "year_u16": y,
        "year_since_1900": y - 1900,
        "year_since_2000": y - 2000,
    }
    for en, ep in EPOCHS.items():
        meta[f"days_{en}"] = (dob - ep).days
    return meta


def try_decode_u32(val: int) -> list[str]:
    hints: list[str] = []
    if 30000 <= val <= 60000:
        for en, ep in EPOCHS.items():
            try:
                dt = ep + timedelta(days=val)
                if 1980 <= dt.year <= 2035:
                    hints.append(f"days_{en}->{dt.isoformat()}")
            except OverflowError:
                pass
    if 5000 <= val <= 20000:
        try:
            dt = GAME - timedelta(days=val)
            if 1980 <= dt.year <= 2035:
                hints.append(f"ageDays_from_game->{dt.isoformat()}")
        except OverflowError:
            pass
    if 19800101 <= val <= 20351231:
        s = str(val)
        try:
            dt = date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
            hints.append(f"ymd_int->{dt.isoformat()}")
        except ValueError:
            pass
    # packed dmy
    d = val & 0xFF
    m = (val >> 8) & 0xFF
    y = (val >> 16) & 0xFFFF
    if 1 <= d <= 31 and 1 <= m <= 12 and 1980 <= y <= 2035:
        hints.append(f"packed_dmy->{y:04d}-{m:02d}-{d:02d}")
    return hints


def main() -> None:
    metas = [player_meta(p) for p in PLAYERS]
    lines: list[str] = [
        f"players={len(metas)} game={GAME.isoformat()}",
        "",
    ]

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            records: list[dict] = []
            for meta in metas:
                dab = best_double(mm, collect_doubles(mm, meta["uid"]))
                if dab is None:
                    continue
                blob = bytes(mm[dab : dab + 512])
                mark_offs = []
                start = 0
                while True:
                    j = blob.find(MARK, start)
                    if j < 0:
                        break
                    mark_offs.append(j)
                    start = j + 1
                records.append({"meta": meta, "dab": dab, "blob": blob, "marks": mark_offs})

            lines.append("## mark trail dumps (first mark in +512)")
            for rec in records:
                m = rec["meta"]
                if not rec["marks"]:
                    lines.append(f"  {m['name']}: NO mark")
                    continue
                j = rec["marks"][0]
                trail = rec["blob"][j : j + 32]
                u32s = [
                    struct.unpack_from("<I", trail, off)[0]
                    for off in range(4, min(28, len(trail) - 3), 4)
                ]
                hints = []
                for u in u32s:
                    hints.extend(try_decode_u32(u)[:2])
                lines.append(
                    f"  {m['name']} mark@{j} age={m['age']} dob={m['dob']} "
                    f"ageDays={m['age_days']} trail={trail.hex(' ')}"
                )
                if hints:
                    lines.append(f"    decode?: {hints[:8]}")

            # --- Consensus: value at mark+delta equals known encoding ---
            encodings = [
                "age",
                "age_days",
                "ymd",
                "packed_dmy",
                "bits_y9m4d5",
                "year_u16",
                "year_since_1900",
                "year_since_2000",
                "days_y1900",
                "days_excel",
                "days_unix",
                "days_y2000",
                "days_fm_1950",
                "m",
                "d",
            ]

            lines.append("\n## consensus: field at (first_mark + delta) == encoding")
            # Only players with a mark
            with_mark = [r for r in records if r["marks"]]
            for enc in encodings:
                best_for_enc: list[tuple[int, int, str]] = []  # score, delta, width
                for width, pack in (("u8", "B"), ("u16", "H"), ("u32", "I"), ("i32", "i")):
                    size = struct.calcsize("<" + pack)
                    hits_by_delta: Counter[int] = Counter()
                    for rec in with_mark:
                        want = int(rec["meta"][enc])
                        j = rec["marks"][0]
                        for delta in range(0, 64 - size + 1):
                            pos = j + delta
                            if pos + size > len(rec["blob"]):
                                continue
                            got = struct.unpack_from("<" + pack, rec["blob"], pos)[0]
                            if got == want:
                                hits_by_delta[delta] += 1
                    need = max(8, int(0.7 * len(with_mark)))
                    for delta, n in hits_by_delta.most_common(3):
                        if n >= need:
                            best_for_enc.append((n, delta, width))
                if best_for_enc:
                    best_for_enc.sort(reverse=True)
                    for n, delta, width in best_for_enc[:5]:
                        lines.append(
                            f"  LOCK? {enc} as {width} @ mark+{delta} "
                            f"matched {n}/{len(with_mark)}"
                        )

            # Same but relative to double start
            lines.append("\n## consensus: field at (double + rel) == encoding (±384)")
            for enc in encodings:
                found_lock = False
                for width, pack in (("u8", "B"), ("u16", "H"), ("u32", "I"), ("i32", "i")):
                    size = struct.calcsize("<" + pack)
                    hits: Counter[int] = Counter()
                    for rec in records:
                        want = int(rec["meta"][enc])
                        for rel in range(-128, 384 - size + 1):
                            pos = 8 + rel if False else rel  # rel from double start
                            # allow negative: read from mm
                            abs_pos = rec["dab"] + rel
                            if abs_pos < 0 or abs_pos + size > len(mm):
                                continue
                            got = struct.unpack_from("<" + pack, mm, abs_pos)[0]
                            if got == want:
                                hits[rel] += 1
                    need = max(10, int(0.7 * len(records)))
                    for rel, n in hits.most_common(5):
                        if n >= need:
                            lines.append(
                                f"  LOCK? {enc} as {width} @ double{rel:+d} "
                                f"matched {n}/{len(records)}"
                            )
                            found_lock = True
                if not found_lock and enc in ("age", "age_days", "days_y1900", "ymd"):
                    # show top noise for key encodings
                    hits = Counter()
                    for rec in records:
                        want = int(rec["meta"][enc])
                        for rel in range(-64, 256):
                            abs_pos = rec["dab"] + rel
                            if abs_pos < 0 or abs_pos + 4 > len(mm):
                                continue
                            for pack, size in (("I", 4), ("H", 2), ("B", 1)):
                                got = struct.unpack_from("<" + pack, mm, abs_pos)[0]
                                if got == want:
                                    hits[(rel, pack)] += 1
                    top = hits.most_common(3)
                    lines.append(f"  (no lock) {enc} top={top}")

            # --- Cross-player delta method ---
            # For each u32 offset from double, check if (val_a - val_b) == (days_a - days_b)
            lines.append("\n## cross-player day-delta lock (u32 @ double+rel)")
            # Use players with mark and varied ages
            sample = records[:16]
            day_key = "days_y1900"
            delta_hits: Counter[int] = Counter()
            pair_n = 0
            for i, ra in enumerate(sample):
                for rb in sample[i + 1 :]:
                    pair_n += 1
                    da = ra["meta"][day_key] - rb["meta"][day_key]
                    if da == 0:
                        continue
                    for rel in range(0, 256, 4):
                        va = struct.unpack_from("<i", mm, ra["dab"] + rel)[0]
                        vb = struct.unpack_from("<i", mm, rb["dab"] + rel)[0]
                        if va - vb == da:
                            delta_hits[rel] += 1
            need_pairs = max(20, int(0.5 * pair_n))
            lines.append(f"  pairs≈{pair_n} need≥{need_pairs}")
            locked = [(rel, n) for rel, n in delta_hits.most_common(20) if n >= need_pairs]
            if locked:
                for rel, n in locked:
                    lines.append(f"  LOCK? dayDelta @ double+{rel} pairs={n}")
            else:
                for rel, n in delta_hits.most_common(8):
                    lines.append(f"  top dayDelta @ double+{rel} pairs={n}")

            # Same for age_days
            delta_hits = Counter()
            for i, ra in enumerate(sample):
                for rb in sample[i + 1 :]:
                    da = ra["meta"]["age_days"] - rb["meta"]["age_days"]
                    if da == 0:
                        continue
                    for rel in range(0, 256, 4):
                        va = struct.unpack_from("<i", mm, ra["dab"] + rel)[0]
                        vb = struct.unpack_from("<i", mm, rb["dab"] + rel)[0]
                        if va - vb == da:
                            delta_hits[rel] += 1
            lines.append("\n## cross-player ageDays-delta lock (i32 @ double+rel)")
            locked = [(rel, n) for rel, n in delta_hits.most_common(20) if n >= need_pairs]
            if locked:
                for rel, n in locked:
                    lines.append(f"  LOCK? ageDaysDelta @ double+{rel} pairs={n}")
            else:
                for rel, n in delta_hits.most_common(8):
                    lines.append(f"  top ageDaysDelta @ double+{rel} pairs={n}")

            # --- Mark-relative day delta ---
            lines.append("\n## cross-player day-delta after first mark")
            delta_hits = Counter()
            marked = [r for r in sample if r["marks"]]
            pair_n = 0
            for i, ra in enumerate(marked):
                for rb in marked[i + 1 :]:
                    pair_n += 1
                    da = ra["meta"][day_key] - rb["meta"][day_key]
                    if da == 0:
                        continue
                    for delta in range(4, 48, 4):
                        va = struct.unpack_from("<i", ra["blob"], ra["marks"][0] + delta)[0]
                        vb = struct.unpack_from("<i", rb["blob"], rb["marks"][0] + delta)[0]
                        if va - vb == da:
                            delta_hits[delta] += 1
            need_pairs = max(10, int(0.4 * max(1, pair_n)))
            lines.append(f"  marked_pairs≈{pair_n} need≥{need_pairs}")
            locked = [(d, n) for d, n in delta_hits.most_common(15) if n >= need_pairs]
            if locked:
                for d, n in locked:
                    lines.append(f"  LOCK? dayDelta @ mark+{d} pairs={n}")
            else:
                for d, n in delta_hits.most_common(8):
                    lines.append(f"  top dayDelta @ mark+{d} pairs={n}")

            # Float days? sometimes SI uses double
            lines.append("\n## float/double coincidences near mark (days_y1900 as float)")
            float_hits = Counter()
            for rec in with_mark:
                want = float(rec["meta"]["days_y1900"])
                j = rec["marks"][0]
                for delta in range(0, 48):
                    if j + delta + 4 > len(rec["blob"]):
                        continue
                    f32 = struct.unpack_from("<f", rec["blob"], j + delta)[0]
                    if abs(f32 - want) < 0.51:
                        float_hits[delta] += 1
            for d, n in float_hits.most_common(8):
                lines.append(f"  f32≈days_y1900 @ mark+{d}: {n}/{len(with_mark)}")

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # print summary only
    print("\n".join(lines[-80:]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
