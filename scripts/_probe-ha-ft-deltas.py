#!/usr/bin/env python3
"""Find any FT player whose HA pack changed across saves; check old pack survival."""
from __future__ import annotations

import importlib.util
import json
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


def load_uids() -> list[tuple[int, str]]:
    p = ROOT / "tmp" / "extract-1911.json"
    d = json.loads(p.read_text(encoding="utf-8-sig"))
    return [(int(pl["uid"]), pl["name"]) for pl in d["players"]]


def packs_for_save(save: Path, uids: list[tuple[int, str]]):
    tmp = decompress(save)
    out = {}
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for uid, name in uids:
                    doubles = mod.collect_doubles(mm, uid)
                    pack = mod.find_mental_trait_pack(mm, doubles)
                    if not pack:
                        continue
                    vals, abs_pack, dab = pack
                    raw = bytes(vals[k] for k in mod.PERSONALITY_PACK_ORDER)
                    out[uid] = {
                        "name": name,
                        "vals": vals,
                        "raw": raw,
                        "abs": abs_pack,
                        "dab": dab,
                    }
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)
    return out


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
    uids = load_uids()
    saves = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    newest, older = saves[0], saves[3]  # 01.12 vs 07.11
    print("compare", older.name, "->", newest.name, "n players", len(uids))
    old_packs = packs_for_save(older, uids)
    new_packs = packs_for_save(newest, uids)
    print("packs old", len(old_packs), "new", len(new_packs))

    changed = []
    for uid, op in old_packs.items():
        np = new_packs.get(uid)
        if not np:
            continue
        if op["raw"] != np["raw"]:
            diffs = {
                k: (op["vals"][k], np["vals"][k])
                for k in mod.PERSONALITY_PACK_ORDER
                if op["vals"][k] != np["vals"][k]
            }
            changed.append((uid, op["name"], diffs, op["raw"], np["raw"]))

    print(f"changed packs: {len(changed)}")
    for uid, name, diffs, oraw, nraw in changed:
        print(f"  {name} ({uid}): {diffs}")

    if not changed:
        print("No HA pack deltas across FT between these saves.")
        print("Cannot validate history retention without an observed HA change.")
        return 0

    # Check whether old raw survives in newest save
    tmp = decompress(newest)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for uid, name, diffs, oraw, nraw in changed:
                    hits = find_raw(mm, oraw)
                    trailed = [
                        h
                        for h in hits
                        if bytes(mm[h + 10 : h + 17]) == mod.MENTAL_HA_TRAIL
                    ]
                    print(
                        f"  survival {name}: old_raw hits={len(hits)} trailed={len(trailed)}"
                    )
                    # near new dab?
                    dab = new_packs[uid]["dab"]
                    near = [h - dab for h in trailed if abs(h - dab) < 50_000]
                    print(f"    trailed near dab: {near[:20]}")
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
