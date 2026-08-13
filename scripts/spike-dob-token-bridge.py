#!/usr/bin/env python3
from __future__ import annotations

import json
import mmap
import struct
from datetime import date
from pathlib import Path

PLAYERS = json.loads(
    Path("tmp/fm-spike/age-hunt-players.json").read_text(encoding="utf-8")
)
DECOMP = Path("tmp/fm-spike/dob-lock-decomp.bin")
MARK = bytes.fromhex("01006c07")
EPOCH = date(1900, 1, 1)


def best_double(mm: mmap.mmap, uid: int) -> int | None:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(mm), 512 * 1024 * 1024)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 12:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    if not hits:
        return None

    def score(dab: int) -> int:
        blob = bytes(mm[dab : dab + 160])
        s = 0
        if b"\x01\x01\x01" in blob[8:120]:
            s += 5
        if MARK in blob:
            s += 3
        if len(blob) >= 35:
            pi = struct.unpack_from("<I", blob, 31)[0]
            if 0 < pi < 200_000:
                s += 4
        return s

    return sorted(hits, key=lambda d: (-score(d), d))[0]


def main() -> None:
    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            ok = 0
            for p in PLAYERS:
                dob = date(*map(int, p["dob"].split("-")))
                days = (dob - EPOCH).days
                uid = int(p["uid"])
                dab = best_double(mm, uid)
                site = mm.find(MARK + struct.pack("<I", days))
                if site < 0 or dab is None:
                    print(p["name"], "skip")
                    continue
                rec = bytes(mm[site : site + 48])
                days_le = struct.pack("<I", days)
                drel = rec.find(days_le)
                after = rec[drel + 4 :]
                u32s = [
                    struct.unpack_from("<I", after, i)[0]
                    for i in range(0, min(24, len(after) - 3), 4)
                ]
                found: list[str] = []
                win = bytes(mm[max(0, dab - 8192) : dab + 8192])
                for v in u32s:
                    if v in (0, 0xFFFFFFFF, days) or v < 10:
                        continue
                    if struct.pack("<I", v) in win:
                        found.append(hex(v))
                # Also try looking back 32 bytes before DOB mark for link ids
                before = bytes(mm[max(0, site - 32) : site])
                before_u32s = [
                    struct.unpack_from("<I", before, i)[0]
                    for i in range(0, len(before) - 3, 4)
                ]
                found_b: list[str] = []
                for v in before_u32s:
                    if v in (0, 0xFFFFFFFF) or v < 10:
                        continue
                    if struct.pack("<I", v) in win:
                        found_b.append(hex(v))
                if found or found_b:
                    ok += 1
                print(
                    f"{p['name']}: after={[hex(x) for x in u32s[:6]]} "
                    f"near_after={found} near_before={found_b}"
                )
            print(f"linked_any={ok}/{len(PLAYERS)}")
        finally:
            mm.close()


if __name__ == "__main__":
    main()
