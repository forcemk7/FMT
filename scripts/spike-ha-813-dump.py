#!/usr/bin/env python3
from __future__ import annotations

import json
import mmap
import os
import struct
import tempfile
from itertools import product
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-813-dump.txt"
ZSTD_OFF = 26

PLAYERS = {
    "kizza": 2002185604,
    "paco": 2000136577,
    "tassinari": 2002083070,
    "seimen": 2000175080,
    "yoan": 2002089146,
}
ALL = list(PLAYERS)


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-813d-", suffix=".bin")
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


def collect(mm, uid):
    pat = struct.pack("<I", uid)
    hits = []
    j = mm.find(pat, 0)
    while j >= 0 and len(hits) < 80:
        hits.append(j)
        j = mm.find(pat, j + 1)
    return hits


def in_band(v, b):
    return b[0] <= v <= b[1]


def main() -> int:
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    tmp = decompress(SAVE)
    lines = []
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hits = {k: collect(mm, uid) for k, uid in PLAYERS.items()}
            lo, hi = 812000000, 814200000
            events = []
            for k, hs in hits.items():
                for h in hs:
                    if lo <= h < hi:
                        events.append((h, k))
            events.sort()
            lines.append("=== hits 812-814.2M ===")
            for h, k in events:
                prev = bytes(mm[h - 16 : h])
                after = bytes(mm[h : h + 64])
                lines.append(f"{h} {k:10s} prev={prev.hex(' ')}")
                lines.append(f"           after={after.hex(' ')}")
                lines.append(f"           u8={list(after[:48])}")

            center = 813300000
            pos = {
                k: min([h for h in hits[k] if lo <= h < hi], key=lambda x: abs(x - center))
                for k in ALL
            }
            lines.append(f"\nchosen nearest-center pos={pos}")

            for attr in (
                "professionalism",
                "temperament",
                "pressure",
                "controversy",
                "sportsmanship",
                "loyalty",
                "ambition",
            ):
                good = []
                for rel in range(-128, 256):
                    vals = {}
                    ok = True
                    for k in ALL:
                        v = mm[pos[k] + rel]
                        locks = cal[PLAYERS[k]].get("locks") or {}
                        if not (1 <= v <= 20) or not in_band(v, cal[PLAYERS[k]]["bands"][attr]):
                            ok = False
                            break
                        if attr in locks and v != locks[attr]:
                            ok = False
                            break
                        vals[k] = v
                    if ok:
                        good.append((rel, vals))
                lines.append(f"{attr} fixed-hit fits={len(good)} {good[:8]}")

            rh = {k: [h for h in hits[k] if lo <= h < hi] for k in ALL}
            lines.append(f"\nregion hit counts={ {k: len(v) for k, v in rh.items()} }")

            # Tem combos (limit 5 hits each to keep cartesian smaller: 5^5=3125)
            lines.append("\n=== Tem combo (up to 5 hits/player) ===")
            tem = []
            for rel in range(-64, 128):
                found = None
                for combo in product(*[rh[k][:5] for k in ALL]):
                    vals = {}
                    ok = True
                    for k, h in zip(ALL, combo):
                        v = mm[h + rel]
                        locks = cal[PLAYERS[k]].get("locks") or {}
                        if not (1 <= v <= 20) or not in_band(
                            v, cal[PLAYERS[k]]["bands"]["temperament"]
                        ):
                            ok = False
                            break
                        if "temperament" in locks and v != locks["temperament"]:
                            ok = False
                            break
                        vals[k] = (h, v)
                    if ok:
                        found = vals
                        break
                if found:
                    tem.append((rel, found))
            lines.append(f"Tem rels={len(tem)}")
            for rel, vals in tem[:20]:
                lines.append(f"  rel={rel} {vals}")

            lines.append("\n=== Pro combo (up to 5 hits/player) ===")
            pro = []
            for rel in range(-64, 128):
                found = None
                for combo in product(*[rh[k][:5] for k in ALL]):
                    vals = {}
                    ok = True
                    for k, h in zip(ALL, combo):
                        v = mm[h + rel]
                        locks = cal[PLAYERS[k]].get("locks") or {}
                        if not (1 <= v <= 20) or not in_band(
                            v, cal[PLAYERS[k]]["bands"]["professionalism"]
                        ):
                            ok = False
                            break
                        if "professionalism" in locks and v != locks["professionalism"]:
                            ok = False
                            break
                        vals[k] = (h, v)
                    if ok:
                        found = vals
                        break
                if found:
                    pro.append((rel, found))
            lines.append(f"Pro rels={len(pro)}")
            for rel, vals in pro[:20]:
                lines.append(f"  rel={rel} {vals}")

            # Look at hit pairs with delta 290 (seimen/paco pattern)
            lines.append("\n=== pairs with delta 290 ===")
            for a in ALL:
                for b in ALL:
                    if a >= b:
                        continue
                    for pa in rh[a]:
                        for pb in rh[b]:
                            if abs(pb - pa) == 290:
                                lines.append(f"{a}@{pa} {b}@{pb}")
                                lines.append(f"  A: {list(mm[pa:pa+64])}")
                                lines.append(f"  B: {list(mm[pb:pb+64])}")
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
        if any(
            x in line
            for x in (
                "fits=",
                "Tem rels",
                "Pro rels",
                "rel=",
                "delta 290",
                "chosen",
                "counts",
                "pairs",
            )
        ):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
