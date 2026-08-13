#!/usr/bin/env python3
"""Inspect every UniqueID hit neighborhood for the calibration 5,
especially non-primary / non-double hits and Tem@+63 lead."""

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
OUT = ROOT / "tmp" / "fm-spike" / "ha-uid-hits.txt"
ZSTD_OFF = 26
SCAN_CAP = 512 * 1024 * 1024  # then also full file for secondary

PLAYERS = {
    "kizza": 2002185604,
    "paco": 2000136577,
    "tassinari": 2002083070,
    "seimen": 2000175080,
    "yoan": 2002089146,
}


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-hits-", suffix=".bin")
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


def collect(mm, uid, end):
    pat = struct.pack("<I", uid)
    hits = []
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 50:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def in_band(v, band):
    return band[0] <= v <= band[1]


def main() -> int:
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    tmp = decompress(SAVE)
    lines = []
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            all_hits = {}
            # FULL file scan for UIDs (may be slow but critical)
            for k, uid in PLAYERS.items():
                all_hits[k] = collect(mm, uid, len(mm))
                lines.append(f"{k}: hits={len(all_hits[k])} {all_hits[k]}")

            # Dump ±64 around each hit
            lines.append("\n=== neighborhoods ===")
            for k, uid in PLAYERS.items():
                lines.append(f"\n-- {k} --")
                for h in all_hits[k]:
                    lo = max(0, h - 32)
                    blob = bytes(mm[lo : h + 96])
                    # detect double
                    is_double = h + 4 < len(mm) and struct.unpack_from("<I", mm, h + 4)[0] == uid
                    is_prev_double = h >= 4 and struct.unpack_from("<I", mm, h - 4)[0] == uid
                    lines.append(f"  @{h} double={is_double} prevDouble={is_prev_double}")
                    lines.append(f"    hex: {blob.hex(' ')}")
                    # bytes at +42..+70 from hit (after-double personality area when double)
                    after = bytes(mm[h : h + 128])
                    lines.append(f"    +32..80: {list(after[32:80])}")

            # Verify Tem@rel for EACH combination of hits (trio), find which hit trio works
            lines.append("\n=== Tem: which hit combo works for trio at same rel ===")
            tem_combos = []
            for rel in range(-128, 256):
                for hk in all_hits["kizza"]:
                    vk = mm[hk + rel] if 0 <= hk + rel < len(mm) else None
                    if vk != 15:
                        continue
                    for hp in all_hits["paco"]:
                        vp = mm[hp + rel] if 0 <= hp + rel < len(mm) else None
                        if vp is None or not in_band(vp, cal[PLAYERS["paco"]]["bands"]["temperament"]):
                            continue
                        for ht in all_hits["tassinari"]:
                            vt = mm[ht + rel] if 0 <= ht + rel < len(mm) else None
                            if vt is None or not in_band(
                                vt, cal[PLAYERS["tassinari"]]["bands"]["temperament"]
                            ):
                                continue
                            # validators
                            valids = {}
                            ok5 = True
                            for vkname in ("seimen", "yoan"):
                                found = None
                                for hs in all_hits[vkname]:
                                    vs = mm[hs + rel] if 0 <= hs + rel < len(mm) else None
                                    if vs is None:
                                        continue
                                    if in_band(vs, cal[PLAYERS[vkname]]["bands"]["temperament"]) and 1 <= vs <= 20:
                                        found = (hs, vs)
                                        break
                                if not found:
                                    ok5 = False
                                    break
                                valids[vkname] = found
                            tem_combos.append(
                                (
                                    ok5,
                                    rel,
                                    {"kizza": (hk, vk), "paco": (hp, vp), "tassinari": (ht, vt), **valids},
                                )
                            )
            # dedupe
            seen = set()
            uniq = []
            for ok5, rel, pos in tem_combos:
                key = (ok5, rel, tuple(sorted((k, v[0], v[1]) for k, v in pos.items())))
                if key in seen:
                    continue
                seen.add(key)
                uniq.append((ok5, rel, pos))
            uniq.sort(key=lambda t: (not t[0], abs(t[1])))
            lines.append(f"Tem combos={len(uniq)}")
            for ok5, rel, pos in uniq[:40]:
                lines.append(f"  all5={ok5} rel={rel}")
                for k, (p, v) in pos.items():
                    lines.append(f"    {k}: hit={p} val={v}")

            # Same for Professionalism
            lines.append("\n=== Pro: which hit combo works for trio at same rel ===")
            pro_combos = []
            for rel in range(-128, 256):
                for hp in all_hits["paco"]:
                    vp = mm[hp + rel] if 0 <= hp + rel < len(mm) else None
                    if vp != 20:
                        continue
                    for hk in all_hits["kizza"]:
                        vk = mm[hk + rel] if 0 <= hk + rel < len(mm) else None
                        if vk is None or not in_band(vk, cal[PLAYERS["kizza"]]["bands"]["professionalism"]):
                            continue
                        for ht in all_hits["tassinari"]:
                            vt = mm[ht + rel] if 0 <= ht + rel < len(mm) else None
                            if vt is None or not in_band(
                                vt, cal[PLAYERS["tassinari"]]["bands"]["professionalism"]
                            ):
                                continue
                            valids = {}
                            ok5 = True
                            for vkname in ("seimen", "yoan"):
                                found = None
                                for hs in all_hits[vkname]:
                                    vs = mm[hs + rel] if 0 <= hs + rel < len(mm) else None
                                    if vs is None:
                                        continue
                                    if in_band(vs, cal[PLAYERS[vkname]]["bands"]["professionalism"]) and 1 <= vs <= 20:
                                        locks = cal[PLAYERS[vkname]].get("locks") or {}
                                        if "professionalism" in locks and vs != locks["professionalism"]:
                                            continue
                                        found = (hs, vs)
                                        break
                                if not found:
                                    ok5 = False
                                    break
                                valids[vkname] = found
                            pro_combos.append(
                                (
                                    ok5,
                                    rel,
                                    {"kizza": (hk, vk), "paco": (hp, vp), "tassinari": (ht, vt), **valids},
                                )
                            )
            seen = set()
            uniq = []
            for ok5, rel, pos in pro_combos:
                key = (ok5, rel, tuple(sorted((k, v[0], v[1]) for k, v in pos.items())))
                if key in seen:
                    continue
                seen.add(key)
                uniq.append((ok5, rel, pos))
            uniq.sort(key=lambda t: (not t[0], abs(t[1])))
            lines.append(f"Pro combos={len(uniq)}")
            for ok5, rel, pos in uniq[:40]:
                lines.append(f"  all5={ok5} rel={rel}")
                for k, (p, v) in pos.items():
                    lines.append(f"    {k}: hit={p} val={v}")

            # Look at Paco secondary hits regions comparatively
            lines.append("\n=== Paco non-double hits detail ===")
            for h in all_hits["paco"]:
                is_double = h + 4 < len(mm) and struct.unpack_from("<I", mm, h + 4)[0] == PLAYERS["paco"]
                is_prev = h >= 4 and struct.unpack_from("<I", mm, h - 4)[0] == PLAYERS["paco"]
                if is_double or is_prev:
                    continue
                blob = bytes(mm[h - 64 : h + 128])
                lines.append(f"@{h}:")
                for i in range(0, len(blob), 16):
                    chunk = blob[i : i + 16]
                    abs_off = h - 64 + i
                    lines.append(f"  {abs_off}: {chunk.hex(' ')}")
                # u32s around
                for i in range(0, len(blob) - 3, 4):
                    v = struct.unpack_from("<I", blob, i)[0]
                    if v in PLAYERS.values() or (1000 < v < 400000 and v % 1 == 0):
                        if v in PLAYERS.values() or (100000 < v < 400000):
                            lines.append(f"  u32@{h-64+i}={v}")

            # Kizza early hit
            lines.append("\n=== Kizza non-primary hit detail ===")
            for h in all_hits["kizza"]:
                is_double = h + 4 < len(mm) and struct.unpack_from("<I", mm, h + 4)[0] == PLAYERS["kizza"]
                is_prev = h >= 4 and struct.unpack_from("<I", mm, h - 4)[0] == PLAYERS["kizza"]
                if is_double or is_prev:
                    continue
                blob = bytes(mm[h - 64 : h + 128])
                lines.append(f"@{h}:")
                for i in range(0, len(blob), 16):
                    chunk = blob[i : i + 16]
                    lines.append(f"  {h-64+i}: {chunk.hex(' ')}")

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
        if any(x in line for x in ("hits=", "all5=", "Tem combos", "Pro combos", "non-double", "non-primary", "  all5=")):
            print(line.encode("ascii", "replace").decode())
        if line.startswith("  all5=") or line.startswith("    "):
            if "hit=" in line or line.startswith("  all5="):
                print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
