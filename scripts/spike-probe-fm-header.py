#!/usr/bin/env python3
"""
Probe .fm save *container* only — no squad/player content.

Prints one JSON object to stdout. Safe to run on any career save during testing;
does not emit club/player names.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import zstandard as zstd

ZSTD_MAGIC = bytes.fromhex("28b52ffd")


def probe(path: Path) -> dict:
    size = path.stat().st_size
    with path.open("rb") as f:
        head = f.read(256)
    magic4 = head[:4]
    magic_ascii = "".join(chr(b) if 32 <= b < 127 else "." for b in magic4)
    # FM24 career we reverse-engineered: 26-byte header, byte[25]==3 → zstd, then stream.
    comp_byte_25 = head[25] if len(head) > 25 else None
    zstd_offsets = []
    start = 0
    while True:
        j = head.find(ZSTD_MAGIC, start)
        if j < 0:
            break
        zstd_offsets.append(j)
        start = j + 1

    trials = []
    for off in sorted({26, 0, 16, 20, 24, 28, 32, *zstd_offsets}):
        if off >= len(head):
            continue
        try:
            with path.open("rb") as f:
                f.seek(off)
                reader = zstd.ZstdDecompressor().stream_reader(f)
                try:
                    chunk = reader.read(64 * 1024)
                finally:
                    reader.close()
            trials.append(
                {
                    "offset": off,
                    "ok": True,
                    "firstOutBytes": len(chunk or b""),
                    "outMagic": (chunk[:4].hex() if chunk else None),
                }
            )
        except Exception as e:  # noqa: BLE001 — diagnostic
            trials.append(
                {
                    "offset": off,
                    "ok": False,
                    "error": type(e).__name__,
                }
            )

    zlib_ok = False
    try:
        import zlib

        for off in (0, 16, 26, 32):
            if off >= len(head):
                continue
            try:
                zlib.decompress(head[off : off + 64], wbits=15)
                zlib_ok = True
                break
            except zlib.error:
                try:
                    zlib.decompress(head[off : off + 64], wbits=-15)
                    zlib_ok = True
                    break
                except zlib.error:
                    pass
    except Exception:
        pass

    best = next((t for t in trials if t.get("ok")), None)
    layout = "unknown"
    if magic4 == b"fmf." and comp_byte_25 == 3 and any(
        t.get("offset") == 26 and t.get("ok") for t in trials
    ):
        layout = "fm24_continue_style_zstd_at_26"
    elif best and best.get("ok"):
        layout = f"zstd_at_{best['offset']}"
    elif zlib_ok:
        layout = "zlib_candidate"

    return {
        "saveBytes": size,
        "saveName": path.name,
        "magicAscii": magic_ascii,
        "magicHex": magic4.hex(),
        "headerHex32": head[:32].hex(),
        "byte25": comp_byte_25,
        "zstdMagicOffsetsInHead": zstd_offsets,
        "zstdTrials": trials,
        "zlibHeadCandidate": zlib_ok,
        "inferredLayout": layout,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: spike-probe-fm-header.py <save.fm>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(json.dumps({"error": f"not found: {path}"}))
        return 1
    print(json.dumps(probe(path), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
