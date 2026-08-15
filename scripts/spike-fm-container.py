"""Spike: outer container layout of FM26 .fm saves (fmf + compression)."""

from __future__ import annotations

import struct
from pathlib import Path

import zstandard as zstd

GAMES = Path(__file__).resolve().parents[1] / "data" / "saves"


def main() -> None:
    save = sorted(GAMES.glob("*.fm"), key=lambda p: p.stat().st_size, reverse=True)[0]
    size = save.stat().st_size
    print("file:", save.name)
    print("size:", size)

    with save.open("rb") as f:
        head = f.read(64)
    print("head64:", head.hex(" "))
    assert head[2:6] == b"fmf.", head[2:6]

    def u32(off: int) -> int:
        return struct.unpack_from("<I", head, off)[0]

    print("bytes0-1:", head[0:2].hex())
    print("magic:", head[2:6])
    print("b6-8:", head[6:9].hex())
    print("u32@9:", u32(9), "file-size delta:", size - u32(9))
    print("u32@13:", u32(13))
    print("u32@17:", u32(17))
    print("u32@21:", u32(21))
    print("byte25:", head[25], hex(head[25]))
    print("from26:", head[26:30].hex(), "zstd?", head[26:30] == bytes.fromhex("28b52ffd"))

    with save.open("rb") as f:
        f.seek(26)
        compressed = f.read(16 * 1024 * 1024)

    try:
        frame = zstd.get_frame_parameters(compressed)
        print(
            "zstd frame content_size:",
            frame.content_size,
            "dict_id:",
            frame.dict_id,
            "window:",
            getattr(frame, "window_size", None),
        )
    except Exception as e:
        print("frame params err:", type(e).__name__, e)

    dctx = zstd.ZstdDecompressor()
    out = dctx.stream_reader(compressed).read(4 * 1024 * 1024)
    print("streamed first output bytes:", len(out))
    print("out head hex:", out[:80].hex(" "))
    ascii = "".join(chr(b) if 32 <= b < 127 else "." for b in out[:300])
    print("out ascii:", ascii)

    text = out.decode("latin-1", errors="ignore")
    for n in (
        "FM26",
        "26.3",
        "26.2",
        "26.3.1",
        "Schalke",
        "player",
        "Player",
        "Determination",
        "hidden",
        "fmf",
    ):
        print(f"find {n!r}:", text.find(n))

    # Compare first zstd magic offsets across a few saves
    print("\n--- header compare ---")
    for path in sorted(GAMES.glob("*.fm"), key=lambda p: p.stat().st_mtime, reverse=True)[:4]:
        with path.open("rb") as f:
            h = f.read(32)
        print(
            path.name[:50],
            "size",
            path.stat().st_size,
            "u32@9",
            struct.unpack_from("<I", h, 9)[0],
            "b25",
            h[25],
            "zstd@",
            26 if h[26:30] == b"\x28\xb5\x2f\xfd" else "NO",
            "head",
            h[:26].hex(" "),
        )


if __name__ == "__main__":
    main()
