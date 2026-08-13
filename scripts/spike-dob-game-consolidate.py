#!/usr/bin/env python3
"""
Consolidate DOB + gameDate encodings against known screenshot players.

Uses existing decomp (tmp/fm-spike/dob-lock-decomp.bin) + age-hunt-players.json.
Emits which encodings lock across players, plus a gameDate candidate from ages.
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
OUT = ROOT / "tmp" / "fm-spike" / "dob-game-consolidate.txt"
MARK = bytes.fromhex("01006c07")
PERSON_HEAD = 512 * 1024 * 1024
EPOCHS = {
    "y1900": date(1900, 1, 1),
    "excel": date(1899, 12, 30),
    "unix": date(1970, 1, 1),
    "y1950": date(1950, 1, 1),
    "y2000": date(2000, 1, 1),
}


def doubles(mm: mmap.mmap, uid: int) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(mm), PERSON_HEAD)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 12:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def score_double(mm: mmap.mmap, dab: int) -> int:
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


def best_double(mm: mmap.mmap, uid: int) -> int | None:
    ds = doubles(mm, uid)
    return sorted(ds, key=lambda d: (-score_double(mm, d), d))[0] if ds else None


def effective_mark_rel(blob: bytes) -> int | None:
    j = blob.find(MARK)
    if j < 0:
        return None
    if blob[j + 4 : j + 8] == MARK:
        return j + 4
    return j


def encodings_for(dob: date, game: date) -> dict[str, bytes]:
    out: dict[str, bytes] = {
        "ymd_HBB": struct.pack("<HBB", dob.year, dob.month, dob.day),
        "ymd_HHH": struct.pack("<HHH", dob.year, dob.month, dob.day),
        "dmy_BBH": struct.pack("<BBH", dob.day, dob.month, dob.year),
        "mdy_BBH": struct.pack("<BBH", dob.month, dob.day, dob.year),
        "ymd_int": struct.pack("<I", dob.year * 10000 + dob.month * 100 + dob.day),
        "packed_dmy": struct.pack(
            "<I", dob.day | (dob.month << 8) | (dob.year << 16)
        ),
        "bits_y9m4d5": struct.pack(
            "<H", ((dob.year - 1900) << 9) | (dob.month << 5) | dob.day
        ),
        "year_u16": struct.pack("<H", dob.year),
        "age_u8": bytes([(game - dob).days // 365]),  # coarse
        "ageDays_u16": struct.pack("<H", (game - dob).days),
        "ageDays_u32": struct.pack("<I", (game - dob).days),
        "ageDays_i32": struct.pack("<i", (game - dob).days),
    }
    for name, ep in EPOCHS.items():
        days = (dob - ep).days
        out[f"days_{name}_u32"] = struct.pack("<I", days & 0xFFFFFFFF)
        out[f"days_{name}_u16"] = struct.pack("<H", days & 0xFFFF)
        out[f"tag02_days_{name}"] = b"\x02" + struct.pack("<I", days & 0xFFFFFFFF)
        out[f"tag01_days_{name}"] = b"\x01" + struct.pack("<I", days & 0xFFFFFFFF)
        # ×5 internal scale sometimes
        out[f"days_{name}_x5_u32"] = struct.pack("<I", (days * 5) & 0xFFFFFFFF)
    # exact fixture age if present handled separately
    return out


def find_all(win: bytes, pat: bytes) -> list[int]:
    out: list[int] = []
    start = 0
    while True:
        i = win.find(pat, start)
        if i < 0:
            break
        out.append(i)
        start = i + 1
    return out


def main() -> None:
    lines: list[str] = []
    if not DECOMP.exists():
        raise SystemExit(f"missing decomp: {DECOMP}")

    # Candidate game dates from fixture ages: Seimen 33 ↔ ~2038–2039.
    game_candidates = [
        date(2039, 7, 1),
        date(2039, 6, 15),
        date(2039, 5, 15),
        date(2039, 1, 1),
        date(2038, 7, 1),
        date(2039, 11, 1),
    ]

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # Precompute best doubles
            players = []
            for p in PLAYERS:
                uid = int(p["uid"])
                y, m, d = map(int, p["dob"].split("-"))
                dob = date(y, m, d)
                dab = best_double(mm, uid)
                players.append(
                    {
                        **p,
                        "dob_d": dob,
                        "age": int(p["age"]),
                        "dab": dab,
                    }
                )
            usable = [p for p in players if p["dab"] is not None]
            lines.append(f"players={len(players)} usable_doubles={len(usable)}")

            # --- A: encoding lock near best double ---
            radius = 4096
            for game in game_candidates:
                lines.append(f"\n## encoding lock @±{radius} game={game.isoformat()}")
                # Exact ages must match gameDate for this candidate
                age_ok = 0
                for p in usable:
                    derived = (
                        game.year
                        - p["dob_d"].year
                        - (
                            (game.month, game.day)
                            < (p["dob_d"].month, p["dob_d"].day)
                        )
                    )
                    if derived == p["age"]:
                        age_ok += 1
                lines.append(f"  age_match_vs_fixture: {age_ok}/{len(usable)}")

                hit_players: dict[str, set[str]] = defaultdict(set)
                rel_hits: dict[str, Counter[int]] = defaultdict(Counter)

                for p in usable:
                    dab = p["dab"]
                    assert dab is not None
                    lo = max(0, dab - radius)
                    hi = min(len(mm), dab + radius)
                    win = bytes(mm[lo:hi])
                    rel0 = dab - lo
                    pats = encodings_for(p["dob_d"], game)
                    pats["fixture_age_u8"] = bytes([p["age"]])
                    pats["fixture_age_u16"] = struct.pack("<H", p["age"])
                    for name, pat in pats.items():
                        offs = find_all(win, pat)
                        if not offs:
                            continue
                        hit_players[name].add(p["name"])
                        for i in offs:
                            rel_hits[name][i - rel0] += 1

                need = max(8, len(usable) * 70 // 100)
                locked = []
                for name, nameset in hit_players.items():
                    if len(nameset) < need:
                        continue
                    # shared relative offset?
                    shared = [
                        (rel, c)
                        for rel, c in rel_hits[name].most_common(20)
                        if c >= need
                    ]
                    locked.append((len(nameset), name, shared[:5]))
                locked.sort(reverse=True)
                if locked:
                    for n, name, shared in locked[:25]:
                        lines.append(f"  HIT {name}: players={n}/{len(usable)} shared={shared}")
                else:
                    # show top near-misses
                    top = sorted(
                        ((len(s), k) for k, s in hit_players.items()), reverse=True
                    )[:12]
                    lines.append(f"  (no lock ≥{need}) top existence: {top}")

            # --- B: mark-relative i32/i16 decode as DOB days ---
            lines.append("\n## mark-trail field decode as DOB days (best game=2039-07-01)")
            game = date(2039, 7, 1)
            for delta in range(0, 24):
                for fmt, size, unpack in (
                    ("u32", 4, lambda b: struct.unpack_from("<I", b, 0)[0]),
                    ("i32", 4, lambda b: struct.unpack_from("<i", b, 0)[0]),
                    ("u16", 2, lambda b: struct.unpack_from("<H", b, 0)[0]),
                    ("i16", 2, lambda b: struct.unpack_from("<h", b, 0)[0]),
                ):
                    ok_by_epoch: Counter[str] = Counter()
                    ok_age_days = 0
                    n_marks = 0
                    for p in usable:
                        dab = p["dab"]
                        assert dab is not None
                        blob = bytes(mm[dab : dab + 512])
                        em = effective_mark_rel(blob)
                        if em is None:
                            continue
                        n_marks += 1
                        trail = blob[em + 4 :]  # after mark bytes
                        if delta + size > len(trail):
                            continue
                        val = unpack(trail[delta:])
                        for ep_name, ep in EPOCHS.items():
                            try:
                                dt = ep + timedelta(days=int(val))
                            except Exception:
                                continue
                            if dt == p["dob_d"]:
                                ok_by_epoch[ep_name] += 1
                        if int(val) == (game - p["dob_d"]).days:
                            ok_age_days += 1
                    for ep_name, n in ok_by_epoch.most_common(3):
                        if n >= 8:
                            lines.append(
                                f"  LOCK? mark+4+{delta} {fmt} as days_{ep_name}: {n}/{n_marks}"
                            )
                    if ok_age_days >= 8:
                        lines.append(
                            f"  LOCK? mark+4+{delta} {fmt} as ageDays: {ok_age_days}/{n_marks}"
                        )

            # --- C: gameDate as days_* near early file / mark samples ---
            lines.append("\n## gameDate existence in first 4MB (days_* encodings)")
            early = bytes(mm[: min(len(mm), 4 * 1024 * 1024)])
            for game in game_candidates:
                for ep_name, ep in EPOCHS.items():
                    days = (game - ep).days
                    pat = struct.pack("<I", days & 0xFFFFFFFF)
                    count = early.count(pat)
                    if count:
                        lines.append(
                            f"  {game.isoformat()} days_{ep_name}={days} hits={count}"
                        )
                # also ymd
                pat = struct.pack("<HBB", game.year, game.month, game.day)
                c = early.count(pat)
                if c:
                    lines.append(f"  {game.isoformat()} ymd_HBB hits={c}")

            # --- D: cross-player DOB day-delta lock (independent of epoch) ---
            lines.append("\n## cross-player DOB day-delta u32 @ double+rel (±512)")
            # For every pair, expected delta_days; find shared rel where u32 diff matches
            pairs = []
            for i, a in enumerate(usable):
                for b in usable[i + 1 :]:
                    pairs.append((a, b, (a["dob_d"] - b["dob_d"]).days))
            rel_ok: Counter[int] = Counter()
            for a, b, delta in pairs:
                da, db = a["dab"], b["dab"]
                assert da is not None and db is not None
                for rel in range(-512, 513):
                    pa, pb = da + rel, db + rel
                    if not (0 <= pa <= len(mm) - 4 and 0 <= pb <= len(mm) - 4):
                        continue
                    va = struct.unpack_from("<i", mm, pa)[0]
                    vb = struct.unpack_from("<i", mm, pb)[0]
                    if va - vb == delta:
                        rel_ok[rel] += 1
            need_pairs = max(20, len(pairs) * 40 // 100)
            top = [(r, c) for r, c in rel_ok.most_common(15) if c >= need_pairs]
            lines.append(f"  pairs={len(pairs)} need≥{need_pairs}")
            if top:
                for r, c in top:
                    lines.append(f"  LOCK? double{r:+d} day-delta matches {c}/{len(pairs)}")
            else:
                for r, c in rel_ok.most_common(8):
                    lines.append(f"  top double{r:+d} {c}/{len(pairs)}")

            # Same after mark
            lines.append("\n## cross-player DOB day-delta u32 @ mark+4+delta")
            mark_ok: Counter[int] = Counter()
            marked_pairs = 0
            for a, b, delta in pairs:
                da, db = a["dab"], b["dab"]
                assert da is not None and db is not None
                ba = bytes(mm[da : da + 512])
                bb = bytes(mm[db : db + 512])
                ea = effective_mark_rel(ba)
                eb = effective_mark_rel(bb)
                if ea is None or eb is None:
                    continue
                marked_pairs += 1
                for dlt in range(0, 64):
                    if ea + 4 + dlt + 4 > len(ba) or eb + 4 + dlt + 4 > len(bb):
                        continue
                    va = struct.unpack_from("<i", ba, ea + 4 + dlt)[0]
                    vb = struct.unpack_from("<i", bb, eb + 4 + dlt)[0]
                    if va - vb == delta:
                        mark_ok[dlt] += 1
            need_m = max(10, marked_pairs * 40 // 100)
            lines.append(f"  marked_pairs={marked_pairs} need≥{need_m}")
            topm = [(d, c) for d, c in mark_ok.most_common(15) if c >= need_m]
            if topm:
                for d, c in topm:
                    lines.append(f"  LOCK? mark+4+{d} day-delta {c}/{marked_pairs}")
            else:
                for d, c in mark_ok.most_common(8):
                    lines.append(f"  top mark+4+{d} {c}/{marked_pairs}")

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
