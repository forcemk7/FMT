#!/usr/bin/env python3
"""Compare HA packs across saves + hunt alt encodings / trailer-linked history."""
from __future__ import annotations

import importlib.util
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "eft", ROOT / "scripts" / "extract-first-team-fast.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

UIDS = {
    2002282525: "Sipho",
    2002266504: "Abbe",
    2002400248: "Itu",
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


def live_pack(mm, uid):
    doubles = mod.collect_doubles(mm, uid)
    pack = mod.find_mental_trait_pack(mm, doubles)
    if not pack:
        return None
    vals, abs_pack, dab = pack
    raw = bytes(vals[k] for k in mod.PERSONALITY_PACK_ORDER)
    t2 = bytes(mm[abs_pack + 8 : abs_pack + 10])
    return vals, raw, t2, abs_pack, dab


def find_raw(mm, needle: bytes) -> list[int]:
    hits = []
    step = 8 << 20
    size = len(mm)
    pos = 0
    while pos < size:
        chunk = bytes(mm[pos : min(size, pos + step + len(needle))])
        start = 0
        while True:
            j = chunk.find(needle, start)
            if j < 0:
                break
            hits.append(pos + j)
            start = j + 1
        pos += step
    return hits


def main() -> int:
    saves = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:4]
    # Cross-save pack values
    by_save = {}
    tmps = []
    try:
        for save in saves:
            label = save.name.split("date ")[-1][:10] if "date " in save.name else save.name
            print(f"\n######## {label}")
            tmp = decompress(save)
            tmps.append(tmp)
            with tmp.open("rb") as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                try:
                    by_save[label] = {}
                    for uid, name in UIDS.items():
                        hit = live_pack(mm, uid)
                        if not hit:
                            print(f"  {name}: no pack")
                            continue
                        vals, raw, t2, abs_pack, dab = hit
                        by_save[label][name] = (vals, raw, t2)
                        print(
                            f"  {name}: {vals} t2={list(t2)} rel={abs_pack-dab}"
                        )
                finally:
                    mm.close()

        print("\n======== cross-save diffs (vs newest)")
        newest = list(by_save.keys())[0]
        for name in UIDS.values():
            if name not in by_save[newest]:
                continue
            print(f"\n-- {name}")
            nvals, nraw, nt2 = by_save[newest][name]
            for label, packs in by_save.items():
                if name not in packs:
                    continue
                vals, raw, t2 = packs[name]
                diffs = {
                    k: (vals[k], nvals[k])
                    for k in mod.PERSONALITY_PACK_ORDER
                    if vals[k] != nvals[k]
                }
                print(f"  {label}: diffs={diffs or 'none'} t2_same={t2==nt2}")

        # On newest save: for any older pack raw that differs, search if still present
        print("\n======== do older pack values survive in newest save?")
        newest_save = saves[0]
        tmp = decompress(newest_save)
        tmps.append(tmp)
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for name in UIDS.values():
                    if name not in by_save[newest]:
                        continue
                    nraw = by_save[newest][name][1]
                    for label, packs in by_save.items():
                        if label == newest or name not in packs:
                            continue
                        oraw = packs[name][1]
                        if oraw == nraw:
                            print(f"  {name} {label}: identical to newest")
                            continue
                        hits = find_raw(mm, oraw)
                        trailed = [
                            h
                            for h in hits
                            if bytes(mm[h + 10 : h + 17]) == mod.MENTAL_HA_TRAIL
                        ]
                        print(
                            f"  {name} {label} raw={list(oraw)} hits={len(hits)} trailed={len(trailed)}"
                        )
            finally:
                mm.close()

        # Alt encoding: ×5 pack near dab for Sipho live values
        print("\n======== alt encodings near Sipho pack (newest)")
        tmp = decompress(newest_save)
        tmps.append(tmp)
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                vals, raw, t2, abs_pack, dab = live_pack(mm, 2002282525)
                x5 = bytes(v * 5 for v in raw)
                region = bytes(mm[dab - 5000 : dab + 2000])
                base = dab - 5000
                # exact ×5
                j = region.find(x5)
                print(f"  ×5 contiguous near dab: {j if j<0 else base+j-dab}")
                # exact raw without requiring trail, scan ±5k for all 8-byte 1-20 with L1<=3 to live
                near = []
                for i in range(len(region) - 8):
                    b = region[i : i + 8]
                    if not all(1 <= x <= 20 for x in b):
                        continue
                    l1 = sum(abs(x - y) for x, y in zip(b, raw))
                    if l1 <= 3:
                        near.append((base + i - dab, l1, list(b)))
                near.sort(key=lambda t: (t[1], abs(t[0])))
                print(f"  raw8 L1<=3 near dab (±5k): {near[:20]}")
                # Genie classic order? Amb Cont Loy etc — skip unless needed
            finally:
                mm.close()
    finally:
        for t in tmps:
            t.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
