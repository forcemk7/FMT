#!/usr/bin/env python3
"""
Spike: locate hidden-attribute bytes using Model Citizens as anchors.

Anchors (this Schalke save):
  Santiago Contreras 2002220356 — Model Citizen / Unflappable
    Det=15 Lea=10
    bands: Pro/Pre/Tem/Loy/Spo 15-20, Amb 12-20, Con 1-14
  Sam Kizza         2002185604 — Model Citizen / Evasive, Unflappable
    Det=16 Lea=15
    bands: same + Tem EXACTLY 15 (media lock)

Also pulls CA mental Det/Lea from the known 69-byte strip to confirm person locus.
"""

from __future__ import annotations

import json
import mmap
import os
import struct
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
OUT = ROOT / "tmp" / "fm-spike" / "ha-model-citizen.txt"
ZSTD_OFF = 26
UID_LO, UID_HI = 1_500_000_000, 2_200_000_000
ATTR_LOOKBACK = 20_000
PERSON_HEAD = 512 * 1024 * 1024

ANCHORS = {
    "Santiago Contreras": {
        "uid": 2002220356,
        "det": 15,
        "lea": 10,
        "bands": {
            "professionalism": (15, 20),
            "pressure": (15, 20),
            "ambition": (12, 20),
            # importantMatches unknown — accept 1-20 for scoring
            "importantMatches": (1, 20),
            "sportsmanship": (15, 20),
            "temperament": (15, 20),
            "loyalty": (15, 20),
            "controversy": (1, 14),
        },
        "exact": {},
    },
    "Sam Kizza": {
        "uid": 2002185604,
        "det": 16,
        "lea": 15,
        "bands": {
            "professionalism": (15, 20),
            "pressure": (15, 20),
            "ambition": (12, 20),
            "importantMatches": (1, 20),
            "sportsmanship": (15, 20),
            "temperament": (15, 15),  # media lock
            "loyalty": (15, 20),
            "controversy": (1, 14),
        },
        "exact": {"temperament": 15},
    },
}

# User order for HA tuple candidates
HA_KEYS = [
    "professionalism",
    "pressure",
    "ambition",
    "importantMatches",
    "sportsmanship",
    "temperament",
    "loyalty",
    "controversy",
]

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


def disp_byte(b: int) -> int:
    return int(round(b / 5))


def disp_bytes(b: bytes) -> list[int]:
    return [disp_byte(x) for x in b]


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
    abs_in_win, rec = cards[-1]
    return len(cards), abs_in_win, rec


def collect_doubles(mm, uid: int, limit: int = 16) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(mm), PERSON_HEAD)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def in_band(v: int, lo: int, hi: int) -> bool:
    return lo <= v <= hi


def score_ha_tuple(vals: list[int], bands: dict, exact: dict) -> int | None:
    if len(vals) != 8:
        return None
    if any(v < 1 or v > 20 for v in vals):
        return None
    score = 0
    for key, v in zip(HA_KEYS, vals):
        lo, hi = bands[key]
        if not in_band(v, lo, hi):
            return None
        score += 2
        if key in exact and v == exact[key]:
            score += 20
        # High Model Citizen traits prefer upper half
        if key != "controversy" and key != "importantMatches" and v >= 15:
            score += 1
        if key == "controversy" and v <= 10:
            score += 1
    return score


def candidate_tuples_from_bytes(raw: bytes) -> list[tuple[int, list[int], str]]:
    """Yield (offset, display_vals, encoding) candidates in a blob."""
    out: list[tuple[int, list[int], str]] = []
    # encoding A: raw already 1-20
    for i in range(0, len(raw) - 7):
        vals = list(raw[i : i + 8])
        out.append((i, vals, "u8_raw"))
    # encoding B: *5 (CA-style)
    for i in range(0, len(raw) - 7):
        vals = [disp_byte(b) for b in raw[i : i + 8]]
        out.append((i, vals, "u8_div5"))
    # encoding C: u16 LE display
    for i in range(0, len(raw) - 15, 2):
        vals = [struct.unpack_from("<H", raw, i + 2 * k)[0] for k in range(8)]
        if all(1 <= v <= 20 for v in vals):
            out.append((i, vals, "u16_raw"))
    # encoding D: u16 LE *5
    for i in range(0, len(raw) - 15, 2):
        vals = [disp_byte(struct.unpack_from("<H", raw, i + 2 * k)[0]) for k in range(8)]
        if all(1 <= v <= 20 for v in vals):
            out.append((i, vals, "u16_div5"))
    return out


def decompress_to_tmp(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-ha-", suffix=".bin")
    os.close(fd)
    tmp = Path(name)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(ZSTD_OFF)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                out.write(block)
        finally:
            reader.close()
    return tmp


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    t0 = time.perf_counter()
    lines.append(f"save={SAVE.name}")
    lines.append(f"anchors={list(ANCHORS)}")

    if not SAVE.is_file():
        lines.append("SAVE MISSING")
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return 1

    print("decompressing…", flush=True)
    tmp = decompress_to_tmp(SAVE)
    print(f"tmp={tmp} bytes={tmp.stat().st_size}", flush=True)

    loci: dict[str, dict] = {}
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for name, meta in ANCHORS.items():
                uid = meta["uid"]
                doubles = collect_doubles(mm, uid)
                lines.append(f"\n=== {name} uid={uid} doubles={len(doubles)} ===")
                for dab in doubles[:8]:
                    lines.append(f"  doubleAbs={dab}")

                best_card = None
                for dab in doubles:
                    lo = max(0, dab - ATTR_LOOKBACK)
                    window = bytes(mm[lo:dab])
                    scored = score_attr_window(window)
                    if not scored:
                        continue
                    n_ok, win_off, rec = scored
                    ment = {k: disp_byte(rec[i]) for i, k in enumerate(MENTAL)}
                    card_abs = lo + win_off
                    hit = (
                        ment.get("determination") == meta["det"]
                        and ment.get("leadership") == meta["lea"]
                    )
                    lines.append(
                        f"  caCardAbs={card_abs} n_ok={n_ok} "
                        f"det={ment.get('determination')} lea={ment.get('leadership')} "
                        f"matchDetLea={hit}"
                    )
                    if hit and (best_card is None or n_ok > best_card[0]):
                        best_card = (n_ok, card_abs, dab, rec, ment)

                if best_card is None and doubles:
                    # fall back: nearest CA strip to first double even if det/lea soft
                    dab = doubles[0]
                    lo = max(0, dab - ATTR_LOOKBACK)
                    scored = score_attr_window(bytes(mm[lo:dab]))
                    if scored:
                        n_ok, win_off, rec = scored
                        ment = {k: disp_byte(rec[i]) for i, k in enumerate(MENTAL)}
                        best_card = (n_ok, lo + win_off, dab, rec, ment)
                        lines.append(
                            f"  FALLBACK caCardAbs={best_card[1]} "
                            f"det={ment.get('determination')} lea={ment.get('leadership')}"
                        )

                if best_card is None:
                    lines.append("  NO CA CARD — cannot locus person")
                    continue

                _, card_abs, dab, rec, ment = best_card
                loci[name] = {
                    "uid": uid,
                    "cardAbs": card_abs,
                    "doubleAbs": dab,
                    "ment": ment,
                }

                # Scan windows relative to CA card + double for HA tuples
                windows = [
                    ("before_card", max(0, card_abs - 256), card_abs),
                    ("after_card", card_abs + 69, card_abs + 69 + 256),
                    ("before_double", max(0, dab - 512), dab),
                    ("after_double", dab + 8, dab + 8 + 512),
                    ("card_gap_to_double", min(card_abs, dab), max(card_abs + 69, dab + 8)),
                ]
                hits: list[tuple[int, int, list[int], str, str]] = []
                for wname, lo, hi in windows:
                    if hi - lo < 8:
                        continue
                    blob = bytes(mm[lo:hi])
                    for off, vals, enc in candidate_tuples_from_bytes(blob):
                        sc = score_ha_tuple(vals, meta["bands"], meta["exact"])
                        if sc is None:
                            continue
                        hits.append((sc, lo + off, vals, enc, wname))
                hits.sort(reverse=True)
                lines.append(f"  HA candidate hits (top 25 of {len(hits)}):")
                for sc, abs_off, vals, enc, wname in hits[:25]:
                    mapped = ", ".join(f"{k}={v}" for k, v in zip(HA_KEYS, vals))
                    lines.append(
                        f"    score={sc} abs={abs_off} enc={enc} win={wname} | {mapped}"
                    )

            # Cross-check: same relative offset from cardAbs for both players
            if len(loci) == 2:
                lines.append("\n=== cross-player relative offsets (cardAbs) ===")
                names = list(loci)
                a, b = names[0], names[1]
                # Re-scan with strict shared relative delta
                shared: list[tuple[int, dict[str, list[int]], str]] = []
                for delta in range(-256, 257):
                    for enc_mode in ("u8_raw", "u8_div5"):
                        ok = True
                        vals_by: dict[str, list[int]] = {}
                        for name, loc in loci.items():
                            abs_off = loc["cardAbs"] + delta
                            if abs_off < 0 or abs_off + 8 > len(mm):
                                ok = False
                                break
                            raw = bytes(mm[abs_off : abs_off + 8])
                            if enc_mode == "u8_raw":
                                vals = list(raw)
                            else:
                                vals = [disp_byte(x) for x in raw]
                            meta = ANCHORS[name]
                            sc = score_ha_tuple(vals, meta["bands"], meta["exact"])
                            if sc is None:
                                ok = False
                                break
                            vals_by[name] = vals
                        if ok:
                            shared.append((delta, vals_by, enc_mode))
                lines.append(f"shared cardAbs deltas: {len(shared)}")
                for delta, vals_by, enc in shared[:40]:
                    lines.append(f"  delta={delta} enc={enc}")
                    for name, vals in vals_by.items():
                        mapped = ", ".join(f"{k}={v}" for k, v in zip(HA_KEYS, vals))
                        lines.append(f"    {name}: {mapped}")

                lines.append("\n=== cross-player relative offsets (doubleAbs) ===")
                shared_d: list[tuple[int, dict[str, list[int]], str]] = []
                for delta in range(-512, 513):
                    for enc_mode in ("u8_raw", "u8_div5"):
                        ok = True
                        vals_by = {}
                        for name, loc in loci.items():
                            abs_off = loc["doubleAbs"] + delta
                            if abs_off < 0 or abs_off + 8 > len(mm):
                                ok = False
                                break
                            raw = bytes(mm[abs_off : abs_off + 8])
                            vals = list(raw) if enc_mode == "u8_raw" else [disp_byte(x) for x in raw]
                            meta = ANCHORS[name]
                            if score_ha_tuple(vals, meta["bands"], meta["exact"]) is None:
                                ok = False
                                break
                            vals_by[name] = vals
                        if ok:
                            shared_d.append((delta, vals_by, enc_mode))
                lines.append(f"shared doubleAbs deltas: {len(shared_d)}")
                for delta, vals_by, enc in shared_d[:40]:
                    lines.append(f"  delta={delta} enc={enc}")
                    for name, vals in vals_by.items():
                        mapped = ", ".join(f"{k}={v}" for k, v in zip(HA_KEYS, vals))
                        lines.append(f"    {name}: {mapped}")
        finally:
            mm.close()

    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass

    lines.append(f"\nelapsedMs={int((time.perf_counter()-t0)*1000)}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}", flush=True)
    # print summary only (avoid console encoding issues)
    for line in lines:
        if line.startswith("===") or "shared" in line or "matchDetLea" in line or line.startswith("  delta="):
            try:
                print(line)
            except UnicodeEncodeError:
                print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
