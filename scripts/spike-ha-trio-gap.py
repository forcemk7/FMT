#!/usr/bin/env python3
"""
Trio HA hunt v2 — key by UID to avoid encoding issues.
Focus: gap between CA card and double (excluding 69B attr cards),
and signature matching of the sparse V|01 personality tail.
"""

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
OUT = ROOT / "tmp" / "fm-spike" / "ha-trio-gap.txt"
ZSTD_OFF = 26
ATTR_LOOKBACK = 24_000
PERSON_HEAD = 512 * 1024 * 1024

MENTAL = [
    "aggression", "anticipation", "bravery", "vision", "decisions",
    "determination", "flair", "leadership", "offTheBall", "positioning",
    "teamwork", "workRate", "composure", "concentration",
]

# stable keys
KEYS = {
    "kizza": "Sam Kizza",
    "paco": "Paco Suárez",
    "tassinari": "Marco Tassinari",
    "seimen": "Dennis Seimen",
    "yoan": "Yoan Robert",
}
TRIO = ["kizza", "paco", "tassinari"]
ALL = list(KEYS)


def d5(b: int) -> int:
    return int(round(b / 5))


def is_attrish(buf: bytes, i: int) -> bool:
    if i + 69 > len(buf):
        return False
    if buf[i + 34] or buf[i + 35] or buf[i + 43] != 0x01:
        return False
    return sum(1 for x in buf[i : i + 22] if 25 <= x <= 105) >= 12


def mark_attr_cards(gap: bytes) -> bytearray:
    """Zero out 69B attrish cards so HA search ignores CA strip internals."""
    mask = bytearray(gap)
    start = 0
    while True:
        z = gap.find(b"\x00\x00", start)
        if z < 0 or z + 35 > len(gap):
            break
        i = z - 34
        if i >= 0 and z == i + 34 and is_attrish(gap, i):
            for j in range(i, min(len(mask), i + 69)):
                mask[j] = 0
            start = z + 69
        else:
            start = z + 1
    return mask


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
            fallback.append((lo + off, dab, ment))
            continue
        if lea is not None and ment["leadership"] != lea:
            fallback.append((lo + off, dab, ment))
            continue
        if det is None and not (14 <= ment["determination"] <= 20):
            fallback.append((lo + off, dab, ment))
            continue
        return lo + off, dab, ment
    return fallback[0] if fallback else None


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-gap-", suffix=".bin")
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


def ok_attr(vals, meta, keys, attr):
    for k in keys:
        v = vals[k]
        p = meta[k]
        if not (1 <= v <= 20):
            return False
        if not in_band(v, p["bands"][attr]):
            return False
        locks = p.get("locks") or {}
        if attr in locks and v != locks[attr]:
            return False
    return True


def parse_sparse(after: bytes):
    for base in range(32, 56):
        if after[base : base + 3] != b"\x01\x01\x01":
            continue
        j = base + 3
        vals = []
        while j + 1 < len(after) and len(vals) < 12:
            v, n = after[j], after[j + 1]
            if 2 <= v <= 20 and n == 1:
                vals.append((j, v))
                j += 2
            elif v == 1:
                j += 1
            else:
                break
        return base, vals, j
    return None, [], None


def main() -> int:
    cal = json.loads(CAL.read_text(encoding="utf-8"))
    # map by our keys via name match on first word / uid from cal
    meta = {}
    for p in cal["players"]:
        for k, name in KEYS.items():
            if p["name"] == name or p["name"].startswith(name.split()[0]):
                meta[k] = p
                break
    # force by uid from cal fixture order
    for p in cal["players"]:
        for k, name in KEYS.items():
            if p["uid"] == {
                "kizza": 2002185604,
                "paco": 2000136577,
                "tassinari": 2002083070,
                "seimen": 2000175080,
                "yoan": 2002089146,
            }[k]:
                meta[k] = p

    lines = []
    tmp = decompress(SAVE)
    loci = {}
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for k, p in meta.items():
                found = find_ca(mm, p["uid"], p.get("determination"), p.get("leadership"))
                if not found:
                    lines.append(f"MISS {k}")
                    continue
                card, dbl, ment = found
                after = bytes(mm[dbl : dbl + 512])
                gap_lo, gap_hi = card + 69, dbl
                if gap_hi < gap_lo:
                    gap_lo, gap_hi = gap_hi, gap_lo
                gap = bytes(mm[gap_lo:gap_hi])
                masked = mark_attr_cards(gap)
                base, sparse, pack_at = parse_sparse(after)
                loci[k] = {
                    "card": card,
                    "dbl": dbl,
                    "gap_lo": gap_lo,
                    "gap": gap,
                    "masked": bytes(masked),
                    "after": after,
                    "sparse": sparse,
                    "pack_at": pack_at,
                    "ment": ment,
                }
                lines.append(
                    f"{k}: card={card} dbl={dbl} gap_len={len(gap)} "
                    f"Det={ment['determination']} Lea={ment['leadership']} "
                    f"sparse={[v for _,v in sparse]} pack_at={pack_at}"
                )

            # --- Gap search: card-relative and double-relative using MASKED gap ---
            lines.append("\n=== MASKED gap: shared dbl-relative offsets (trio) ===")
            # Represent each byte in gap by its offset from dbl (negative)
            # Build map: for each player, dict[rel_to_dbl] = value (masked; 0 means cleared)
            rel_maps = {}
            for k, loc in loci.items():
                m = {}
                # gap covers [gap_lo, dbl) typically
                for i, b in enumerate(loc["masked"]):
                    abs_pos = loc["gap_lo"] + i
                    rel = abs_pos - loc["dbl"]  # negative
                    m[rel] = b
                rel_maps[k] = m

            shared_rels = set(rel_maps["kizza"]) & set(rel_maps["paco"]) & set(rel_maps["tassinari"])
            lines.append(f"shared dbl-relative positions in gaps: {len(shared_rels)}")

            for enc_name, enc in (("raw", lambda b: b), ("d5", d5)):
                for attr in (
                    "professionalism",
                    "temperament",
                    "controversy",
                    "pressure",
                    "sportsmanship",
                ):
                    hits = []
                    for rel in sorted(shared_rels, key=abs):
                        vals = {}
                        ok = True
                        for k in TRIO:
                            b = rel_maps[k][rel]
                            if b == 0:  # masked out CA card
                                ok = False
                                break
                            v = enc(b)
                            vals[k] = v
                        if not ok:
                            continue
                        if ok_attr(vals, meta, TRIO, attr):
                            hits.append((rel, vals))
                    lines.append(f"{enc_name} {attr}: {len(hits)}")
                    for rel, vals in hits[:15]:
                        lines.append(f"  rel={rel}: {vals}")

            # --- Card-relative: offset from card start ---
            lines.append("\n=== MASKED gap: shared card-relative offsets (trio) ===")
            card_maps = {}
            for k, loc in loci.items():
                m = {}
                for i, b in enumerate(loc["masked"]):
                    abs_pos = loc["gap_lo"] + i
                    rel = abs_pos - loc["card"]
                    m[rel] = b
                card_maps[k] = m
            shared_c = set(card_maps["kizza"]) & set(card_maps["paco"]) & set(card_maps["tassinari"])
            lines.append(f"shared card-relative positions: {len(shared_c)}")
            for enc_name, enc in (("raw", lambda b: b), ("d5", d5)):
                for attr in ("professionalism", "temperament", "controversy", "pressure"):
                    hits = []
                    for rel in sorted(shared_c, key=abs)[:200000]:
                        vals = {}
                        ok = True
                        for k in TRIO:
                            b = card_maps[k].get(rel, 0)
                            if b == 0:
                                ok = False
                                break
                            vals[k] = enc(b)
                        if not ok:
                            continue
                        if ok_attr(vals, meta, TRIO, attr):
                            hits.append((rel, vals))
                    lines.append(f"{enc_name} {attr}: {len(hits)}")
                    for rel, vals in hits[:12]:
                        # validate all5 if possible
                        all_vals = {}
                        all_ok = True
                        for k in ALL:
                            b = card_maps[k].get(rel, 0)
                            if b == 0:
                                all_ok = False
                                break
                            all_vals[k] = (enc(b) if enc_name == "d5" else b) if True else b
                            all_vals[k] = enc(b)
                        if all_ok:
                            all_ok = ok_attr(all_vals, meta, ALL, attr)
                        lines.append(f"  rel={rel}: {vals} all5={all_ok}")

            # --- Signature: find 01 01 01 blocks near Tassinari with Tem in sparse ---
            lines.append("\n=== Tassinari neighborhood: any V|01 sparse with Tem 3-6 ===")
            t_dbl = loci["tassinari"]["dbl"]
            neighborhood = bytes(mm[t_dbl - 8192 : t_dbl + 8192])
            found_sig = 0
            for i in range(len(neighborhood) - 8):
                if neighborhood[i : i + 3] != b"\x01\x01\x01":
                    continue
                j = i + 3
                vals = []
                while j + 1 < len(neighborhood) and len(vals) < 10:
                    v, n = neighborhood[j], neighborhood[j + 1]
                    if 2 <= v <= 20 and n == 1:
                        vals.append(v)
                        j += 2
                    elif v == 1:
                        j += 1
                    else:
                        break
                if any(3 <= v <= 6 for v in vals):
                    found_sig += 1
                    if found_sig <= 20:
                        abs_off = t_dbl - 8192 + i
                        lines.append(
                            f"  abs={abs_off} dbl_rel={abs_off - t_dbl} vals={vals}"
                        )
            lines.append(f"total Tem-ish sparse blocks near Tassinari: {found_sig}")

            # Same for Con 15-20 in sparse
            lines.append("\n=== Tassinari neighborhood: V|01 sparse with Con 15-20 ===")
            found_sig = 0
            for i in range(len(neighborhood) - 8):
                if neighborhood[i : i + 3] != b"\x01\x01\x01":
                    continue
                j = i + 3
                vals = []
                while j + 1 < len(neighborhood) and len(vals) < 10:
                    v, n = neighborhood[j], neighborhood[j + 1]
                    if 2 <= v <= 20 and n == 1:
                        vals.append(v)
                        j += 2
                    elif v == 1:
                        j += 1
                    else:
                        break
                if any(15 <= v <= 20 for v in vals) and any(3 <= v <= 6 for v in vals):
                    found_sig += 1
                    if found_sig <= 20:
                        abs_off = t_dbl - 8192 + i
                        lines.append(
                            f"  abs={abs_off} dbl_rel={abs_off - t_dbl} vals={vals}"
                        )
            lines.append(f"total Tem+Con-ish sparse blocks: {found_sig}")

            # Kizza/Paco ground truth: does sparse Pro/Tem hypothesis survive?
            lines.append("\n=== family A working hypothesis ===")
            lines.append(
                f"kizza sparse={[v for _,v in loci['kizza']['sparse']]} "
                f"=> hyp Pro={loci['kizza']['sparse'][0][1] if loci['kizza']['sparse'] else None} "
                f"Tem={loci['kizza']['sparse'][1][1] if len(loci['kizza']['sparse'])>1 else None}"
            )
            lines.append(
                f"paco sparse={[v for _,v in loci['paco']['sparse']]} "
                f"=> hyp Pro={loci['paco']['sparse'][0][1] if loci['paco']['sparse'] else None}"
            )
            lines.append(
                "tassinari/seimen/yoan sparse empty at same header — HAs not in that list for them"
            )

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
        print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
