#!/usr/bin/env python3
"""
Align the post-double 01-interleaved person block using:
  Paco  Pro==20 (raw 0x14)
  Kizza Tem==15 (raw 0x0f)

Hypothesis: after double-UID there is a `00… 01 01 01 <vals 01-separated> …` person sheet.
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
OUT = ROOT / "tmp" / "fm-spike" / "ha-interleaved-01.txt"
ZSTD_OFF = 26
ATTR_LOOKBACK = 24_000
PERSON_HEAD = 512 * 1024 * 1024

ANCHORS = {
    "Paco": {"uid": 2000136577, "det": 19, "lea": 14},
    "Kizza": {"uid": 2002185604, "det": 16, "lea": 15},
    "Contreras": {"uid": 2002220356, "det": 15, "lea": 10},
}

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


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-ha6-", suffix=".bin")
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


def find_01_block(blob: bytes) -> int | None:
    """Find first run of ≥3 0x01 after a short zero pad, within first 160B."""
    for i in range(0, min(len(blob) - 8, 160)):
        if blob[i] != 1:
            continue
        # prefer blocks preceded by zeros
        pre = blob[max(0, i - 6) : i]
        if pre.count(0) < 3:
            continue
        run = 0
        while i + run < len(blob) and blob[i + run] == 1:
            run += 1
        if run >= 3:
            return i
    return None


def parse_interleaved(blob: bytes, start: int, max_vals: int = 16) -> tuple[list[int], list[tuple[int, int]]]:
    """
    From start of 01-run, walk:
      - skip leading 01 fillers
      - collect V where pattern is V 01 and 1<=V<=20
      - stop when pattern breaks for more than one byte, or hit non-attr blob
    """
    i = start
    while i < len(blob) and blob[i] == 1:
        i += 1
    vals = []
    positions = []
    while i + 1 < len(blob) and len(vals) < max_vals:
        v = blob[i]
        nxt = blob[i + 1]
        if 1 <= v <= 20 and nxt == 1:
            vals.append(v)
            positions.append((i, v))
            i += 2
            continue
        # allow lone trailing 01 fillers between value pairs
        if v == 1:
            i += 1
            continue
        break
    return vals, positions


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
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
                card, dbl, _rec, ment = found
                loci[name] = {"card": card, "dbl": dbl, "ment": ment}
                lines.append(f"{name}: card={card} dbl={dbl}")

            alignments = {}
            for name, loc in loci.items():
                blob = bytes(mm[loc["dbl"] : loc["dbl"] + 256])
                blk = find_01_block(blob)
                lines.append(f"\n=== {name} after-double ===")
                lines.append(f"01-block start=+{blk}")
                if blk is None:
                    continue
                vals, positions = parse_interleaved(blob, blk)
                alignments[name] = {"blk": blk, "vals": vals, "positions": positions, "blob": blob}
                lines.append(f"interleaved vals={vals}")
                lines.append(f"positions={positions}")
                # also dump the 48 bytes around the block
                lo = max(0, blk - 8)
                hi = min(len(blob), blk + 48)
                chunk = blob[lo:hi]
                hx = " ".join(f"{b:02x}" for b in chunk)
                lines.append(f"hex[{lo}:{hi}]: {hx}")

            # Lock checks
            lines.append("\n=== lock checks ===")
            if "Paco" in alignments:
                pv = alignments["Paco"]["vals"]
                lines.append(f"Paco vals contain 20 (Pro)? {20 in pv}  vals={pv}")
            if "Kizza" in alignments:
                kv = alignments["Kizza"]["vals"]
                lines.append(f"Kizza vals contain 15 (Tem)? {15 in kv}  vals={kv}")

            # Position-wise compare between Paco and Kizza by index in interleaved list
            if "Paco" in alignments and "Kizza" in alignments:
                lines.append("\n=== index alignment Paco vs Kizza ===")
                pv = alignments["Paco"]["vals"]
                kv = alignments["Kizza"]["vals"]
                n = max(len(pv), len(kv))
                for i in range(n):
                    a = pv[i] if i < len(pv) else None
                    b = kv[i] if i < len(kv) else None
                    note = ""
                    if a == 20 and b is not None:
                        note = "  ← Paco Pro slot?"
                    if b == 15 and a is not None:
                        note += "  ← Kizza Tem slot?"
                    lines.append(f"  idx={i}: Paco={a} Kizza={b}{note}")

            # Byte-relative to dbl: positions where Paco has raw 20 and Kizza has raw 15
            lines.append("\n=== absolute offsets of raw locks (whole 256B) ===")
            for name, needle, label in (("Paco", 20, "Pro20"), ("Kizza", 15, "Tem15")):
                if name not in alignments:
                    continue
                blob = alignments[name]["blob"]
                hits = [i for i, b in enumerate(blob) if b == needle]
                # filter to those followed by 0x01 (interleaved-ish)
                hit01 = [i for i in hits if i + 1 < len(blob) and blob[i + 1] == 1]
                lines.append(f"{name} {label} raw hits={hits[:20]}")
                lines.append(f"{name} {label} as XX 01 hits={hit01}")

            # Shared relative offsets where both have their hard lock as XX 01
            if "Paco" in alignments and "Kizza" in alignments:
                p_offs = {
                    i for i, b in enumerate(alignments["Paco"]["blob"])
                    if b == 20 and i + 1 < 256 and alignments["Paco"]["blob"][i + 1] == 1
                }
                k_offs = {
                    i for i, b in enumerate(alignments["Kizza"]["blob"])
                    if b == 15 and i + 1 < 256 and alignments["Kizza"]["blob"][i + 1] == 1
                }
                shared = p_offs & k_offs
                lines.append(f"\nshared rel-off where Paco XX=20|01 AND Kizza XX=15|01: {sorted(shared)}")
                # not expected same value, but same offset for DIFFERENT locks is the gold:
                # offset where Pac=20|01 and that same offset on Kizza =15|01
                same_slot = sorted(p_offs & k_offs)  # wrong - that's value coinciding
                # correct: offsets present in both players' 01-blocks as value slots
                p_slots = {pos for pos, _v in alignments["Paco"]["positions"]}
                k_slots = {pos for pos, _v in alignments["Kizza"]["positions"]}
                # normalize to block-relative
                pb = alignments["Paco"]["blk"]
                kb = alignments["Kizza"]["blk"]
                p_rel = {pos - pb for pos, _v in alignments["Paco"]["positions"]}
                k_rel = {pos - kb for pos, _v in alignments["Kizza"]["positions"]}
                lines.append(f"Paco slot rel-to-01block={sorted(p_rel)}")
                lines.append(f"Kizza slot rel-to-01block={sorted(k_rel)}")
                lines.append(f"shared slot rel-to-01block={sorted(p_rel & k_rel)}")

                # For each shared relative slot, print both values
                for rel in sorted(p_rel & k_rel):
                    pv = alignments["Paco"]["blob"][pb + rel]
                    kv = alignments["Kizza"]["blob"][kb + rel]
                    lines.append(f"  rel=+{rel}: Paco={pv} Kizza={kv}")

            # Dump Contreras similarly for Model Citizen feasibility
            if "Contreras" in alignments:
                lines.append("\n=== Contreras interleaved (Model Citizen bands) ===")
                cv = alignments["Contreras"]["vals"]
                lines.append(f"vals={cv}")
                mc = {
                    "pro": (15, 20),
                    "pre": (15, 20),
                    "amb": (12, 20),
                    "tem": (15, 20),
                    "loy": (15, 20),
                    "spo": (15, 20),
                    "con": (1, 14),
                }
                lines.append(f"any val in MC-ish ranges: {[v for v in cv if 12 <= v <= 20]}")

            # Scan ALL first-team? Too heavy. Instead try: read every XX 01 in Paco/Kizza
            # within ±0 of 01-block as potential HA tuple with various widths.
            lines.append("\n=== try 8-wide value lists from interleaved stream ===")
            HA_NAMES = [
                "professionalism", "pressure", "ambition", "importantMatches",
                "sportsmanship", "temperament", "loyalty", "controversy",
            ]
            ORDERS = {
                "user": HA_NAMES,
                "pro_tem": ["professionalism", "temperament", "pressure", "ambition", "loyalty", "sportsmanship", "controversy", "importantMatches"],
                "gs1": ["professionalism", "ambition", "loyalty", "pressure", "temperament", "sportsmanship", "controversy", "importantMatches"],
            }

            def bands_ok(name: str, mapping: dict) -> bool:
                if name == "Paco":
                    if mapping.get("professionalism") != 20:
                        return False
                    if not (10 <= mapping.get("temperament", -1) <= 20):
                        return False
                    if not (1 <= mapping.get("loyalty", -1) <= 10):
                        return False
                    if not (6 <= mapping.get("controversy", -1) <= 14):
                        return False
                    if not (1 <= mapping.get("pressure", -1) <= 14):
                        return False
                    return True
                if name == "Kizza":
                    if mapping.get("temperament") != 15:
                        return False
                    for k, (lo, hi) in {
                        "professionalism": (15, 20),
                        "pressure": (15, 20),
                        "ambition": (12, 20),
                        "loyalty": (15, 20),
                        "sportsmanship": (15, 20),
                        "controversy": (1, 14),
                    }.items():
                        v = mapping.get(k, -1)
                        if not (lo <= v <= hi):
                            return False
                    return True
                if name == "Contreras":
                    for k, (lo, hi) in {
                        "professionalism": (15, 20),
                        "pressure": (15, 20),
                        "ambition": (12, 20),
                        "temperament": (15, 20),
                        "loyalty": (15, 20),
                        "sportsmanship": (15, 20),
                        "controversy": (1, 14),
                    }.items():
                        v = mapping.get(k, -1)
                        if not (lo <= v <= hi):
                            return False
                    return True
                return False

            for ord_name, keys in ORDERS.items():
                lines.append(f"order={ord_name}")
                for name, al in alignments.items():
                    vals = al["vals"]
                    # try padding short lists with None — skip if < needed
                    # Also try windows into vals if longer
                    matched = []
                    if len(vals) >= 8:
                        for start in range(0, len(vals) - 7):
                            window = vals[start : start + 8]
                            mapping = dict(zip(keys, window))
                            if bands_ok(name, mapping):
                                matched.append((start, mapping))
                    elif len(vals) > 0:
                        # pad with scanning nearby raw 1-20 bytes after last val?
                        pass
                    lines.append(f"  {name}: matches={len(matched)}")
                    for start, mapping in matched[:5]:
                        lines.append(f"    start={start} {mapping}")

                # Cross: require at least Paco and Kizza matches with same start index
                if "Paco" in alignments and "Kizza" in alignments:
                    p_ok = []
                    k_ok = []
                    pv, kv = alignments["Paco"]["vals"], alignments["Kizza"]["vals"]
                    if len(pv) >= 8 and len(kv) >= 8:
                        for start in range(0, min(len(pv), len(kv)) - 7):
                            pm = dict(zip(keys, pv[start : start + 8]))
                            km = dict(zip(keys, kv[start : start + 8]))
                            if bands_ok("Paco", pm) and bands_ok("Kizza", km):
                                lines.append(f"  CROSS start={start}")
                                lines.append(f"    Paco:  {pm}")
                                lines.append(f"    Kizza: {km}")
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
                "card=", "01-block", "interleaved", "contain", "idx=",
                "shared", "CROSS", "matches=", "vals=",
            )
        ):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
