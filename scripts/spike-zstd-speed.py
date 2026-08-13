#!/usr/bin/env python3
"""Time full zstd decompress throughput (no scanning)."""

from __future__ import annotations

import time
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
CHUNK = 8 * 1024 * 1024


def main() -> None:
    print(f"save={SAVE.name} compressed={SAVE.stat().st_size/1e6:.0f}MB", flush=True)
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        t0 = time.perf_counter()
        out = 0
        next_mark = 256 * 1024 * 1024
        try:
            while True:
                try:
                    block = reader.read(CHUNK)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                out += len(block)
                if out >= next_mark:
                    dt = time.perf_counter() - t0
                    print(
                        f"  {out/1e6:.0f}MB out in {dt:.2f}s ({out/dt/1e6:.0f} MB/s)",
                        flush=True,
                    )
                    next_mark += 256 * 1024 * 1024
        finally:
            reader.close()
        dt = time.perf_counter() - t0
        print(f"DONE {out/1e6:.0f}MB in {dt:.2f}s ({out/dt/1e6:.0f} MB/s)", flush=True)


if __name__ == "__main__":
    main()
