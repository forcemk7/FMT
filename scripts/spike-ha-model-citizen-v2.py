#!/usr/bin/env python3
"""
Deeper HA locus spike for Contreras + Kizza.

1) Confirm CA card + dump mid-card bytes (not mental/phys/tech).
2) Search large windows excluding 69b CA cards for Tem==15 (Kizza lock).
3) Try several HA field orderings with *5 encoding.
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
OUT = ROOT / "tmp" / "fm-spike" / "ha-model-citizen-v2.txt"
ZSTD_OFF = 26
ATTR_LOOKBACK = 20_000
PERSON_HEAD = 512 * 1024 * 1024

CONTRERAS = 2002220356
KIZZA = 2002185604
DET = {"contreras": 15, "kizza": 16}
LEA = {"contreras": 10, "kizza": 15}

ORDERS = {
    "user": [
        "professionalism",
        "pressure",
        "ambition",
        "importantMatches",
        "sportsmanship",
        "temperament",
        "loyalty",
        "controversy",
    ],
    "gs1": [
        "professionalism",
        "ambition",
        "loyalty",
        "pressure",
        "temperament",
        "sportsmanship",
        "controversy",
        "importantMatches",
    ],
    "gs2": [
        "ambition",
        "loyalty",
        "pressure",
        "professionalism",
        "sportsmanship",
        "temperament",
        "controversy",
        "importantMatches",
    ],
    "tem7": [  # temperament at index 7 (last)
        "professionalism",
        "ambition",
        "loyalty",
        "pressure",
        "sportsmanship",
        "controversy",
        "importantMatches",
        "temperament",
    ],
    "tem5": [
        "professionalism",
        "ambition",
        "loyalty",
        "pressure",
        "sportsmanship",
        "temperament",
        "controversy",
        "importantMatches",
    ],
}

BANDS_C = {
    "professionalism": (15, 20),
    "pressure": (15, 20),
    "ambition": (12, 20),
    "importantMatches": (1, 20),
    "sportsmanship": (15, 20),
    "temperament": (15, 20),
    "loyalty": (15, 20),
    "controversy": (1, 14),
}
BANDS_K = dict(BANDS_C)
BANDS_K["temperament"] = (15, 15)

MENTAL = [
    "aggression",
    "anticipation",
    "bravery",
    "vision",
    "decisions",
    "determination",
    "flair",
    "leadership",
    "offTheBall",
    "positioning",
    "teamwork",
    "workRate",
    "composure",
    "concentration",
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
        key=lambda u: (
            len(by_u16[u]),
            max(r[1][23] for r in by_u16[u]),
            max(r[0] for r in by_u16[u]),
        ),
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


def find_ca(mm, uid: int, want_det: int, want_lea: int):
    for dab in collect_doubles(mm, uid):
        lo = max(0, dab - ATTR_LOOKBACK)
        hit = score_attr_window(bytes(mm[lo:dab]))
        if not hit:
            continue
        off, rec = hit
        ment = {k: d5(rec[i]) for i, k in enumerate(MENTAL)}
        if ment["determination"] == want_det and ment["leadership"] == want_lea:
            return lo + off, dab, rec, ment
    return None


def ok_bands(vals: dict, bands: dict) -> bool:
    for k, (lo, hi) in bands.items():
        v = vals.get(k)
        if v is None or not (lo <= v <= hi):
            return False
    return True


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-ha2-", suffix=".bin")
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


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    t0 = time.perf_counter()
    print("decompress…", flush=True)
    tmp = decompress(SAVE)
    print(f"tmp bytes={tmp.stat().st_size}", flush=True)

    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            c = find_ca(mm, CONTRERAS, DET["contreras"], LEA["contreras"])
            k = find_ca(mm, KIZZA, DET["kizza"], LEA["kizza"])
            if not c or not k:
                lines.append(f"CA miss c={bool(c)} k={bool(k)}")
                OUT.write_text("\n".join(lines), encoding="utf-8")
                return 1
            c_card, c_dbl, c_rec, c_ment = c
            k_card, k_dbl, k_rec, k_ment = k
            lines.append(f"Contreras card={c_card} double={c_dbl} ment={c_ment}")
            lines.append(f"Kizza     card={k_card} double={k_dbl} ment={k_ment}")

            for label, rec in (("Contreras", c_rec), ("Kizza", k_rec)):
                lines.append(f"\n--- {label} mid-card bytes ---")
                lines.append(f"  raw[22:44]={list(rec[22:44])}")
                lines.append(f"  d5[22:44]={[d5(x) for x in rec[22:44]]}")
                lines.append(f"  raw[37:44]={list(rec[37:44])} d5={[d5(x) for x in rec[37:44]]}")
                # try every 8-byte window inside 22..55 as HA under each order
                for ord_name, keys in ORDERS.items():
                    for base in range(22, 48):
                        chunk = rec[base : base + 8]
                        if len(chunk) < 8:
                            continue
                        vals = {keys[i]: d5(chunk[i]) for i in range(8)}
                        if ok_bands(vals, BANDS_C if label == "Contreras" else BANDS_K):
                            lines.append(
                                f"  HIT midcard order={ord_name} base={base} {vals}"
                            )

            # Large window search excluding CA cards
            lines.append("\n=== window search (exclude CA 69b cards) ===")
            results: list[tuple[int, str, str, int, dict]] = []
            for who, card, dbl, bands in (
                ("Contreras", c_card, c_dbl, BANDS_C),
                ("Kizza", k_card, k_dbl, BANDS_K),
            ):
                spans = [
                    (max(0, card - 4096), card),
                    (card + 69, min(len(mm), card + 69 + 8192)),
                    (max(0, dbl - 4096), dbl),
                    (dbl + 8, min(len(mm), dbl + 8 + 8192)),
                ]
                # merge and skip CA card
                for lo, hi in spans:
                    blob = bytearray(mm[lo:hi])
                    # blank out CA if overlapping
                    ca_lo, ca_hi = card, card + 69
                    for i in range(len(blob)):
                        abs_i = lo + i
                        if ca_lo <= abs_i < ca_hi:
                            blob[i] = 0
                    for ord_name, keys in ORDERS.items():
                        tem_i = keys.index("temperament")
                        for i in range(0, len(blob) - 7):
                            raw = blob[i : i + 8]
                            if raw[tem_i] == 0:
                                continue
                            vals_d5 = {keys[j]: d5(raw[j]) for j in range(8)}
                            if who == "Kizza" and vals_d5["temperament"] != 15:
                                continue
                            if not ok_bands(vals_d5, bands):
                                continue
                            # reject if looks like mental CA header (too many mid values in aggression positions)
                            if sum(1 for v in vals_d5.values() if 8 <= v <= 18) >= 7 and vals_d5.get("importantMatches", 0) >= 10:
                                # still allow — but mark dense
                                pass
                            results.append((20, who, ord_name, lo + i, vals_d5))

                            vals_raw = {keys[j]: int(raw[j]) for j in range(8)}
                            if ok_bands(vals_raw, bands):
                                if who != "Kizza" or vals_raw["temperament"] == 15:
                                    results.append((15, who, ord_name + "/raw", lo + i, vals_raw))

            # Prefer hits that exist for BOTH at same order + same delta from card
            lines.append(f"total unilateral hits={len(results)}")
            by_pair: dict[tuple, list] = defaultdict(list)
            for score, who, ord_name, abs_off, vals in results:
                by_pair[(who, ord_name)].append((abs_off, vals))

            lines.append("\n=== shared card-relative deltas ===")
            for ord_name in ORDERS:
                c_hits = by_pair.get(("Contreras", ord_name), []) + by_pair.get(
                    ("Contreras", ord_name + "/raw"), []
                )
                k_hits = by_pair.get(("Kizza", ord_name), []) + by_pair.get(
                    ("Kizza", ord_name + "/raw"), []
                )
                c_map = {off - c_card: (off, vals) for off, vals in c_hits}
                k_map = {off - k_card: (off, vals) for off, vals in k_hits}
                shared = sorted(set(c_map) & set(k_map))
                lines.append(f"order={ord_name} shared_card_deltas={len(shared)}")
                for delta in shared[:30]:
                    lines.append(f"  delta={delta}")
                    lines.append(f"    C {c_map[delta][1]}")
                    lines.append(f"    K {k_map[delta][1]}")

            lines.append("\n=== shared double-relative deltas ===")
            for ord_name in ORDERS:
                c_hits = by_pair.get(("Contreras", ord_name), []) + by_pair.get(
                    ("Contreras", ord_name + "/raw"), []
                )
                k_hits = by_pair.get(("Kizza", ord_name), []) + by_pair.get(
                    ("Kizza", ord_name + "/raw"), []
                )
                c_map = {off - c_dbl: (off, vals) for off, vals in c_hits}
                k_map = {off - k_dbl: (off, vals) for off, vals in k_hits}
                shared = sorted(set(c_map) & set(k_map))
                lines.append(f"order={ord_name} shared_double_deltas={len(shared)}")
                for delta in shared[:30]:
                    lines.append(f"  delta={delta}")
                    lines.append(f"    C {c_map[delta][1]}")
                    lines.append(f"    K {k_map[delta][1]}")

            # Dump 128 bytes after each CA card for eyeballing
            lines.append("\n=== hex after CA card (128B) ===")
            for label, card in (("Contreras", c_card), ("Kizza", k_card)):
                blob = bytes(mm[card + 69 : card + 69 + 128])
                lines.append(f"{label}:")
                for i in range(0, len(blob), 16):
                    chunk = blob[i : i + 16]
                    hx = " ".join(f"{b:02x}" for b in chunk)
                    d = " ".join(f"{d5(b):2d}" for b in chunk)
                    lines.append(f"  +{i:03d}: {hx} | {d}")

            lines.append("\n=== hex before double (128B) ===")
            for label, dbl in (("Contreras", c_dbl), ("Kizza", k_dbl)):
                blob = bytes(mm[dbl - 128 : dbl])
                lines.append(f"{label}:")
                for i in range(0, len(blob), 16):
                    chunk = blob[i : i + 16]
                    hx = " ".join(f"{b:02x}" for b in chunk)
                    d = " ".join(f"{d5(b):2d}" for b in chunk)
                    lines.append(f"  -{128-i:03d}: {hx} | {d}")
        finally:
            mm.close()

    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass

    lines.append(f"\nelapsedMs={int((time.perf_counter()-t0)*1000)}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}", flush=True)
    for line in lines:
        if "shared_" in line or line.startswith("Contreras card") or line.startswith("Kizza") or "HIT midcard" in line or "total unilateral" in line:
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
