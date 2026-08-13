#!/usr/bin/env python3
"""Focus global HA hunt on dense UID clusters (esp ~813MB region)."""

from __future__ import annotations

import json
import mmap
import os
import struct
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-cluster-813.txt"
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

ORDERS = {
    "user": [
        "professionalism", "pressure", "ambition", "importantMatches",
        "sportsmanship", "temperament", "loyalty", "controversy",
    ],
    "pro_tem": [
        "professionalism", "temperament", "pressure", "ambition",
        "loyalty", "sportsmanship", "controversy", "importantMatches",
    ],
    "gs1": [
        "professionalism", "ambition", "loyalty", "pressure",
        "temperament", "sportsmanship", "controversy", "importantMatches",
    ],
}


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-813-", suffix=".bin")
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


def in_band(v, band):
    return band[0] <= v <= band[1]


def ok_tuple(raw, bands, order, locks):
    for i, key in enumerate(order):
        v = raw[i]
        if not (1 <= v <= 20) or not in_band(v, bands[key]):
            return False
        if key in locks and v != locks[key]:
            return False
    return True


def cluster_hits(hits, lo, hi):
    return [h for h in hits if lo <= h < hi]


def main() -> int:
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    meta = {k: cal[uid] for k, uid in PLAYERS.items()}
    tmp = decompress(SAVE)
    lines = []
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hits = {k: collect(mm, uid) for k, uid in PLAYERS.items()}

            # Discover dense windows: slide 2MB windows, count players present
            lines.append("=== dense 2MB windows with >=4 players ===")
            all_pos = sorted({h for hs in hits.values() for h in hs})
            windows = []
            for start in range(0, len(mm), 1_000_000):
                end = start + 2_000_000
                present = {
                    k: [h for h in hits[k] if start <= h < end] for k in ALL
                }
                n = sum(1 for k in ALL if present[k])
                if n >= 4:
                    windows.append((start, n, {k: len(present[k]) for k in ALL}, present))
            for start, n, counts, _ in windows[:30]:
                lines.append(f"win@{start}: players={n} counts={counts}")

            # Analyze top regions of interest
            regions = [
                ("813M", 800_000_000, 830_000_000),
                ("1958M", 1_950_000_000, 1_970_000_000),
                ("1981M", 1_975_000_000, 1_990_000_000),
                ("1007M", 1_000_000_000, 1_020_000_000),
            ]

            for rname, lo, hi in regions:
                lines.append(f"\n======== region {rname} [{lo},{hi}) ========")
                rh = {k: cluster_hits(hits[k], lo, hi) for k in ALL}
                for k in ALL:
                    lines.append(f"{k}: {rh[k]}")
                # pairwise deltas
                deltas = Counter()
                for a in ALL:
                    for b in ALL:
                        if a >= b:
                            continue
                        for pa in rh[a]:
                            for pb in rh[b]:
                                d = abs(pb - pa)
                                if 16 <= d <= 20000:
                                    deltas[d] += 1
                lines.append(f"common pairwise deltas (top): {deltas.most_common(20)}")

                # residue analysis for candidate strides
                for stride in [48, 56, 64, 68, 69, 72, 76, 77, 80, 96, 100, 104, 112, 128, 136, 144, 160, 192, 200, 256]:
                    residues = None
                    for k in ALL:
                        if not rh[k]:
                            residues = set()
                            break
                        rset = {h % stride for h in rh[k]}
                        residues = rset if residues is None else (residues & rset)
                    if residues:
                        lines.append(f"stride={stride} shared_residues={sorted(residues)[:12]} n={len(residues)}")

                # For each player pick the FIRST hit in region; scan rel for HA
                # Require same residue class - pick residue with most players
                for stride in [64, 72, 77, 80, 96, 112, 128, 144]:
                    # build residue -> {player: [hits]}
                    by_res = defaultdict(lambda: defaultdict(list))
                    for k in ALL:
                        for h in rh[k]:
                            by_res[h % stride][k].append(h)
                    # residues with all 5
                    full = [r for r, m in by_res.items() if len(m) == 5]
                    if not full:
                        continue
                    lines.append(f"\nstride={stride} full residues={full[:10]}")
                    for resid in full[:5]:
                        # use first hit per player
                        pos = {k: by_res[resid][k][0] for k in ALL}
                        lines.append(f"  resid={resid} pos={pos}")
                        # dump 32 bytes after each UID
                        for k in ALL:
                            blob = bytes(mm[pos[k] : pos[k] + 48])
                            lines.append(f"    {k}+0..47: {list(blob)}")
                        # scan relative offsets for 8-byte HA packs
                        found = []
                        for rel in range(-64, 200):
                            for enc in ("raw",):
                                for ord_name, order in ORDERS.items():
                                    ok = True
                                    decoded = {}
                                    for k in ALL:
                                        raw = bytes(mm[pos[k] + rel : pos[k] + rel + 8])
                                        if len(raw) < 8 or not ok_tuple(
                                            raw, meta[k]["bands"], order, meta[k].get("locks") or {}
                                        ):
                                            ok = False
                                            break
                                        decoded[k] = list(raw)
                                    if ok:
                                        found.append((rel, ord_name, decoded))
                        lines.append(f"  8-byte HA fits: {len(found)}")
                        for rel, ord_name, decoded in found[:10]:
                            lines.append(f"    rel={rel} order={ord_name} {decoded}")

                        # single-attr fits at same rel
                        for attr in ("professionalism", "temperament", "pressure", "controversy", "sportsmanship"):
                            ahits = []
                            for rel in range(-64, 200):
                                vals = {}
                                ok = True
                                for k in ALL:
                                    v = mm[pos[k] + rel]
                                    locks = meta[k].get("locks") or {}
                                    if not (1 <= v <= 20) or not in_band(v, meta[k]["bands"][attr]):
                                        ok = False
                                        break
                                    if attr in locks and v != locks[attr]:
                                        ok = False
                                        break
                                    vals[k] = v
                                if ok:
                                    ahits.append((rel, vals))
                            if ahits:
                                lines.append(f"  {attr} single-byte fits: {len(ahits)}")
                                for rel, vals in ahits[:8]:
                                    lines.append(f"    rel={rel} {vals}")

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
                "win@",
                "========",
                "common pairwise",
                "stride=",
                "8-byte",
                "single-byte",
                "full residues",
                "rel=",
            )
        ):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
