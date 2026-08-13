#!/usr/bin/env python3
"""Sprint 12: dump Assan truth-pair site @159847656 and unify header variants."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "capa-sprint12-assan-header.txt"

BIN = sorted(
    Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)


def pick() -> Path:
    for p in BIN:
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no bin")


def main() -> int:
    path = pick()
    t0 = time.perf_counter()
    lines = [f"# CAPA sprint12 Assan header · {path.name}", ""]
    with path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            pair_at = 159847656
            dab = 159849949
            lines.append(f"pair_at={pair_at} dab={dab} gap={dab - pair_at}")
            lines.append(
                "ctx-80..+64: "
                + bytes(mm[pair_at - 80 : pair_at + 64]).hex(" ")
            )
            # compare to Kizza known good header
            kizza_pair = 246119505
            lines.append("")
            lines.append("Kizza reference pre32+pair+post16:")
            lines.append(
                bytes(mm[kizza_pair - 32 : kizza_pair + 20]).hex(" ")
            )
            lines.append("")
            lines.append("Assan pre32+pair+post16:")
            lines.append(
                bytes(mm[pair_at - 32 : pair_at + 20]).hex(" ")
            )
            lines.append("")
            lines.append("Bandeira pre32+pair+post16:")
            b_pair = 267673507
            lines.append(
                bytes(mm[b_pair - 32 : b_pair + 20]).hex(" ")
            )

            # Try alternate magics ending before Assan pair
            lines.append("")
            lines.append("## scan pre-64 for 40 30 / 40 20 motifs")
            pre = bytes(mm[pair_at - 64 : pair_at])
            for needle in (
                b"\x08\x02\x40\x30",
                b"\x09\x02\x40\x30",
                b"\x00\x02\x40\x30",
                b"\x08\x00\x40\x20",
                b"\x09\x00\x40\x20",
                b"\x02\x40\x30",
                b"\x40\x30\x04",
            ):
                idx = pre.rfind(needle)
                lines.append(f"  {needle.hex()} rfind={idx}")

            # Byte-diff Assan vs Kizza aligned on CA/PA pair
            lines.append("")
            lines.append("## aligned pre-40 byte diff Assan vs Kizza")
            a = bytes(mm[pair_at - 40 : pair_at + 8])
            k = bytes(mm[kizza_pair - 40 : kizza_pair + 8])
            for i, (ba, bk) in enumerate(zip(a, k)):
                rel = i - 40
                mark = " **" if ba != bk else ""
                lines.append(f"  rel={rel:+d}: A={ba:02x} K={bk:02x}{mark}")

            # Hypothesis: same layout but MAGIC prefix differs by 1 byte
            # Parse Assan as if magic starts wherever 40 30 04 00 00 00 appears
            lines.append("")
            lines.append("## try parse from each 40 30 04 00 00 00 before pair")
            pre2 = bytes(mm[pair_at - 64 : pair_at])
            start = 0
            while True:
                j = pre2.find(b"\x40\x30\x04\x00\x00\x00", start)
                if j < 0:
                    break
                abs_m = pair_at - 64 + j - 2  # include possible 08 02 before
                # try abs_m and abs_m+1 etc
                for off in range(abs_m - 2, abs_m + 3):
                    chunk = bytes(mm[off : off + 31])
                    lines.append(f"  @{off}: {chunk.hex(' ')}")
                    if len(chunk) >= 31:
                        rid = struct.unpack_from("<I", chunk, 8)[0]
                        p1 = struct.unpack_from("<I", chunk, 12)[0]
                        p2 = struct.unpack_from("<I", chunk, 16)[0]
                        tag = chunk[20]
                        vals = struct.unpack_from("<HHHHH", chunk, 21)
                        lines.append(
                            f"    id={rid} ptrs={p1},{p2} tag={tag} "
                            f"xyzca_pa={vals}"
                        )
                start = j + 1

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
