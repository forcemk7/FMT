#!/usr/bin/env python3
"""Dump after-double + hunt Tem/Pro/Con/Pre anchors across the locked 5."""

from __future__ import annotations

import json
import mmap
import os
import struct
import tempfile
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-cal5-dump.txt"
ZSTD_OFF = 26
ATTR_LOOKBACK = 24_000
PERSON_HEAD = 512 * 1024 * 1024

MENTAL = [
    "aggression", "anticipation", "bravery", "vision", "decisions",
    "determination", "flair", "leadership", "offTheBall", "positioning",
    "teamwork", "workRate", "composure", "concentration",
]


def d5(b: int) -> int:
    return int(round(b / 5))


def is_attrish(buf: bytes, i: int) -> bool:
    if i + 69 > len(buf):
        return False
    if buf[i + 34] or buf[i + 35] or buf[i + 43] != 0x01:
        return False
    return sum(1 for x in buf[i : i + 22] if 25 <= x <= 105) >= 12


def score_attr_window(window: bytes):
    by_u16: dict[int, list[tuple[int, bytes]]] = defaultdict(list)
    start = 0
    while True:
        z = window.find(b"\x00\x00", start)
        if z < 0 or z + 35 > len(window):
            break
        i = z - 34
        if i >= 0 and z == i + 34 and is_attrish(window, i):
            rec = window[i : i + 69]
            u16 = struct.unpack_from("<H", rec, 36)[0]
            by_u16[u16].append((i, rec))
            start = z + 69
        else:
            start = z + 1
    if not by_u16:
        return None
    best_u16 = max(
        by_u16.keys(),
        key=lambda u: (len(by_u16[u]), max(r[1][23] for r in by_u16[u]), max(r[0] for r in by_u16[u])),
    )
    cards = by_u16[best_u16]
    cards.sort(key=lambda t: (t[1][23], t[0]))
    return cards[-1]


def find_ca(mm, uid: int, det, lea):
    pat = struct.pack("<II", uid, uid)
    hits = []
    j = mm.find(pat, 0, PERSON_HEAD)
    while j >= 0 and len(hits) < 16:
        hits.append(j)
        j = mm.find(pat, j + 1, PERSON_HEAD)
    fallback = []
    for dab in hits:
        lo = max(0, dab - ATTR_LOOKBACK)
        hit = score_attr_window(bytes(mm[lo:dab]))
        if not hit:
            continue
        off, rec = hit
        ment = {k: d5(rec[i]) for i, k in enumerate(MENTAL)}
        if det is not None and ment["determination"] != det:
            fallback.append((lo + off, dab, ment, rec))
            continue
        if lea is not None and ment["leadership"] != lea:
            fallback.append((lo + off, dab, ment, rec))
            continue
        if det is None and not (14 <= ment["determination"] <= 20):
            fallback.append((lo + off, dab, ment, rec))
            continue
        return lo + off, dab, ment, rec
    return fallback[0] if fallback else None


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-cal5-", suffix=".bin")
    os.close(fd)
    tmp = Path(name)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(ZSTD_OFF)
        r = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = r.read(8 << 20)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                out.write(b)
        finally:
            r.close()
    return tmp


def in_band(v, band):
    return band[0] <= v <= band[1]


def main() -> int:
    cal = json.loads(CAL.read_text(encoding="utf-8"))
    players = cal["players"]
    lines = []
    tmp = decompress(SAVE)
    loci = {}
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in players:
                found = find_ca(mm, p["uid"], p.get("determination"), p.get("leadership"))
                if not found:
                    lines.append(f"MISS {p['name']}")
                    continue
                card, dbl, ment, rec = found
                after = bytes(mm[dbl : dbl + 256])
                before = bytes(mm[max(0, dbl - 256) : dbl])
                after_card = bytes(mm[card + 69 : card + 69 + 256])
                loci[p["name"]] = {
                    "p": p,
                    "card": card,
                    "dbl": dbl,
                    "ment": ment,
                    "rec": rec,
                    "after": after,
                    "before": before,
                    "after_card": after_card,
                }
                lines.append(f"=== {p['name']} card={card} dbl={dbl} Det={ment['determination']} Lea={ment['leadership']} ===")
                for off in range(0, 128, 16):
                    chunk = after[off : off + 16]
                    lines.append(f"  after+{off:03d}: {' '.join(f'{b:02x}' for b in chunk)}")
                # 01-runs
                for i in range(len(after) - 3):
                    if after[i : i + 3] == b"\x01\x01\x01" and (i == 0 or after[i - 1] != 1):
                        ctx = after[max(0, i - 4) : i + 24]
                        lines.append(f"  01-run@{i}: {ctx.hex(' ')}")
                mid = list(rec[44:55])
                lines.append(f"  mid11 raw={mid} d5={[d5(x) for x in mid]}")

            # Distinctive Tem/Pro/Con/Pre byte hunts in after/before/after_card windows
            lines.append("\n=== distinctive value offsets (rel to double) ===")
            queries = [
                ("Sam Kizza", "temperament", 15, "raw"),
                ("Paco Suárez", "professionalism", 20, "raw"),
                ("Marco Tassinari", "temperament", None, "raw_band"),  # 3-6
                ("Dennis Seimen", "controversy", None, "raw_band_con"),  # 1-5
                ("Yoan Robert", "pressure", None, "raw_band_pre"),  # 17-19
            ]

            # For each player, find offsets of lock values in after blob
            def band_of(name, attr):
                return next(x["bands"][attr] for x in players if x["name"] == name)

            # Rank shared card-relative and double-relative offsets for Tem:
            # Tassinari in 3-6, Kizza==15, Paco in 10-20, Seimen in 10-14, Yoan in 15-20
            lines.append("\n=== Tem shared offsets (raw 1-20) ===")
            for region in ("after", "before", "after_card"):
                hits = []
                for off in range(256):
                    vals = {}
                    ok = True
                    for name, loc in loci.items():
                        blob = loc[region]
                        if off >= len(blob):
                            ok = False
                            break
                        v = blob[off]
                        vals[name] = v
                        if not (1 <= v <= 20):
                            ok = False
                            break
                        if not in_band(v, band_of(name, "temperament")):
                            ok = False
                            break
                        locks = loc["p"].get("locks") or {}
                        if "temperament" in locks and v != locks["temperament"]:
                            ok = False
                            break
                    if ok:
                        hits.append((off, vals))
                lines.append(f"region={region} Tem hits={len(hits)}")
                for off, vals in hits[:15]:
                    pretty = ", ".join(f"{n.split()[0]}={vals[n]}" for n in sorted(vals))
                    lines.append(f"  +{off}: {pretty}")

            for attr in ("professionalism", "pressure", "controversy", "sportsmanship", "loyalty", "ambition"):
                lines.append(f"\n=== {attr} shared offsets (raw 1-20) ===")
                for region in ("after", "before", "after_card"):
                    hits = []
                    for off in range(256):
                        vals = {}
                        ok = True
                        for name, loc in loci.items():
                            blob = loc[region]
                            if off >= len(blob):
                                ok = False
                                break
                            v = blob[off]
                            vals[name] = v
                            if not (1 <= v <= 20):
                                ok = False
                                break
                            if not in_band(v, band_of(name, attr)):
                                ok = False
                                break
                            locks = loc["p"].get("locks") or {}
                            if attr in locks and v != locks[attr]:
                                ok = False
                                break
                        if ok:
                            hits.append((off, vals))
                    lines.append(f"region={region} hits={len(hits)}")
                    for off, vals in hits[:10]:
                        pretty = ", ".join(f"{n.split()[0]}={vals[n]}" for n in sorted(vals))
                        lines.append(f"  +{off}: {pretty}")

            # mid11 across players
            lines.append("\n=== CA mid11 comparison ===")
            for name, loc in loci.items():
                mid = list(loc["rec"][44:55])
                lines.append(f"{name}: raw={mid} d5={[d5(x) for x in mid]}")

        finally:
            mm.close()
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in ("===", "hits=", "Tem hits", "01-run", "mid11", "MISS", "card=")):
            if line.startswith("  after+"):
                continue
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
