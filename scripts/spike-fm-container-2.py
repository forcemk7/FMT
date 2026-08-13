"""Spike #2: nested SI archive records inside decompressed FM26 .fm."""

from __future__ import annotations

import struct
from pathlib import Path

import zstandard as zstd

GAMES = (
    Path.home()
    / "Documents"
    / "Sports Interactive"
    / "Football Manager 26"
    / "games"
)
OUT_DIR = Path(__file__).resolve().parents[1] / "tmp" / "fm-spike"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def ascii_run(data: bytes, start: int, n: int = 80) -> str:
    chunk = data[start : start + n]
    return "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)


def dump_footer(path: Path, n: int = 64 * 1024) -> None:
    size = path.stat().st_size
    with path.open("rb") as f:
        f.seek(max(0, size - n))
        tail = f.read()
    (OUT_DIR / "footer.bin").write_bytes(tail)
    print("footer last 128 hex:", tail[-128:].hex(" "))
    text = tail.decode("latin-1", errors="ignore")
    for needle in ("FM26", "26.3", "24.3", "Schalke", "xml", "XML", "<"):
        print(f"footer find {needle!r}:", text.rfind(needle))


def parse_outer(path: Path) -> bytes:
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf."
        assert head[25] == 3, f"expected zstd marker 3, got {head[25]}"
        compressed = f.read()  # rest of file; may include footer after zstd

    # Strip a possible trailing region: u32@9 claimed payload-ish size
    claimed = struct.unpack_from("<I", head, 9)[0]
    file_size = path.stat().st_size
    print("claimed u32@9:", claimed, "file:", file_size, "delta:", file_size - claimed)

    # Decompress streaming until frame ends; record how many compressed bytes consumed
    dctx = zstd.ZstdDecompressor()
    reader = dctx.stream_reader(compressed)
    chunks: list[bytes] = []
    total = 0
    while True:
        block = reader.read(8 * 1024 * 1024)
        if not block:
            break
        chunks.append(block)
        total += len(block)
        print(f"  decompressed so far: {total:,} bytes")
        if total >= 64 * 1024 * 1024:
            print("  stopping early at 64MB for spike")
            break
    data = b"".join(chunks)
    (OUT_DIR / "outer-partial.bin").write_bytes(data[: min(len(data), 8 * 1024 * 1024)])
    print("wrote outer-partial.bin sample")
    return data


def scan_tags(data: bytes) -> None:
    # Look for 4-byte ASCII tags like 'tad.', 'fmf.', 'db.', ending with '.'
    tags: dict[bytes, list[int]] = {}
    for i in range(0, min(len(data) - 4, 8 * 1024 * 1024)):
        if data[i + 3] != ord("."):
            continue
        tag = data[i : i + 4]
        if not all(32 < b < 127 for b in tag[:3]):
            continue
        if not tag[:3].isalpha():
            continue
        tags.setdefault(tag, []).append(i)
    print("tag hits (first 8MB):")
    for tag, offs in sorted(tags.items(), key=lambda kv: -len(kv[1]))[:40]:
        print(f"  {tag!r}: count={len(offs)} first={offs[:5]}")


def inspect_first_records(data: bytes) -> None:
    print("first 256:", ascii_run(data, 0, 256))
    # Heuristic walk: many SI records look like:
    #   u16/u8 type?, tag[4], ...
    # Inner starts: 03 01 74 61 64 2e 2e 00 08 00 00 00 32 34 2e 33 2e 30 2b 30 00
    #               ^^ ^^ t  a  d  .  .  \0 then maybe length then "24.3.0+0\0"
    if data[2:6] == b"tad.":
        print("confirmed inner tad. at offset 2")
        # string after?
        nul = data.find(b"\x00", 12)
        print("maybe version cstr:", data[12:nul])


def extract_cstrings(data: bytes, limit: int = 200) -> None:
    strings: list[str] = []
    i = 0
    n = min(len(data), 2 * 1024 * 1024)
    while i < n and len(strings) < limit:
        if 32 <= data[i] < 127:
            j = i
            while j < n and 32 <= data[j] < 127:
                j += 1
            if j - i >= 6:
                strings.append(data[i:j].decode("ascii", errors="ignore"))
            i = j + 1
        else:
            i += 1
    print(f"sample printable strings ({len(strings)}):")
    for s in strings[:80]:
        print(" ", s)


def main() -> None:
    path = sorted(GAMES.glob("*.fm"), key=lambda p: p.stat().st_size, reverse=True)[0]
    print("file:", path.name)
    dump_footer(path)
    print("\n--- decompress outer ---")
    data = parse_outer(path)
    print("\n--- inspect ---")
    inspect_first_records(data)
    scan_tags(data)
    extract_cstrings(data)


if __name__ == "__main__":
    main()
