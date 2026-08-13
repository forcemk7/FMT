#!/usr/bin/env python3
"""
Classic CM/FM staff HA block hunt.

Historical staff record (CM0102 TStaff) stores raw 1-byte personality HAs
contiguously as:
  Adaptability, Ambition, Determination, Loyalty,
  Pressure, Professionalism, Sportsmanship, Temperament

Modern FM moved Determination into visible mentals, and added Controversy /
Important Matches. Try classic + modern variants as contiguous raw 1..20 packs
relative to UniqueID hits (person/staff object), NOT the *5 CA card.
"""

from __future__ import annotations

import json
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-classic-staff-order.txt"
ZSTD_OFF = 26

PLAYERS = {
    "kizza": 2002185604,
    "paco": 2000136577,
    "tassinari": 2002083070,
    "seimen": 2000175080,
    "yoan": 2002089146,
}
ALL = list(PLAYERS)
TRIO = ["kizza", "paco", "tassinari"]

# Orders keyed by attribute names we have bands for.
# Adaptability / Determination treated as wildcards (1-20) when present.
ORDERS = {
    "classic8": [
        "adaptability",
        "ambition",
        "determination",
        "loyalty",
        "pressure",
        "professionalism",
        "sportsmanship",
        "temperament",
    ],
    "classic_no_det": [
        "adaptability",
        "ambition",
        "loyalty",
        "pressure",
        "professionalism",
        "sportsmanship",
        "temperament",
        "controversy",
    ],
    "modern_pers": [
        "ambition",
        "loyalty",
        "pressure",
        "professionalism",
        "sportsmanship",
        "temperament",
        "controversy",
        "importantMatches",
    ],
    "classic_shifted_pro": [
        "loyalty",
        "pressure",
        "professionalism",
        "sportsmanship",
        "temperament",
        "ambition",
        "controversy",
        "importantMatches",
    ],
    # CM offsets starting at Loy (skip adapt/amb/det)
    "from_loy": [
        "loyalty",
        "pressure",
        "professionalism",
        "sportsmanship",
        "temperament",
    ],
}


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-classic-", suffix=".bin")
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


def collect(mm, uid, limit=40):
    pat = struct.pack("<I", uid)
    hits = []
    j = mm.find(pat, 0)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(pat, j + 1)
    return hits


def in_band(v, band):
    return band[0] <= v <= band[1]


def wild_band(name, key, meta):
    if key in meta[name]["bands"]:
        return meta[name]["bands"][key]
    # wildcards for attrs we don't calibrate
    return [1, 20]


def ok_pack(raw: bytes, keys: list[str], name: str, meta) -> bool:
    if len(raw) < len(keys):
        return False
    locks = meta[name].get("locks") or {}
    for i, key in enumerate(keys):
        v = raw[i]
        if not (1 <= v <= 20):
            return False
        if not in_band(v, wild_band(name, key, meta)):
            return False
        if key in locks and v != locks[key]:
            return False
    return True


def main() -> int:
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    meta = {k: cal[uid] for k, uid in PLAYERS.items()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    tmp = decompress(SAVE)

    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hits = {k: collect(mm, uid) for k, uid in PLAYERS.items()}
            for k in ALL:
                lines.append(f"{k}: hits={len(hits[k])}")

            # Prefer primary double-UID hits (second copy at +4)
            primary = {}
            for k, uid in PLAYERS.items():
                for h in hits[k]:
                    if h + 4 < len(mm) and struct.unpack_from("<I", mm, h + 4)[0] == uid:
                        primary[k] = h
                        break
                if k not in primary and hits[k]:
                    primary[k] = hits[k][0]
            lines.append(f"primary doubles={primary}")

            # Scan relative to primary for each order
            lines.append("\n=== primary-double relative contiguous packs ===")
            for ord_name, keys in ORDERS.items():
                n = len(keys)
                hits_found = []
                for rel in range(-256, 512):
                    ok = True
                    decoded = {}
                    for k in TRIO:
                        raw = bytes(mm[primary[k] + rel : primary[k] + rel + n])
                        if not ok_pack(raw, keys, k, meta):
                            ok = False
                            break
                        decoded[k] = list(raw)
                    if not ok:
                        continue
                    # validators
                    ok5 = True
                    decoded5 = dict(decoded)
                    for k in ("seimen", "yoan"):
                        raw = bytes(mm[primary[k] + rel : primary[k] + rel + n])
                        if not ok_pack(raw, keys, k, meta):
                            ok5 = False
                            break
                        decoded5[k] = list(raw)
                    hits_found.append((ok5, rel, decoded5 if ok5 else decoded))
                lines.append(f"{ord_name}: trio_hits={len(hits_found)}")
                for ok5, rel, decoded in hits_found[:15]:
                    lines.append(f"  all5={ok5} rel={rel}")
                    for k, vals in decoded.items():
                        mapped = dict(zip(keys, vals))
                        lines.append(f"    {k}: {mapped}")

            # Also: any-hit transfer within ±256 using classic_no_det / from_loy
            lines.append("\n=== any-hit transfer (classic_no_det) ===")
            keys = ORDERS["classic_no_det"]
            n = len(keys)
            transfer = []
            for rel in range(-128, 256):
                # need each player to have SOME hit that fits
                pos = {}
                decoded = {}
                ok = True
                for k in ALL:
                    found = None
                    for h in hits[k][:25]:
                        raw = bytes(mm[h + rel : h + rel + n])
                        if ok_pack(raw, keys, k, meta):
                            found = (h, list(raw))
                            break
                    if not found:
                        ok = False
                        break
                    pos[k], decoded[k] = found
                if ok:
                    transfer.append((rel, pos, decoded))
            lines.append(f"classic_no_det transfer rels={len(transfer)}")
            for rel, pos, decoded in transfer[:20]:
                lines.append(f"  rel={rel}")
                for k in ALL:
                    mapped = dict(zip(keys, decoded[k]))
                    lines.append(f"    {k}@{pos[k]}: {mapped}")

            lines.append("\n=== any-hit transfer (from_loy 5-byte) ===")
            keys = ORDERS["from_loy"]
            n = len(keys)
            transfer = []
            for rel in range(-128, 256):
                pos = {}
                decoded = {}
                ok = True
                for k in ALL:
                    found = None
                    for h in hits[k][:25]:
                        raw = bytes(mm[h + rel : h + rel + n])
                        if ok_pack(raw, keys, k, meta):
                            found = (h, list(raw))
                            break
                    if not found:
                        ok = False
                        break
                    pos[k], decoded[k] = found
                if ok:
                    transfer.append((rel, pos, decoded))
            lines.append(f"from_loy transfer rels={len(transfer)}")
            for rel, pos, decoded in transfer[:20]:
                lines.append(f"  rel={rel}")
                for k in ALL:
                    mapped = dict(zip(keys, decoded[k]))
                    lines.append(f"    {k}@{pos[k]}: {mapped}")

            # Subtuple: just Pro+Tem+Con at strides 1 (adjacent) and known classic gaps
            lines.append("\n=== Pro/Tem/Con triple patterns near primary ===")
            # classic: Pro at +0, Spo +1, Tem +2 relative inside block
            # Try find Pro=20 for paco and Tem=15 for kizza at fixed gap
            for gap in range(0, 16):
                for rel in range(-128, 256):
                    vp = mm[primary["paco"] + rel]
                    if vp != 20:
                        continue
                    vk = mm[primary["kizza"] + rel + gap]
                    if vk != 15:
                        continue
                    # tassinari tem in 3-6 at same gap from his pro? or tem at rel+gap
                    vt = mm[primary["tassinari"] + rel + gap]
                    if not (3 <= vt <= 6):
                        continue
                    # seimen pro at rel in 18-19
                    vs = mm[primary["seimen"] + rel]
                    if not (18 <= vs <= 19):
                        continue
                    lines.append(
                        f"  Pro@rel Tem@rel+{gap}: pacoPro={vp} kizzaTem={vk} "
                        f"tassTem={vt} seimenPro={vs} rel={rel}"
                    )

        finally:
            mm.close()
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(
            x in line
            for x in (
                "trio_hits=",
                "transfer rels=",
                "all5=",
                "Pro@rel",
                "primary",
                "hits=",
            )
        ):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
