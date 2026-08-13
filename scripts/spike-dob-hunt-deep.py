#!/usr/bin/env python3
"""Deeper DOB hunt: year±month/day clusters + personIndex sheet."""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "dob-hunt-players.json").read_text(encoding="utf-8")
)
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
OUT = ROOT / "tmp" / "fm-spike" / "dob-hunt-deep.txt"
PERSON_HEAD = 512 * 1024 * 1024
RADIUS = 8192


def collect_doubles(buf: mmap.mmap, uid: int, limit: int = 12) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(buf), PERSON_HEAD)
    j = buf.find(pat, 0, end)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = buf.find(pat, j + 1, end)
    return hits


def score_person_double(buf: mmap.mmap, dab: int) -> int:
    blob = bytes(buf[dab : dab + 128])
    score = 0
    if b"\x01\x01\x01" in blob[8:80]:
        score += 5
    if len(blob) > 8 and blob[8] in (1, 2):
        score += 1
    if bytes.fromhex("01006c07") in blob:
        score += 3
    return score


def best_double(buf: mmap.mmap, doubles: list[int]) -> int | None:
    if not doubles:
        return None
    return sorted(doubles, key=lambda d: (-score_person_double(buf, d), d))[0]


def person_index(buf: mmap.mmap, dab: int) -> int | None:
    if dab + 35 > len(buf):
        return None
    # layout variants: +31 for good person doubles; verify plausible range
    for off in (31, 32, 28, 24):
        val = struct.unpack_from("<I", buf, dab + off)[0]
        if 1 <= val <= 50_000:
            return val
    return None


def find_ymd_clusters(win: bytes, rel0: int, y: int, m: int, d: int) -> list[tuple[str, int]]:
    """Find encodings where year/month/day co-locate within a short span."""
    year = struct.pack("<H", y)
    hits: list[tuple[str, int]] = []
    start = 0
    while True:
        i = win.find(year, start)
        if i < 0:
            break
        # look ±8 bytes for month and day as u8
        lo = max(0, i - 8)
        hi = min(len(win), i + 2 + 8)
        ctx = win[lo:hi]
        year_in_ctx = i - lo
        has_m = m in ctx
        has_d = d in ctx
        if has_m and has_d:
            # classify layouts
            # ymd: year then m then d nearby
            after = win[i + 2 : i + 8]
            before = win[max(0, i - 6) : i]
            kind = "year_near_md"
            if len(after) >= 2 and after[0] == m and after[1] == d:
                kind = "ymd_u16_u8_u8"
            elif len(after) >= 2 and after[0] == d and after[1] == m:
                kind = "ydm_u16_u8_u8"
            elif len(before) >= 2 and before[-2] == d and before[-1] == m:
                kind = "dmy_u8_u8_u16"
            elif len(before) >= 2 and before[-2] == m and before[-1] == d:
                kind = "mdy_u8_u8_u16"
            hits.append((kind, i - rel0))
        start = i + 1
    return hits


def main() -> None:
    lines: list[str] = [f"players={len(PLAYERS)}", ""]
    cluster_counts: Counter[str] = Counter()
    cluster_offsets: dict[str, list[int]] = defaultdict(list)
    indexes: list[tuple[str, int, int]] = []  # name, uid, personIndex

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                uid = int(p["uid"])
                y, m, d = map(int, p["dob"].split("-"))
                dab = best_double(mm, collect_doubles(mm, uid))
                if dab is None:
                    lines.append(f"## {p['name']}: no double")
                    continue
                pi = person_index(mm, dab)
                if pi is not None:
                    indexes.append((p["name"], uid, pi))
                lo = max(0, dab - RADIUS)
                hi = min(len(mm), dab + RADIUS)
                win = bytes(mm[lo:hi])
                rel0 = dab - lo
                clusters = find_ymd_clusters(win, rel0, y, m, d)
                lines.append(
                    f"## {p['name']} dob={p['dob']} best={dab} personIndex={pi}"
                )
                if not clusters:
                    lines.append("  no year+month+day cluster in ±8KB")
                else:
                    for kind, off in clusters[:12]:
                        lines.append(f"  {kind} @{off}")
                        cluster_counts[kind] += 1
                        cluster_offsets[kind].append(off)

            lines.append("\n## cluster kind counts")
            for k, n in cluster_counts.most_common():
                offs = cluster_offsets[k]
                maj = Counter(offs).most_common(8)
                lines.append(f"  {k}: players≈{n} top_offsets={maj}")

            lines.append("\n## personIndex list")
            for name, uid, pi in indexes:
                lines.append(f"  {pi:5d}  {uid}  {name}")

            # If personIndexes are dense, try stride alignment for DOB days_y1900
            if len(indexes) >= 8:
                lines.append("\n## personIndex stride probe (days_y1900 at base+stride*pi)")
                # Build map pi -> dob days
                pi_days = {}
                for p in PLAYERS:
                    dab = best_double(mm, collect_doubles(mm, int(p["uid"])))
                    if dab is None:
                        continue
                    pi = person_index(mm, dab)
                    if pi is None:
                        continue
                    y, m, d = map(int, p["dob"].split("-"))
                    days = (date(y, m, d) - date(1900, 1, 1)).days
                    pi_days[pi] = (days, p["name"])

                # Guess stride by pairing two indexes
                sample = sorted(pi_days.items())[:12]
                lines.append(f"  sample indexes: {[(pi, n) for pi, (_, n) in sample]}")

                # Search for abs offsets of days for first player, then test stride for others
                first_pi, (first_days, first_name) = sample[0]
                pat = struct.pack("<I", first_days)
                candidates = []
                j = 0
                while len(candidates) < 40:
                    j = mm.find(pat, j, min(len(mm), PERSON_HEAD))
                    if j < 0:
                        break
                    candidates.append(j)
                    j += 1
                lines.append(f"  {first_name} days_y1900 abs hits (first 40): {candidates[:20]}")

                # For each candidate abs, assume table_base = abs - stride*pi, try strides
                scored = []
                for abs0 in candidates[:30]:
                    for stride in (4, 8, 12, 16, 20, 24, 32, 36, 40, 48, 64, 72, 76, 77, 80, 96, 128):
                        base = abs0 - stride * first_pi
                        if base < 0:
                            continue
                        ok = 0
                        for pi, (days, _name) in pi_days.items():
                            pos = base + stride * pi
                            if pos < 0 or pos + 4 > len(mm):
                                continue
                            if struct.unpack_from("<I", mm, pos)[0] == days:
                                ok += 1
                        if ok >= max(5, len(pi_days) // 2):
                            scored.append((ok, stride, base, abs0))
                scored.sort(reverse=True)
                lines.append(f"  top stride hits: {scored[:15]}")
        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT, "lines", len(lines))


if __name__ == "__main__":
    main()
