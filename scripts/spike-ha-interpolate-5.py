#!/usr/bin/env python3
"""
Interpolate HA byte layout across the locked 5-player narrow set.

For each shared relative offset (vs CA card / double-UID), collect raw and /5
values across all 5 players, then rank offsets that simultaneously satisfy
each player's band for a hypothesized attribute.

Hard locks:
  Paco.professionalism == 20
  Kizza.temperament == 15
Distinctive bands:
  Tassinari.temperament 3-6, controversy 15-20, sportsmanship 1-7
  Seimen.professionalism 18-19, controversy 1-5
  Yoan.pressure 17-19
"""

from __future__ import annotations

import json
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
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-interpolate-5.txt"
ZSTD_OFF = 26
ATTR_LOOKBACK = 24_000
PERSON_HEAD = 512 * 1024 * 1024
WIN = 512  # bytes after double / around card

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


def d5(b: int) -> int:
    return int(round(b / 5))


def in_band(v: int, band: list[int]) -> bool:
    return band[0] <= v <= band[1]


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
    while j >= 0 and len(hits) < 16:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def find_ca(mm, uid: int, det: int | None, lea: int | None):
    doubles = collect_doubles(mm, uid)
    candidates = []
    for dab in doubles:
        lo = max(0, dab - ATTR_LOOKBACK)
        hit = score_attr_window(bytes(mm[lo:dab]))
        if not hit:
            continue
        off, rec = hit
        ment = {k: d5(rec[i]) for i, k in enumerate(MENTAL)}
        ok = True
        if det is not None and ment["determination"] != det:
            ok = False
        if lea is not None and ment["leadership"] != lea:
            ok = False
        # Perfectionist fallback: det 14-20 if unknown
        if det is None and not (14 <= ment["determination"] <= 20):
            ok = False
        if ok:
            return lo + off, dab, rec, ment
        candidates.append((lo + off, dab, rec, ment))
    # fallback: best det match for known lea, else first
    if det is not None:
        for c in candidates:
            if c[3]["determination"] == det:
                return c
    if candidates:
        return candidates[0]
    return None


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-ha5i-", suffix=".bin")
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


def score_offset_for_attr(
    values_by_player: dict[str, int],
    players: list[dict],
    attr: str,
) -> int | None:
    """Return number of players in-band, or None if any hard lock fails."""
    ok = 0
    for p in players:
        name = p["name"]
        v = values_by_player[name]
        locks = p.get("locks") or {}
        if attr in locks and v != locks[attr]:
            return None
        if in_band(v, p["bands"][attr]):
            ok += 1
        else:
            return None
    return ok


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cal = json.loads(CAL.read_text(encoding="utf-8"))
    players = cal["players"]
    lines: list[str] = []

    t0 = time.perf_counter()
    print("decompress…", flush=True)
    tmp = decompress(SAVE)
    print(f"bytes={tmp.stat().st_size}", flush=True)

    loci: dict[str, dict] = {}
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in players:
                found = find_ca(mm, p["uid"], p.get("determination"), p.get("leadership"))
                if not found:
                    lines.append(f"{p['name']}: CA MISS uid={p['uid']}")
                    continue
                card, dbl, rec, ment = found
                loci[p["name"]] = {
                    "card": card,
                    "dbl": dbl,
                    "ment": ment,
                    "after": bytes(mm[dbl : dbl + WIN]),
                    "before_card": bytes(mm[max(0, card - 128) : card]),
                    "after_card": bytes(mm[card + 69 : card + 69 + WIN]),
                    "gap": bytes(mm[min(card + 69, dbl) : max(card + 69, dbl)])
                    if abs(dbl - (card + 69)) < 20000
                    else b"",
                }
                lines.append(
                    f"{p['name']}: card={card} dbl={dbl} gap={dbl-(card+69)} "
                    f"Det={ment['determination']} Lea={ment['leadership']}"
                )

            if len(loci) < 5:
                lines.append(f"Only {len(loci)}/5 loci — abort ranking")
                OUT.write_text("\n".join(lines), encoding="utf-8")
                print("\n".join(lines))
                return 1

            # --- single-attr offset ranking on after-double ---
            lines.append("\n=== after-double single-attr offset hits (all 5 in-band) ===")
            for enc_name, enc in (("raw", lambda b: int(b)), ("d5", d5)):
                lines.append(f"\n-- encoding={enc_name} --")
                for attr in HA_KEYS:
                    hits = []
                    for off in range(WIN):
                        vals = {name: enc(loci[name]["after"][off]) for name in loci}
                        # skip if values look like UIDs garbage (all > 20 for raw)
                        if enc_name == "raw" and any(v > 20 or v < 1 for v in vals.values()):
                            # allow for d5 path only mainly; for raw require 1..20
                            continue
                        if enc_name == "d5" and any(v < 1 or v > 20 for v in vals.values()):
                            continue
                        sc = score_offset_for_attr(vals, players, attr)
                        if sc == 5:
                            hits.append((off, vals))
                    lines.append(f"{attr}: {len(hits)} offsets")
                    for off, vals in hits[:12]:
                        pretty = ", ".join(f"{n.split()[0]}={vals[n]}" for n in sorted(vals))
                        lines.append(f"  +{off}: {pretty}")

            # Prefer offsets that jointly explain Pro + Tem + Pre + Con (distinctive)
            lines.append("\n=== joint layout search (Pro/Tem/Pre/Con) after-double ===")
            distinctive = [
                ("professionalism", "Pro"),
                ("temperament", "Tem"),
                ("pressure", "Pre"),
                ("controversy", "Con"),
                ("sportsmanship", "Spo"),
            ]
            for enc_name, enc in (("raw", lambda b: int(b)), ("d5", d5)):
                lines.append(f"\n-- encoding={enc_name} --")
                # precompute candidate offsets per attr
                cand: dict[str, list[int]] = {}
                for attr, _label in distinctive:
                    cand[attr] = []
                    for off in range(WIN):
                        vals = {name: enc(loci[name]["after"][off]) for name in loci}
                        if enc_name == "raw" and any(v > 20 or v < 1 for v in vals.values()):
                            continue
                        if enc_name == "d5" and any(v < 1 or v > 20 for v in vals.values()):
                            continue
                        if score_offset_for_attr(vals, players, attr) == 5:
                            cand[attr].append(off)
                    lines.append(f"  {attr} candidates={len(cand[attr])} -> {cand[attr][:20]}")

                # find combinations where all 4-5 offsets are distinct
                pro_offs = cand["professionalism"]
                tem_offs = cand["temperament"]
                pre_offs = cand["pressure"]
                con_offs = cand["controversy"]
                spo_offs = cand["sportsmanship"]
                combos = 0
                for po in pro_offs:
                    for to in tem_offs:
                        if to == po:
                            continue
                        for pr in pre_offs:
                            if pr in (po, to):
                                continue
                            for co in con_offs:
                                if co in (po, to, pr):
                                    continue
                                # optional spo
                                spo_ok = [s for s in spo_offs if s not in (po, to, pr, co)]
                                if not spo_ok and spo_offs:
                                    continue
                                combos += 1
                                if combos <= 30:
                                    lines.append(
                                        f"  COMBO Pro+{po} Tem+{to} Pre+{pr} Con+{co} Spo+{spo_ok[:3]}"
                                    )
                                    # dump values
                                    for attr, off in (
                                        ("professionalism", po),
                                        ("temperament", to),
                                        ("pressure", pr),
                                        ("controversy", co),
                                    ):
                                        vals = {
                                            name: enc(loci[name]["after"][off]) for name in loci
                                        }
                                        pretty = ", ".join(
                                            f"{n.split()[0]}={vals[n]}" for n in sorted(vals)
                                        )
                                        lines.append(f"    {attr}+{off}: {pretty}")
                lines.append(f"  total distinct combos (capped list): {combos}")

            # Also try 01-interleaved slots after the +39 marker (fixed for Paco/Kizza)
            lines.append("\n=== 01-interleaved slots after double (marker hunt) ===")
            for name, loc in loci.items():
                blob = loc["after"]
                marker = blob.find(b"\x00\x00\x00\x01\x01\x01")
                lines.append(f"{name}: marker={marker}")
                if marker < 0:
                    continue
                # slots at marker+3, +5, +7 ... (val then 0x01)
                slots = []
                for i in range(8):
                    off = marker + 3 + 2 * i
                    if off < len(blob):
                        slots.append((off, blob[off], blob[off + 1] if off + 1 < len(blob) else None))
                lines.append(f"  slots={slots}")

            # Cross: for each slot index 0..7, collect raw values across players with same marker-relative
            lines.append("\n=== marker-relative slot matrix (raw) ===")
            # only players with marker at same absolute-relative offset
            markers = {n: loci[n]["after"].find(b"\x00\x00\x00\x01\x01\x01") for n in loci}
            lines.append(f"markers={markers}")
            for slot in range(8):
                row = {}
                for name, loc in loci.items():
                    m = markers[name]
                    if m < 0:
                        continue
                    off = m + 3 + 2 * slot
                    row[name] = loc["after"][off]
                if len(row) < 5:
                    lines.append(f"slot{slot}: incomplete {row}")
                    continue
                # which attrs could this slot be?
                fits = []
                for attr in HA_KEYS:
                    if score_offset_for_attr(row, players, attr) == 5:
                        fits.append(attr)
                pretty = ", ".join(f"{n.split()[0]}={row[n]}" for n in sorted(row))
                lines.append(f"slot{slot}: {pretty}  fits={fits or '-'}")

            # Contiguous 8-byte HA packs after marker (raw)
            lines.append("\n=== contiguous 8-byte packs near marker / after 01-run ===")
            for base_rel in range(0, 120):
                # collect 8 bytes at base_rel for all players
                pass
            # smarter: after each player's 01-run ends, take next 8 bytes
            for name, loc in loci.items():
                blob = loc["after"]
                m = markers[name]
                if m < 0:
                    continue
                p = m
                while p < len(blob) and blob[p] in (0, 1):
                    p += 1
                # skip V01 or fillers
                q = p
                while q + 1 < len(blob):
                    if 1 <= blob[q] <= 20 and blob[q + 1] == 1:
                        q += 2
                        continue
                    if blob[q] == 1:
                        q += 1
                        continue
                    break
                pack = list(blob[q : q + 16])
                lines.append(f"{name}: pack@+{q} raw={pack} d5={[d5(x) for x in pack]}")

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
        if any(
            x in line
            for x in (
                "card=",
                "MISS",
                "candidates=",
                "COMBO",
                "slot",
                "marker",
                "professionalism:",
                "temperament:",
                "pressure:",
                "controversy:",
                "sportsmanship:",
                "total distinct",
                "pack@",
            )
        ):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
