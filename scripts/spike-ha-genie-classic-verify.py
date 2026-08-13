#!/usr/bin/env python3
"""Verify Genie mental packs near person doubles; report shared rels."""

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
TABLE = ROOT / "data" / "fixtures" / "ha-genie-table.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-genie-classic-verify.txt"

ORDERS = {
    "classic7": [
        "ambition", "loyalty", "pressure", "professionalism",
        "sportsmanship", "temperament", "controversy",
    ],
    "classic8": [
        "ambition", "loyalty", "pressure", "professionalism",
        "sportsmanship", "temperament", "controversy", "importantMatches",
    ],
    "gs8": [
        "adaptability", "ambition", "controversy", "loyalty",
        "pressure", "professionalism", "sportsmanship", "temperament",
    ],
    "cm7": [
        "adaptability", "ambition", "loyalty",
        "pressure", "professionalism", "sportsmanship", "temperament",
    ],
    "loy_tail5": [
        "loyalty", "pressure", "professionalism", "sportsmanship", "temperament",
    ],
    "match5": [
        "consistency", "dirtiness", "importantMatches",
        "injuryProneness", "versatility",
    ],
}


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-gcv-", suffix=".bin")
    os.close(fd)
    tmp = Path(name)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(26)
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


def pack_bytes(p: dict, keys: list[str]) -> bytes | None:
    m = p["mental"]
    mh = p["matchHidden"]
    out = []
    for k in keys:
        if k in m:
            out.append(m[k])
        elif k in mh:
            out.append(mh[k])
        else:
            return None
    return bytes(out)


def find_all(mm, pat: bytes, limit=40) -> list[int]:
    hits = []
    j = mm.find(pat)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(pat, j + 1)
    return hits


def best_double(mm, uid: int) -> tuple[int | None, int]:
    doubles = find_all(mm, struct.pack("<II", uid, uid), limit=20)
    best = None
    best_score = -1
    for d in doubles:
        blob = bytes(mm[d : d + 128])
        score = 0
        if b"\x01\x01\x01" in blob[8:80]:
            score += 5
        if len(blob) > 8 and blob[8] in (1, 2):
            score += 1
        if score > best_score:
            best_score = score
            best = d
    return best, best_score


def main() -> int:
    players = [
        p for p in json.loads(TABLE.read_text(encoding="utf-8"))["players"]
        if p.get("status") == "complete"
    ]
    lines = [f"players={len(players)}"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print("decompressing…", flush=True)
    tmp = decompress(SAVE)
    # order -> list of (name, rel) for unique/near hits
    rel_map: dict[str, list[tuple[str, int, int]]] = {k: [] for k in ORDERS}

    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for p in players:
                    name = p["name"]
                    best, score = best_double(mm, p["uid"])
                    lines.append(f"\n=== {name} double@{best} score={score} ===")
                    for label, keys in ORDERS.items():
                        needle = pack_bytes(p, keys)
                        if not needle:
                            continue
                        hits = find_all(mm, needle, limit=30)
                        near = [(h, h - best) for h in hits if best is not None and abs(h - best) <= 16384]
                        lines.append(
                            f"  {label} {list(needle)}: hits={len(hits)} near={near[:6]}"
                        )
                        # record unique global or near
                        if len(hits) == 1:
                            h = hits[0]
                            rel = (h - best) if best is not None else None
                            lines.append(f"    UNIQUE abs={h} rel={rel}")
                            if rel is not None:
                                rel_map[label].append((name, rel, h))
                                ctx = bytes(mm[h - 12 : h + len(needle) + 12])
                                lines.append(f"    ctx={ctx.hex(' ')}")
                        elif near:
                            h, rel = min(near, key=lambda t: abs(t[1]))
                            rel_map[label].append((name, rel, h))
                            ctx = bytes(mm[h - 12 : h + len(needle) + 12])
                            lines.append(f"    closest abs={h} rel={rel:+d} ctx={ctx.hex(' ')}")

                lines.append("\n=== REL SUMMARY ===")
                for label, rows in rel_map.items():
                    lines.append(f"{label}: {rows}")
                    if len(rows) >= 2:
                        rels = [r for _, r, _ in rows]
                        lines.append(f"  rels={rels}")
            finally:
                mm.close()
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in ("===", "UNIQUE", "closest", "REL", "hits=", "rels=")):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
