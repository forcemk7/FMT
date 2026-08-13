#!/usr/bin/env python3
"""Compare byte structure immediately AFTER double-UID for Contreras + Kizza."""

from __future__ import annotations

import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
OUT = ROOT / "tmp" / "fm-spike" / "ha-after-double.txt"

PLAYERS = {
    "Contreras": 2002220356,
    "Kizza": 2002185604,
}


def d5(b: int) -> int:
    return int(round(b / 5))


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-ha4-", suffix=".bin")
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


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = decompress(SAVE)
    lines = []
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for name, uid in PLAYERS.items():
                pat = struct.pack("<II", uid, uid)
                dab = mm.find(pat)
                lines.append(f"=== {name} uid={uid} doubleAbs={dab} ===")
                blob = bytes(mm[dab : dab + 256])
                for i in range(0, len(blob), 16):
                    chunk = blob[i : i + 16]
                    hx = " ".join(f"{b:02x}" for b in chunk)
                    dv = " ".join(f"{d5(b):2d}" for b in chunk)
                    rv = " ".join(f"{b:2d}" for b in chunk if True)
                    lines.append(f"+{i:03d}: {hx}")
                    lines.append(f"     d5 {dv}")
                    lines.append(f"     raw{[b for b in chunk]}")

                # Parse interleaved val,0x01 sequences after double+8
                lines.append("  interleaved low-bytes where next==0x01:")
                for start in range(8, 120):
                    seq = []
                    j = start
                    while j + 1 < len(blob) and blob[j + 1] == 0x01 and 1 <= blob[j] <= 20:
                        seq.append(blob[j])
                        j += 2
                        if len(seq) >= 12:
                            break
                    if len(seq) >= 6:
                        lines.append(f"    start=+{start} len={len(seq)} {seq}")
        finally:
            mm.close()
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
