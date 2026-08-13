#!/usr/bin/env python3
"""
Hunt age as a small integer near person double-UID.

Uses screenshot DOBs in tmp/fm-spike/dob-hunt-players.json, derives ages from
a candidate game date (default mid-2039 from fixture ages), then finds relative
offsets where age_u8 / age_u16 coincide across players.
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
PLAYERS_PATH = ROOT / "tmp" / "fm-spike" / "dob-hunt-players.json"
FIXTURE = ROOT / "data" / "fixtures" / "save-players.json"
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
OUT = ROOT / "tmp" / "fm-spike" / "age-hunt-results.txt"
AGED = ROOT / "tmp" / "fm-spike" / "age-hunt-players.json"
PERSON_HEAD = 512 * 1024 * 1024
RADIUS = 2048

# Fixture Seimen 33 / Bandeira 24 imply roughly mid-2039 before Seimen's Dec birthday.
GAME_DATES = [
    date(2039, 7, 1),
    date(2039, 5, 15),
    date(2039, 1, 1),
    date(2038, 7, 1),
]


def age_on(dob: date, when: date) -> int:
    years = when.year - dob.year
    if (when.month, when.day) < (dob.month, dob.day):
        years -= 1
    return years


def load_players(game: date) -> list[dict]:
    raw = json.loads(PLAYERS_PATH.read_text(encoding="utf-8"))
    fixture_ages = {
        int(p["uid"]): int(p["age"])
        for p in json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
        if p.get("age") is not None
    }
    out: list[dict] = []
    for p in raw:
        y, m, d = map(int, p["dob"].split("-"))
        dob = date(y, m, d)
        age = fixture_ages.get(int(p["uid"]), age_on(dob, game))
        out.append({**p, "age": age, "gameDate": game.isoformat()})
    return out


def collect_doubles(buf: mmap.mmap, uid: int, limit: int = 12) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(buf), PERSON_HEAD)
    j = buf.find(pat, 0, end)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = buf.find(pat, j + 1, end)
    return hits


def score_person_double(buf: mmap.mmap, dab: int) -> int:
    blob = bytes(buf[dab : dab + 160])
    score = 0
    if b"\x01\x01\x01" in blob[8:120]:
        score += 5
    if len(blob) > 8 and blob[8] in (1, 2):
        score += 1
    if bytes.fromhex("01006c07") in blob:
        score += 3
    # Prefer records that look like personIndex@+31 is smallish
    if len(blob) >= 35:
        pi = struct.unpack_from("<I", blob, 31)[0]
        if 0 < pi < 200_000:
            score += 4
    return score


def best_double(buf: mmap.mmap, doubles: list[int]) -> int | None:
    if not doubles:
        return None
    return sorted(doubles, key=lambda d: (-score_person_double(buf, d), d))[0]


def scan_ages(
    mm: mmap.mmap, players: list[dict], *, radius: int = RADIUS
) -> tuple[list[str], Counter[int], Counter[int]]:
    lines: list[str] = []
    u8_hits: Counter[int] = Counter()
    u16_hits: Counter[int] = Counter()
    usable = 0

    for p in players:
        uid = int(p["uid"])
        age = int(p["age"])
        doubles = collect_doubles(mm, uid)
        dab = best_double(mm, doubles)
        if dab is None:
            lines.append(f"## {p['name']} uid={uid} age={age} NO double")
            continue
        usable += 1
        lo = max(0, dab - radius)
        hi = min(len(mm), dab + radius + 2)
        win = bytes(mm[lo:hi])
        rel0 = dab - lo
        age_u8_offs: list[int] = []
        age_u16_offs: list[int] = []
        for i, b in enumerate(win):
            rel = i - rel0
            if -radius <= rel <= radius and b == age:
                age_u8_offs.append(rel)
                u8_hits[rel] += 1
        for i in range(0, len(win) - 1):
            rel = i - rel0
            if -radius <= rel <= radius and struct.unpack_from("<H", win, i)[0] == age:
                age_u16_offs.append(rel)
                u16_hits[rel] += 1
        # also near zeros padded age±1 as soft signal (birthday / season edge)
        soft: list[str] = []
        for delta in (-1, 1):
            a2 = age + delta
            if not (1 <= a2 <= 60):
                continue
            n = sum(1 for b in win[rel0 - 64 : rel0 + 64] if b == a2)
            if n:
                soft.append(f"age{delta:+d}@±64×{n}")

        lines.append(
            f"## {p['name']} uid={uid} age={age} best={dab} "
            f"u8×{len(age_u8_offs)} u16×{len(age_u16_offs)} "
            f"{' '.join(soft)}"
        )
        if age_u8_offs:
            near = [o for o in age_u8_offs if abs(o) <= 256]
            lines.append(f"  age_u8 near±256: {near[:24]}")
        if age_u16_offs:
            near = [o for o in age_u16_offs if abs(o) <= 256]
            lines.append(f"  age_u16 near±256: {near[:24]}")

    lines.append(f"\n## usable players with doubles: {usable}/{len(players)}")
    return lines, u8_hits, u16_hits


def consensus_lines(
    label: str, hits: Counter[int], n_players: int, *, min_frac: float = 0.6
) -> list[str]:
    need = max(3, int(n_players * min_frac + 0.999))
    out = [f"\n## consensus {label} (need ≥{need}/{n_players})"]
    ranked = [(off, c) for off, c in hits.most_common(40) if c >= need]
    if not ranked:
        out.append("  (none)")
        # still show top noisy hits
        out.append("  top10 anyway:")
        for off, c in hits.most_common(10):
            out.append(f"    rel={off:+6d} players={c}")
        return out
    for off, c in ranked:
        out.append(f"  LOCK? rel={off:+6d} players={c}/{n_players}")
    return out


def verify_offset(
    mm: mmap.mmap, players: list[dict], off: int, *, kind: str
) -> list[str]:
    lines = [f"\n## verify {kind} @ rel={off:+d}"]
    ok = 0
    for p in players:
        uid = int(p["uid"])
        age = int(p["age"])
        dab = best_double(mm, collect_doubles(mm, uid))
        if dab is None:
            lines.append(f"  {p['name']}: no double")
            continue
        pos = dab + off
        if not (0 <= pos < len(mm) - 1):
            lines.append(f"  {p['name']}: OOB")
            continue
        if kind == "u8":
            got = mm[pos]
        else:
            got = struct.unpack_from("<H", mm, pos)[0]
        match = got == age
        ok += int(match)
        lines.append(
            f"  {'OK' if match else 'MISS'} {p['name']}: got={got} want={age} abs={pos}"
        )
    lines.append(f"  matched {ok}/{len(players)}")
    return lines


def main() -> None:
    assert DECOMP.exists(), f"missing decomp cache {DECOMP}"
    game = GAME_DATES[0]
    players = load_players(game)
    AGED.write_text(json.dumps(players, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines: list[str] = [
        f"save={SAVE.name}",
        f"gameDate={game.isoformat()} (primary)",
        f"players={len(players)}",
        f"radius=±{RADIUS}",
        "",
    ]
    # show age range
    ages = sorted({int(p["age"]) for p in players})
    lines.append(f"age values: {ages}")
    lines.append("")

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            body, u8_hits, u16_hits = scan_ages(mm, players)
            lines.extend(body)
            lines.extend(consensus_lines("age_u8", u8_hits, len(players)))
            lines.extend(consensus_lines("age_u16", u16_hits, len(players)))

            # verify best candidates
            for off, c in u8_hits.most_common(5):
                if c >= max(3, len(players) // 2):
                    lines.extend(verify_offset(mm, players, off, kind="u8"))
            for off, c in u16_hits.most_common(5):
                if c >= max(3, len(players) // 2):
                    lines.extend(verify_offset(mm, players, off, kind="u16"))

            # try alternate game dates for primary u8 consensus shift
            lines.append("\n## alternate gameDate age_u8 top offsets")
            for g in GAME_DATES[1:]:
                alt = load_players(g)
                _, a8, _ = scan_ages(mm, alt)
                top = a8.most_common(3)
                lines.append(
                    f"  {g.isoformat()} ages={[p['age'] for p in alt[:5]]}… top={top}"
                )
                need = max(3, int(len(alt) * 0.6 + 0.999))
                locked = [(o, c) for o, c in a8.most_common(20) if c >= need]
                if locked:
                    lines.append(f"    LOCK candidates: {locked[:5]}")
        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-60:]))
    print("wrote", OUT)
    print("wrote", AGED)


if __name__ == "__main__":
    main()
