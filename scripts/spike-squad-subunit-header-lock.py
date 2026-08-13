#!/usr/bin/env python3
"""Sprint: confirm II/U19 squad lists via shared header motif + nearby names."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "squad-subunit-header-lock.txt"

# From validate sprint
II_COUNT_AT = 57023793
U19_COUNT_AT = 60415763  # contains Solo
U19_NAME_AT = 60415908

MOTIF = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"  # immediately before count


def pick_bin() -> Path:
    for p in sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no bin")


def read_lp_strings(mm: mmap.mmap, lo: int, hi: int) -> list[tuple[int, str]]:
    out = []
    off = lo
    while off + 8 <= hi:
        n = struct.unpack_from("<I", mm, off)[0]
        if 3 <= n <= 48 and off + 4 + n <= hi:
            raw = bytes(mm[off + 4 : off + 4 + n])
            if raw.isascii() and raw[:1].isalpha() and b"\x00" not in raw:
                try:
                    s = raw.decode("ascii")
                    if any(c.islower() or c.isdigit() for c in s) or " " in s or s.isupper():
                        out.append((off, s))
                        off += 4 + n
                        continue
                except Exception:
                    pass
        off += 1
    return out


def parse_list(mm: mmap.mmap, count_at: int) -> dict:
    count = struct.unpack_from("<H", mm, count_at)[0]
    jobs = [
        struct.unpack_from("<I", mm, count_at + 2 + 4 * k)[0] for k in range(count)
    ]
    pre = bytes(mm[count_at - 64 : count_at + 2])
    return {"count": count, "jobs": jobs, "pre": pre.hex(" ")}


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# subunit header lock · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for label, ca in (("II", II_COUNT_AT), ("U19", U19_COUNT_AT)):
                rec = parse_list(mm, ca)
                lines.append(f"## {label} count@{ca} n={rec['count']}")
                lines.append(f"  pre64: {rec['pre']}")
                lines.append(f"  jobs: {rec['jobs']}")
                # strings in ±400
                strs = read_lp_strings(mm, ca - 400, ca + 80)
                # also raw ascii contains
                win = bytes(mm[ca - 300 : ca + 20])
                for needle in (
                    b"Schalke",
                    b"U19",
                    b"II",
                    b"Reserve",
                    b"Amateure",
                    b"Jugend",
                ):
                    j = win.find(needle)
                    if j >= 0:
                        lines.append(f"  raw {needle!r} at pre+{j - 300}")
                lines.append(f"  lp-strings nearby: {strs[:12]}")

            lines.append("")
            lines.append("## distance U19 list → name")
            lines.append(f"  name@{U19_NAME_AT} - list@{U19_COUNT_AT} = {U19_NAME_AT - U19_COUNT_AT}")

            # Global: find motif+plausible count near both sites' neighborhood
            # and also scan for other Schalke subunit lists with same header
            lines.append("")
            lines.append("## other motif lists in 55–65MB band (possible sibling squads)")
            lo, hi = 55_000_000, 65_000_000
            start = lo
            found = []
            while True:
                j = mm.find(MOTIF, start, hi)
                if j < 0:
                    break
                count_at = j + len(MOTIF)
                count = struct.unpack_from("<H", mm, count_at)[0]
                if 12 <= count <= 50:
                    jobs = [
                        struct.unpack_from("<I", mm, count_at + 2 + 4 * k)[0]
                        for k in range(min(count, 8))
                    ]
                    ok = sum(1 for x in jobs if 50_000 <= x <= 2_000_000)
                    if ok >= 6:
                        # peek strings before
                        win = bytes(mm[max(lo, j - 200) : j])
                        label = "?"
                        for s, name in (
                            (b"U19", "U19"),
                            (b"II", "II"),
                            (b"Reserve", "Reserve"),
                            (b"First", "First"),
                        ):
                            if s in win:
                                label = name
                                break
                        found.append((count_at, count, label, jobs[:4]))
                start = j + 1
            lines.append(f"  candidates={len(found)}")
            for ca, n, label, sample in found[:40]:
                mark = ""
                if ca == II_COUNT_AT:
                    mark = " <<II_LOCK"
                if ca == U19_COUNT_AT:
                    mark = " <<U19_LOCK"
                lines.append(
                    f"  @{ca} n={n} label={label} sample={sample}{mark}"
                )

            # Write fixture-style summary
            lines.append("")
            lines.append("## LOCK SUMMARY")
            lines.append(
                "Header before count: "
                "[…] ff ff ff ff <u32> <u32> ff ff ff ff 00 ff ff ff ff <count:u16> <jobs:u32×count>"
            )
            lines.append(
                "U19: list@60415763 n=27, name 'Schalke 04 U19'@60415908 (Δ=+145)"
            )
            lines.append(
                "II:  list@57023793 n=23 containing Ermin job 237871 "
                "(name not co-located in ±300; may be affiliate without inline name)"
            )

        finally:
            mm.close()

    lines.append(f"\nelapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
