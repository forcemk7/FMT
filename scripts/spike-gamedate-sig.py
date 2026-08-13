#!/usr/bin/env python3
"""Tighten gameDate signature using prelude markers around known 2039-07-01 hit."""

from __future__ import annotations

import mmap
import struct
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

DECOMP = Path("tmp/fm-spike/dob-lock-decomp.bin")
EPOCH = date(1900, 1, 1)
GAME = date(2039, 7, 1)
GAME_DAYS = (GAME - EPOCH).days  # 50950 = 0xC706


def main() -> None:
    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            pat = struct.pack("<I", GAME_DAYS)
            hits = []
            j = mm.find(pat, 0, 16 * 1024 * 1024)
            while j >= 0 and len(hits) < 30:
                hits.append(j)
                j = mm.find(pat, j + 1, 16 * 1024 * 1024)
            print(f"early hits for {GAME.isoformat()} days={GAME_DAYS}: {len(hits)}")
            for h in hits:
                pre = bytes(mm[max(0, h - 16) : h])
                post = bytes(mm[h : h + 16])
                print(f"  @{h}\n    pre ={pre.hex(' ')}\n    post={post.hex(' ')}")

            # Test signatures: pre.endswith(sig) then days
            sigs = {
                "c7080000": bytes.fromhex("c7080000"),
                "ffff_c7080000": bytes.fromhex("ffffffffc7080000"),
                "00_c7080000": bytes.fromhex("00c7080000"),
                "0600_then?": None,
            }
            print("\n## signature exclusivity (how many career dates match each sig in 8MB)")
            early = min(len(mm), 8 * 1024 * 1024)
            for name, sig in sigs.items():
                if sig is None:
                    continue
                dates: Counter[str] = Counter()
                start = 0
                while True:
                    j = mm.find(sig, start, early)
                    if j < 0:
                        break
                    off = j + len(sig)
                    if off + 4 > early:
                        break
                    days = struct.unpack_from("<I", mm, off)[0]
                    if 45_000 <= days <= 56_000:
                        try:
                            dt = EPOCH + timedelta(days=days)
                            if 2024 <= dt.year <= 2045:
                                # require twin after?
                                if off + 12 <= early:
                                    a = struct.unpack_from("<I", mm, off + 4)[0]
                                    b = struct.unpack_from("<I", mm, off + 8)[0]
                                    if a == b and a > 255:
                                        dates[dt.isoformat()] += 1
                        except Exception:
                            pass
                    start = j + 1
                print(f"  {name}: unique_dates={len(dates)} top={dates.most_common(8)}")
                print(f"    has_GAME={dates.get(GAME.isoformat(), 0)}")

            # Also: consecutive day pair (d-1, d) both as u32
            print("\n## consecutive day pair (prev=days-1) + twin in 8MB")
            dates2: Counter[str] = Counter()
            for off in range(4, early - 12):
                prev = struct.unpack_from("<I", mm, off - 4)[0]
                days = struct.unpack_from("<I", mm, off)[0]
                if days - prev != 1:
                    continue
                if not (45_000 <= days <= 56_000):
                    continue
                try:
                    dt = EPOCH + timedelta(days=days)
                except Exception:
                    continue
                if not (2024 <= dt.year <= 2045):
                    continue
                a = struct.unpack_from("<I", mm, off + 4)[0]
                b = struct.unpack_from("<I", mm, off + 8)[0]
                twin = a == b and a > 255
                if twin:
                    dates2[dt.isoformat()] += 1
            print(f"  unique={len(dates2)} top={dates2.most_common(10)}")
            print(f"  has_GAME={dates2.get(GAME.isoformat(), 0)}")

            # 6c07 + days for GAME
            print("\n## mark+gameDays")
            needle = bytes.fromhex("01006c07") + pat
            j = mm.find(needle)
            n = 0
            while j >= 0 and n < 10:
                print(f"  @{j} ctx={bytes(mm[j:j+24]).hex(' ')}")
                n += 1
                j = mm.find(needle, j + 1)
            print(f"  total_shown={n}")
        finally:
            mm.close()


if __name__ == "__main__":
    main()
