#!/usr/bin/env python3
"""Hunt HA mental-trait pack history near person doubles."""
from __future__ import annotations

import importlib.util
import mmap
import os
import struct
import tempfile
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "eft", ROOT / "scripts" / "extract-first-team-fast.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

# A few FT players with known packs / recent CA change interest
TARGETS = {
    2002282525: "Sipho Sithole",
    2002266504: "Lukas Abbe",
    2002158957: "Adrian Itu",  # may be wrong; resolve from extract if needed
}


def decompress(save: Path) -> Path:
    zstd_off = int(mod.probe_container(save)["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-ha-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)
    n = 0
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zstd_off)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    chunk = reader.read(8 << 20)
                except zstd.ZstdError:
                    if n == 0:
                        raise
                    break
                if not chunk:
                    break
                out.write(chunk)
                n += len(chunk)
        finally:
            reader.close()
    return tmp


def pack_l1(a: bytes, b: bytes) -> int:
    return sum(abs(x - y) for x, y in zip(a, b))


def find_all_packs_in_window(window: bytes, base_abs: int) -> list[tuple[int, bytes, bytes]]:
    """Return (abs_pack, raw8, trail2) for signature hits."""
    out = []
    start = 0
    while True:
        j = window.find(mod.MENTAL_HA_TRAIL, start)
        if j < 0:
            break
        pack_off = j - 10
        if pack_off >= 0:
            raw = window[pack_off : pack_off + 8]
            trail2 = window[pack_off + 8 : pack_off + 10]
            if len(raw) == 8 and all(1 <= b <= 20 for b in raw):
                lead = window[max(0, pack_off - 6) : pack_off]
                if lead.count(0) >= 4:
                    out.append((base_abs + pack_off, bytes(raw), bytes(trail2)))
        start = j + 1
    return out


def named(raw: bytes) -> dict[str, int]:
    return {k: int(raw[i]) for i, k in enumerate(mod.PERSONALITY_PACK_ORDER)}


def analyze_player(mm: mmap.mmap, uid: int, name: str) -> None:
    doubles = mod.collect_doubles(mm, uid)
    print(f"\n==== {name} uid={uid} doubles={len(doubles)}")
    if not doubles:
        return
    pack = mod.find_mental_trait_pack(mm, doubles)
    if not pack:
        print("  no live pack")
        return
    vals, pack_abs, dab = pack
    print(f"  live pack@{pack_abs} dab@{dab} rel={pack_abs - dab}")
    print(f"  live {vals}")
    live_raw = bytes(vals[k] for k in mod.PERSONALITY_PACK_ORDER)

    # Wide windows around each double
    for look_back, look_ahead, label in [
        (2_048, 4_096, "current"),
        (20_000, 20_000, "20k"),
        (80_000, 40_000, "80k"),
        (200_000, 50_000, "200k"),
    ]:
        all_hits = []
        for dab2 in doubles:
            lo = max(0, dab2 - look_back)
            hi = min(len(mm), dab2 + look_ahead)
            hits = find_all_packs_in_window(bytes(mm[lo:hi]), lo)
            for abs_pack, raw, t2 in hits:
                all_hits.append((abs_pack - dab2, abs_pack, raw, t2, dab2))
        # unique by abs
        by_abs = {}
        for rel, abs_pack, raw, t2, dab2 in all_hits:
            by_abs[abs_pack] = (rel, raw, t2, dab2)
        cont = []
        for abs_pack, (rel, raw, t2, dab2) in by_abs.items():
            l1 = pack_l1(live_raw, raw)
            cont.append((l1, rel, abs_pack, raw, t2))
        cont.sort()
        print(f"  [{label}] signature packs={len(by_abs)} continuous L1<=8: {sum(1 for x in cont if x[0] <= 8)}")
        # show best continuous / near
        shown = 0
        for l1, rel, abs_pack, raw, t2 in cont:
            if l1 > 12 and shown >= 8:
                continue
            if shown >= 12:
                break
            mark = " LIVE" if abs_pack == pack_abs else ""
            if l1 <= 8:
                mark += " CONT"
            print(
                f"    L1={l1:2d} rel={rel:6d} raw={list(raw)} t2={list(t2)}{mark}"
            )
            shown += 1

    # Whole-file search for exact live pack raw
    needle = live_raw
    hits = []
    step = 8 << 20
    size = len(mm)
    pos = 0
    while pos < size:
        chunk = bytes(mm[pos : min(size, pos + step + 8)])
        start = 0
        while True:
            j = chunk.find(needle, start)
            if j < 0:
                break
            abs_off = pos + j
            # require trail nearby
            trail_ok = bytes(mm[abs_off + 10 : abs_off + 17]) == mod.MENTAL_HA_TRAIL
            hits.append((abs_off - dab, abs_off, trail_ok))
            start = j + 1
        pos += step
    print(f"  whole-file exact live raw hits={len(hits)} (showing ≤15)")
    for rel, abs_off, trail_ok in hits[:15]:
        print(f"    rel={rel} abs={abs_off} trail={trail_ok}")


def resolve_itu_uid(mm: mmap.mmap) -> int | None:
    # try extract json
    import json
    for p in [
        ROOT / "tmp" / "extract-1911.json",
        ROOT / "tmp" / "lawal-extract.json",
    ]:
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        for pl in d.get("players") or []:
            if "Itu" in (pl.get("name") or ""):
                return int(pl["uid"])
    return TARGETS.get(2002158957)


def main() -> int:
    save = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[0]
    print("save", save.name)
    print("PACK_ORDER", mod.PERSONALITY_PACK_ORDER)
    print("TRAIL", list(mod.MENTAL_HA_TRAIL))
    print("LOOKBACK/AHEAD", mod.MENTAL_HA_LOOKBACK, mod.MENTAL_HA_LOOKAHEAD)

    tmp = decompress(save)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                itu = resolve_itu_uid(mm)
                targets = {
                    2002282525: "Sipho Sithole",
                    2002266504: "Lukas Abbe",
                }
                if itu:
                    targets[itu] = "Adrian Itu"
                for uid, name in targets.items():
                    analyze_player(mm, uid, name)
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
