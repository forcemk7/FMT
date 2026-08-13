"""Fixed 69B structure hunt (+43==01) + lock physical@+14; probe mental order."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/band69-locked.txt")
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


def flat(p: dict) -> dict[str, int]:
    out = {}
    for g, attrs in p["attributes"].items():
        for k, v in attrs.items():
            out[f"{g}.{k}"] = int(v)
    return out


def phys(p):
    a = flat(p)
    return [a[f"physical.{k}"] for k in [
        "acceleration", "agility", "balance", "jumpingReach",
        "naturalFitness", "pace", "stamina", "strength",
    ]]


def ment(p):
    a = flat(p)
    return [a[f"mental.{k}"] for k in [
        "aggression", "anticipation", "bravery", "composure",
        "concentration", "decisions", "determination", "flair",
        "leadership", "offTheBall", "positioning", "teamwork",
        "vision", "workRate",
    ]]


def tech(p):
    a = flat(p)
    keys = [
        "crossing", "dribbling", "finishing", "firstTouch", "heading",
        "longShots", "marking", "passing", "tackling", "technique",
    ]
    if f"technical.{keys[0]}" not in a:
        return None
    return [a[f"technical.{k}"] for k in keys]


def phys_ok(buf, off, expects, tol=1):
    """tol on DISPLAY units after round(b/5)."""
    if off + 8 > len(buf):
        return 0
    ok = 0
    for i, e in enumerate(expects):
        if abs(round(buf[off + i] / 5) - e) <= tol:
            ok += 1
    return ok


def is_rec(buf, i) -> bool:
    if i + 55 > len(buf):
        return False
    if buf[i + 22] != 0x07 or buf[i + 24] != 0x9C:
        return False
    if buf[i + 34] != 0 or buf[i + 35] != 0:
        return False
    if buf[i + 43] != 0x01:  # FIXED: was wrongly +42
        return False
    # attr-ish head
    mid = sum(1 for x in buf[i : i + 22] if 30 <= x <= 100)
    return mid >= 14


def main() -> None:
    lines: list[str] = []
    lines.append("LOCK: physical@+14 as 1-100, display=round(byte/5)")
    lines.append("Band sta/str within ±1 display of fixture; others exact.\n")

    for name, dbl in DOUBLE.items():
        win = extract(dbl, 65536, before=65536)
        hits = []
        for i in range(0, len(win) - 69):
            if not is_rec(win, i):
                continue
            abs_i = dbl - 65536 + i
            u16 = struct.unpack_from("<H", win, i + 36)[0]
            pok = phys_ok(win, i + 14, phys(PLAYERS[name]), tol=1)
            mok = 0
            for off in range(0, 9):
                # count mental matches screen order
                m = ment(PLAYERS[name])
                ok = sum(
                    1
                    for j, e in enumerate(m)
                    if i + off + j < len(win)
                    and abs(round(win[i + off + j] / 5) - e) <= 1
                )
                mok = max(mok, ok)
            hits.append((abs_i, u16, pok, mok, list(win[i : i + 22])))
        hits.sort(key=lambda t: (-t[2], -t[3], abs(t[0] - dbl)))
        lines.append(f"## {name} 69B-shaped near dbl (±64KB): n={len(hits)}")
        for abs_i, u16, pok, mok, head in hits[:20]:
            lines.append(
                f"  @{abs_i} rel={abs_i-dbl:+d} u16={u16} phys@+14={pok}/8 mental_best~={mok}/14"
            )
            if pok >= 5 or mok >= 8:
                disp = [round(x / 5) for x in head]
                lines.append(f"    head_disp={disp}")
                lines.append(f"    head_raw={head}")

    # Count how many records share Band u16 globally (cap)
    lines.append("\n======== Band u16=0xA0B4 record count (sample stream) ========")
    pat = struct.pack("<H", 0xA0B4)
    # Only count those with 00 00 before and 00 00 00 00 00 after then 01? 
    # Simpler: count u16 with preceding 07 ?? 9c within -20
    count = 0
    abs_base = 0
    carry = b""
    examples = []
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
                start = 0
                while True:
                    j = data.find(pat, start)
                    if j < 0:
                        break
                    abs_hit = chunk_start + j
                    if abs_hit >= abs_base and j >= 36:
                        # check if this is +36 of a rec
                        rec_i = j - 36
                        if rec_i >= 0 and is_rec(data, rec_i):
                            count += 1
                            if len(examples) < 8:
                                examples.append(chunk_start + rec_i)
                    start = j + 1
                abs_base += len(block)
                carry = data[-80:]
        finally:
            reader.close()
    lines.append(f"records with u16=0xA0B4: {count}")
    lines.append(f"examples: {examples}")

    # Mental: try all rotations / find best permutation of last 8 is expensive;
    # instead: treat first 6 (strong matches) as anchored; for remaining 8 bytes
    # assign remaining 8 mental attrs by min L1 on ×5
    lines.append("\n======== Band mental: greedy assign bytes[0..13] ========")
    rec = extract(264923389, 69)
    names = [
        "aggression", "anticipation", "bravery", "composure", "concentration",
        "decisions", "determination", "flair", "leadership", "offTheBall",
        "positioning", "teamwork", "vision", "workRate",
    ]
    a = flat(PLAYERS["Patrick Bandeira"])
    # Hungarian-ish greedy: for each byte pick closest remaining attr
    remaining = set(names)
    assignment = []
    for i in range(14):
        got = rec[i]
        best = None
        for nm in remaining:
            exp = a[f"mental.{nm}"] * 5
            diff = abs(got - exp)
            if best is None or diff < best[0]:
                best = (diff, nm, a[f"mental.{nm}"], got)
        assert best
        remaining.remove(best[1])
        assignment.append((i, best[1], best[2], best[3], best[0]))
    ok = sum(1 for *_, d in assignment if d <= 5)
    lines.append(f"greedy matches within ×5±5: {ok}/14 (warning: order not preserved)")
    for i, nm, disp, got, diff in assignment:
        lines.append(
            f"  +{i}: byte={got} -> {nm} fixture={disp} (exp={disp*5}, d={diff})"
        )

    # Tech before physical? bytes don't exist in 0-13 if mental takes them.
    # Search tech×5 pack (±2) in ±64KB of Band double
    lines.append("\n======== Band tech×5 pack near double ========")
    t = tech(PLAYERS["Patrick Bandeira"])
    assert t
    needle = bytes(x * 5 for x in t)
    win = extract(DOUBLE["Patrick Bandeira"], 65536, before=65536)
    # fuzzy: allow each byte ±2
    hits = 0
    for i in range(len(win) - 10):
        ok = all(abs(win[i + j] - needle[j]) <= 2 for j in range(10))
        if ok:
            hits += 1
            if hits <= 5:
                abs_i = DOUBLE["Patrick Bandeira"] - 65536 + i
                lines.append(f"  tech~ @{abs_i} rel={abs_i-DOUBLE['Patrick Bandeira']:+d}")
    lines.append(f"  total fuzzy tech hits: {hits}")

    lines.append(
        """
======== SUMMARY ========
- Physical block LOCKED at +14..+21 of 69B records (1-100, display=round/5).
- Band has a strip of these records ~11KB before double-UID (match/history snapshots?).
- Mental@+0 still NOT trusted: only first few screen-order fields fit fixture;
  either different order, mixed fields, or fixture mental is stale.
- Seimen/Müller: see shaped-hit counts above — if 0, they may use different
  phys needles or sit outside ±64KB / different record flavour (GK).
"""
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
