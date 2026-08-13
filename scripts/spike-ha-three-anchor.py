#!/usr/bin/env python3
"""
Three-anchor HA hunt:
  Paco Suárez       2000136577 — Model Professional / Media-friendly — Pro==20, Det=19, Lea=14
  Sam Kizza         2002185604 — Model Citizen / Evasive,Unflappable — Tem==15, Det=16, Lea=15
  Santiago Contreras 2002220356 — Model Citizen / Unflappable — Det=15, Lea=10

Find CA cards via Det/Lea, then search for Pro=20 (Paco) and Tem=15 (Kizza)
as *5 (raw 100 / 75) or raw display, looking for shared relative layout.
"""

from __future__ import annotations

import mmap
import os
import struct
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
OUT = ROOT / "tmp" / "fm-spike" / "ha-three-anchor.txt"
ZSTD_OFF = 26
ATTR_LOOKBACK = 24_000
PERSON_HEAD = 512 * 1024 * 1024

ANCHORS = {
    "Paco": {"uid": 2000136577, "det": 19, "lea": 14, "pro": 20},
    "Kizza": {"uid": 2002185604, "det": 16, "lea": 15, "tem": 15},
    "Contreras": {"uid": 2002220356, "det": 15, "lea": 10},
}

MENTAL = [
    "aggression", "anticipation", "bravery", "vision", "decisions",
    "determination", "flair", "leadership", "offTheBall", "positioning",
    "teamwork", "workRate", "composure", "concentration",
]

ORDERS = [
    ("user", ["professionalism", "pressure", "ambition", "importantMatches", "sportsmanship", "temperament", "loyalty", "controversy"]),
    ("gs1", ["professionalism", "ambition", "loyalty", "pressure", "temperament", "sportsmanship", "controversy", "importantMatches"]),
    ("gs2", ["ambition", "loyalty", "pressure", "professionalism", "sportsmanship", "temperament", "controversy", "importantMatches"]),
    ("pro_first", ["professionalism", "ambition", "pressure", "loyalty", "temperament", "sportsmanship", "controversy", "importantMatches"]),
]

# Intersection bands still useful for Contreras + Kizza Model Citizen core
BANDS = {
    # Soft bands from FMT history snapshot (Model Pro + Media-friendly union);
    # hard lock is Pro==20 only.
    "Paco": {
        "professionalism": (20, 20),
        "pressure": (1, 14),
        "ambition": (1, 20),
        "importantMatches": (1, 20),
        "sportsmanship": (1, 20),
        "temperament": (10, 20),
        "loyalty": (1, 10),
        "controversy": (6, 14),
    },
    "Kizza": {
        "professionalism": (15, 20),
        "pressure": (15, 20),
        "ambition": (12, 20),
        "importantMatches": (1, 20),
        "sportsmanship": (15, 20),
        "temperament": (15, 15),
        "loyalty": (15, 20),
        "controversy": (1, 14),
    },
    "Contreras": {
        "professionalism": (15, 20),
        "pressure": (15, 20),
        "ambition": (12, 20),
        "importantMatches": (1, 20),
        "sportsmanship": (15, 20),
        "temperament": (15, 20),
        "loyalty": (15, 20),
        "controversy": (1, 14),
    },
}


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


def collect_doubles(mm, uid: int) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits = []
    end = min(len(mm), PERSON_HEAD)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 12:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def find_ca(mm, uid: int, det: int, lea: int):
    for dab in collect_doubles(mm, uid):
        lo = max(0, dab - ATTR_LOOKBACK)
        hit = score_attr_window(bytes(mm[lo:dab]))
        if not hit:
            continue
        off, rec = hit
        ment = {k: d5(rec[i]) for i, k in enumerate(MENTAL)}
        if ment["determination"] == det and ment["leadership"] == lea:
            return lo + off, dab, rec, ment
    return None


def ok_bands(vals: dict, bands: dict) -> bool:
    for k, (lo, hi) in bands.items():
        v = vals.get(k)
        if v is None or not (lo <= v <= hi):
            return False
    return True


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-ha5-", suffix=".bin")
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


def scan_person(mm, card: int, dbl: int, bands: dict, hard: dict):
    """hard: {key: exact_display} using d5 or raw."""
    hits = []
    spans = [
        ("before_card", max(0, card - 512), card),
        ("after_card", card + 69, min(len(mm), card + 69 + 4096)),
        ("before_double", max(0, dbl - 512), dbl),
        ("after_double", dbl + 8, min(len(mm), dbl + 8 + 4096)),
        ("card_to_double", min(card + 69, dbl), max(card + 69, dbl)),
    ]
    ca_lo, ca_hi = card, card + 69
    for wname, lo, hi in spans:
        if hi - lo < 8:
            continue
        blob = bytearray(mm[lo:hi])
        for i in range(len(blob)):
            if ca_lo <= lo + i < ca_hi:
                blob[i] = 0
        for ord_name, keys in ORDERS:
            for enc in ("d5", "raw"):
                for i in range(0, len(blob) - 7):
                    raw = blob[i : i + 8]
                    if enc == "d5":
                        vals = {keys[j]: d5(raw[j]) for j in range(8)}
                    else:
                        vals = {keys[j]: int(raw[j]) for j in range(8)}
                    # hard locks
                    bad = False
                    for hk, hv in hard.items():
                        if vals.get(hk) != hv:
                            bad = True
                            break
                    if bad:
                        continue
                    if not ok_bands(vals, bands):
                        continue
                    hits.append((wname, ord_name, enc, lo + i, vals, lo + i - card, lo + i - dbl))
    return hits


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    t0 = time.perf_counter()
    print("decompress…", flush=True)
    tmp = decompress(SAVE)
    print(f"bytes={tmp.stat().st_size}", flush=True)

    loci = {}
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for name, meta in ANCHORS.items():
                found = find_ca(mm, meta["uid"], meta["det"], meta["lea"])
                if not found:
                    lines.append(f"{name}: CA MISS")
                    continue
                card, dbl, rec, ment = found
                loci[name] = {"card": card, "dbl": dbl, "ment": ment}
                lines.append(f"{name}: card={card} dbl={dbl} mentDet={ment['determination']} mentLea={ment['leadership']}")

            if len(loci) < 3:
                lines.append("Need all 3 CA loci")
                OUT.write_text("\n".join(lines), encoding="utf-8")
                return 1

            all_hits = {}
            for name, loc in loci.items():
                hard = {}
                if "pro" in ANCHORS[name]:
                    hard["professionalism"] = ANCHORS[name]["pro"]
                if "tem" in ANCHORS[name]:
                    hard["temperament"] = ANCHORS[name]["tem"]
                hits = scan_person(mm, loc["card"], loc["dbl"], BANDS[name], hard)
                all_hits[name] = hits
                lines.append(f"{name}: HA candidates={len(hits)} hard={hard}")
                for h in hits[:15]:
                    wname, ord_name, enc, abs_off, vals, dcard, ddbl = h
                    lines.append(
                        f"  win={wname} order={ord_name} enc={enc} abs={abs_off} dCard={dcard} dDbl={ddbl} {vals}"
                    )

            # Shared card-relative delta across all three for same order+enc
            lines.append("\n=== shared card deltas (all 3) ===")
            for ord_name, _keys in ORDERS:
                for enc in ("d5", "raw"):
                    maps = {}
                    for name, hits in all_hits.items():
                        m = {}
                        for h in hits:
                            if h[1] == ord_name and h[2] == enc:
                                m[h[5]] = h  # dCard
                        maps[name] = m
                    shared = set(maps["Paco"]) & set(maps["Kizza"]) & set(maps["Contreras"])
                    lines.append(f"order={ord_name} enc={enc} shared={len(shared)}")
                    for delta in sorted(shared, key=abs)[:20]:
                        lines.append(f"  delta={delta}")
                        for name in ("Paco", "Kizza", "Contreras"):
                            lines.append(f"    {name}: {maps[name][delta][4]}")

            lines.append("\n=== shared double deltas (all 3) ===")
            for ord_name, _keys in ORDERS:
                for enc in ("d5", "raw"):
                    maps = {}
                    for name, hits in all_hits.items():
                        m = {}
                        for h in hits:
                            if h[1] == ord_name and h[2] == enc:
                                m[h[6]] = h  # dDbl
                        maps[name] = m
                    shared = set(maps["Paco"]) & set(maps["Kizza"]) & set(maps["Contreras"])
                    lines.append(f"order={ord_name} enc={enc} shared={len(shared)}")
                    for delta in sorted(shared, key=abs)[:20]:
                        lines.append(f"  delta={delta}")
                        for name in ("Paco", "Kizza", "Contreras"):
                            lines.append(f"    {name}: {maps[name][delta][4]}")

            # Pairwise Paco×Kizza (sharp locks Pro=20 and Tem=15)
            lines.append("\n=== pairwise Paco×Kizza card deltas ===")
            for ord_name, _keys in ORDERS:
                for enc in ("d5", "raw"):
                    pm = {h[5]: h for h in all_hits["Paco"] if h[1] == ord_name and h[2] == enc}
                    km = {h[5]: h for h in all_hits["Kizza"] if h[1] == ord_name and h[2] == enc}
                    shared = set(pm) & set(km)
                    lines.append(f"order={ord_name} enc={enc} shared={len(shared)}")
                    for delta in sorted(shared, key=abs)[:30]:
                        lines.append(f"  delta={delta}")
                        lines.append(f"    Paco:  {pm[delta][4]}")
                        lines.append(f"    Kizza: {km[delta][4]}")

            # Dump after-double hex for Paco
            lines.append("\n=== Paco after double (192B) ===")
            dab = loci["Paco"]["dbl"]
            blob = bytes(mm[dab : dab + 192])
            for i in range(0, len(blob), 16):
                chunk = blob[i : i + 16]
                hx = " ".join(f"{b:02x}" for b in chunk)
                dv = " ".join(f"{d5(b):2d}" for b in chunk)
                lines.append(f"+{i:03d}: {hx} | {dv}")
        finally:
            mm.close()

    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass

    lines.append(f"\nelapsedMs={int((time.perf_counter()-t0)*1000)}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in ("card=", "candidates=", "shared=", "CA MISS", "pairwise", "order=")):
            if line.startswith("    "):
                continue
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
