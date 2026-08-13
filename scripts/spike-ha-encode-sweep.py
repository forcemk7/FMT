#!/usr/bin/env python3
"""
HA encoding sweep for the calibration 5:
  - float32 LE of distinctive display values near double-UID
  - int16 LE of raw / *5 values
  - search all UID hit neighborhoods (not just primary double)
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
OUT = ROOT / "tmp" / "fm-spike" / "ha-encode-sweep.txt"
ZSTD_OFF = 26
ATTR_LOOKBACK = 24_000
PERSON_HEAD = 512 * 1024 * 1024
NEAR = 2048

UIDS = {
    "kizza": 2002185604,
    "paco": 2000136577,
    "tassinari": 2002083070,
    "seimen": 2000175080,
    "yoan": 2002089146,
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
            fallback.append((lo + off, dab, ment, hits))
            continue
        if lea is not None and ment["leadership"] != lea:
            fallback.append((lo + off, dab, ment, hits))
            continue
        if det is None and not (14 <= ment["determination"] <= 20):
            fallback.append((lo + off, dab, ment, hits))
            continue
        return lo + off, dab, ment, hits
    return (*fallback[0],) if fallback else None


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-enc-", suffix=".bin")
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
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    meta = {k: cal[uid] for k, uid in UIDS.items()}
    lines = []
    tmp = decompress(SAVE)

    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            loci = {}
            for k, uid in UIDS.items():
                p = meta[k]
                found = find_ca(mm, uid, p.get("determination"), p.get("leadership"))
                if not found:
                    lines.append(f"MISS {k}")
                    continue
                card, dbl, ment, doubles = found
                loci[k] = {"card": card, "dbl": dbl, "ment": ment, "doubles": doubles, "uid": uid}
                lines.append(f"{k}: card={card} dbl={dbl} doubles={len(doubles)}")

            # Float32 search near primary double for lock values
            lines.append("\n=== float32 LE near primary double (±2KB) ===")
            targets = {
                "kizza": [("tem", 15.0), ("tem5", 75.0)],
                "paco": [("pro", 20.0), ("pro5", 100.0)],
                "tassinari": [("tem_lo", 3.0), ("tem_hi", 6.0), ("con_lo", 15.0)],
            }
            for k, tlist in targets.items():
                dbl = loci[k]["dbl"]
                blob = bytes(mm[max(0, dbl - NEAR) : dbl + NEAR])
                base = max(0, dbl - NEAR)
                for label, want in tlist:
                    hits = []
                    for i in range(0, len(blob) - 3):
                        val = struct.unpack_from("<f", blob, i)[0]
                        if abs(val - want) < 1e-4:
                            hits.append(base + i - dbl)
                    lines.append(f"{k} {label}={want}: n={len(hits)} rel={hits[:20]}")

            # int16 LE: Tem=15 / Pro=20 / Tem in 3-6 as values at same relative offset
            lines.append("\n=== int16 LE shared dbl-relative (trio) ===")
            windows = {
                k: bytes(mm[loci[k]["dbl"] : loci[k]["dbl"] + NEAR]) for k in ("kizza", "paco", "tassinari")
            }
            for attr, checker in (
                (
                    "temperament",
                    lambda vals: (
                        vals["kizza"] == 15
                        and in_band(vals["paco"], meta["paco"]["bands"]["temperament"])
                        and in_band(vals["tassinari"], meta["tassinari"]["bands"]["temperament"])
                    ),
                ),
                (
                    "professionalism",
                    lambda vals: (
                        vals["paco"] == 20
                        and in_band(vals["kizza"], meta["kizza"]["bands"]["professionalism"])
                        and in_band(vals["tassinari"], meta["tassinari"]["bands"]["professionalism"])
                    ),
                ),
                (
                    "controversy",
                    lambda vals: all(
                        in_band(vals[k], meta[k]["bands"]["controversy"])
                        for k in ("kizza", "paco", "tassinari")
                    ),
                ),
            ):
                hits = []
                for off in range(0, NEAR - 1):
                    vals = {
                        k: struct.unpack_from("<H", windows[k], off)[0]
                        for k in ("kizza", "paco", "tassinari")
                    }
                    # prefer display-scale 1..20
                    if any(v > 100 for v in vals.values()):
                        continue
                    if checker(vals):
                        hits.append((off, vals))
                lines.append(f"u16 {attr} display-ish: {len(hits)}")
                for off, vals in hits[:15]:
                    lines.append(f"  +{off}: {vals}")

            # Also u16 of *5 scale (Pro=100, Tem=75, Tem 15-30 for tassinari)
            lines.append("\n=== int16 LE *5-scale shared ===")
            hits = []
            for off in range(0, NEAR - 1):
                vals = {
                    k: struct.unpack_from("<H", windows[k], off)[0]
                    for k in ("kizza", "paco", "tassinari")
                }
                # interpret as *5 raw internal
                disp = {k: int(round(v / 5)) for k, v in vals.items()}
                if not (1 <= disp["kizza"] <= 20 and 1 <= disp["paco"] <= 20 and 1 <= disp["tassinari"] <= 20):
                    continue
                if disp["kizza"] != 15:
                    continue
                if not in_band(disp["paco"], meta["paco"]["bands"]["temperament"]):
                    continue
                if not in_band(disp["tassinari"], meta["tassinari"]["bands"]["temperament"]):
                    continue
                hits.append((off, vals, disp))
            lines.append(f"u16 Tem as /5: {len(hits)}")
            for off, vals, disp in hits[:15]:
                lines.append(f"  +{off}: raw={vals} disp={disp}")

            # Scan ALL double-UID hits (not just primary) for Paco Pro sparse signature
            # and whether any secondary locus has Tassinari Tem sparse
            lines.append("\n=== alternate double-UID loci: sparse survey ===")
            for k in ("kizza", "paco", "tassinari", "seimen", "yoan"):
                lines.append(f"-- {k} --")
                for dab in loci[k]["doubles"][:8]:
                    after = bytes(mm[dab : dab + 96])
                    sparse = []
                    for base in range(32, 56):
                        if after[base : base + 3] != b"\x01\x01\x01":
                            continue
                        j = base + 3
                        while j + 1 < len(after) and len(sparse) < 8:
                            v, n = after[j], after[j + 1]
                            if 2 <= v <= 20 and n == 1:
                                sparse.append(v)
                                j += 2
                            elif v == 1:
                                j += 1
                            else:
                                break
                        break
                    lines.append(f"  dbl={dab} sparse={sparse} head={after[36:56].hex(' ')}")

            # Global rarity: count how often byte==Tem-ish 3..6 appears next to 01 after 01 01 01 in person head? too heavy.
            # Instead: for Tassinari Tem, search for pattern `01 01 01 XX 01` with XX in 3-6 within ±64KB of UID
            lines.append("\n=== Tassinari ±64KB: 01 01 01 (3-6) 01 occurrences ===")
            t_uid = UIDS["tassinari"]
            # find single UID hits too
            pat = struct.pack("<I", t_uid)
            uid_hits = []
            j = mm.find(pat, 0, PERSON_HEAD)
            while j >= 0 and len(uid_hits) < 40:
                uid_hits.append(j)
                j = mm.find(pat, j + 1, PERSON_HEAD)
            lines.append(f"uid hit count (capped 40)={len(uid_hits)}")
            found = 0
            for uh in uid_hits:
                lo = max(0, uh - 65536)
                hi = min(len(mm), uh + 65536)
                blob = bytes(mm[lo:hi])
                for i in range(len(blob) - 5):
                    if blob[i : i + 3] == b"\x01\x01\x01":
                        v = blob[i + 3]
                        if 3 <= v <= 6 and blob[i + 4] == 1:
                            found += 1
                            if found <= 25:
                                lines.append(
                                    f"  near_uid={uh} abs={lo+i} uid_rel={lo+i-uh} vals_start={v}"
                                )
            lines.append(f"total 01 01 01 Tem3-6 01 near any Tassinari uid: {found}")

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
