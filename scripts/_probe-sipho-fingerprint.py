#!/usr/bin/env python3
"""Search 22.11 save for Sipho FM-live mental fingerprint near person double."""
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

UID = 2002282525

# FM screenshot live attrs (22.11)
FM_MENTAL = {
    "aggression": 8,
    "anticipation": 13,
    "bravery": 8,
    "vision": 13,
    "decisions": 12,
    "determination": 15,
    "flair": 17,
    "leadership": 4,
    "offTheBall": 16,
    "positioning": 10,
    "teamwork": 12,
    "workRate": 12,
    "composure": 13,
    "concentration": 10,
}

FM_PHYS = {
    "acceleration": 16,
    "agility": 16,
    "balance": 14,
    "pace": 16,
    "stamina": 14,
    "strength": 10,
    "jumpingReach": 7,
    "naturalFitness": 16,
}


def decompress(save: Path) -> Path:
    zstd_off = int(mod.probe_container(save)["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-p-", suffix=".bin")
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


def main() -> int:
    save = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[0]
    print("save", save.name)
    print("MENTAL", mod.MENTAL)
    ordered = [FM_MENTAL[n] for n in mod.MENTAL]
    print("FM mental ordered", list(zip(mod.MENTAL, ordered)))
    needle = bytes(v * 5 for v in ordered)
    phys_b = bytes(FM_PHYS[n] * 5 for n in mod.PHYS)
    combo = needle + phys_b
    print("needle", list(needle))

    tmp = decompress(save)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                dab = mod.collect_doubles(mm, UID)[0]
                print("double", dab)

                # Whole-file scan for exact mental vector
                whole_hits: list[int] = []
                step = 8 << 20
                size = len(mm)
                needle_l = len(needle)
                pos = 0
                while pos < size:
                    chunk = bytes(mm[pos : min(size, pos + step + needle_l)])
                    start = 0
                    while True:
                        j = chunk.find(needle, start)
                        if j < 0:
                            break
                        whole_hits.append(pos + j - dab)
                        start = j + 1
                    pos += step
                print(
                    "whole-file mental hits rel-double:",
                    whole_hits[:40],
                    "n=",
                    len(whole_hits),
                )

                combo_hits: list[int] = []
                pos = 0
                while pos < size:
                    chunk = bytes(mm[pos : min(size, pos + step + len(combo))])
                    start = 0
                    while True:
                        j = chunk.find(combo, start)
                        if j < 0:
                            break
                        combo_hits.append(pos + j - dab)
                        start = j + 1
                    pos += step
                print(
                    "mental+phys combo hits rel-double:",
                    combo_hits[:40],
                    "n=",
                    len(combo_hits),
                )

                for rel in [h for h in whole_hits if abs(h) < 500_000][:30]:
                    abs_off = dab + rel
                    if abs_off + 69 > len(mm):
                        continue
                    rec = bytes(mm[abs_off : abs_off + 69])
                    print(
                        f"\n hit rel={rel} b34/35={rec[34], rec[35]} seal={rec[43]} "
                        f"u16={struct.unpack_from('<H', rec, 36)[0]} b23={rec[23]} "
                        f"attrish={mod.is_attrish(mm, abs_off)}"
                    )
                    disp = [round(x / 5) for x in rec[0:22]]
                    print(
                        "  m+p",
                        list(zip(list(mod.MENTAL) + list(mod.PHYS), disp)),
                    )
                    for delta in range(-40, 41):
                        a = abs_off + delta
                        if a < 0 or a + 69 > len(mm):
                            continue
                        if not mod.is_attrish(mm, a):
                            continue
                        d = mod.decode_attrs(bytes(mm[a : a + 69]))
                        m = d.get("mental") or {}
                        if m.get("determination") == 15:
                            print(
                                f"  attrish@delta={delta} Det={m.get('determination')} "
                                f"Lea={m.get('leadership')} Ant={m.get('anticipation')} "
                                f"Cmp={m.get('composure')} "
                                f"u16={struct.unpack_from('<H', mm, a + 36)[0]}"
                            )
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
