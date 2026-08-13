"""Hunt Unique IDs + identity strings in the local FM26 save (streaming zstd)."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike")
OUT.mkdir(parents=True, exist_ok=True)

PLAYERS_PATH = Path("data/fixtures/save-players.json")

PLAYERS = [
    {
        "kind": "REAL",
        "uid": 2000175080,
        "name": "Dennis Seimen",
        "club": "Schalke 04",
        "age": 33,
        "nation": "Germany",
        "nation2": "Romania",
        "pos": "GK",
        "det": 18,
        "lea": 16,
    },
    {
        "kind": "NEWGEN",
        "uid": 2002234366,
        "name": "Patrick Bandeira",
        "club": "Schalke 04",
        "age": 24,
        "nation": "Portugal",
        "nation2": None,
        "pos": "D (L)",
        "det": 16,
        "lea": 14,
    },
    {
        "kind": "NEWGEN",
        "uid": 2002266341,
        "name": "Robert Müller",
        "club": "Schalke 04",
        "age": 20,
        "nation": "Germany",
        "nation2": None,
        "pos": "AM (C)",
        "det": 16,
        "lea": 17,
    },
]


def encodings(uid: int) -> dict[str, bytes]:
    return {
        "u32le": struct.pack("<I", uid & 0xFFFFFFFF),
        "u32be": struct.pack(">I", uid & 0xFFFFFFFF),
        "u64le": struct.pack("<Q", uid),
        "u64be": struct.pack(">Q", uid),
    }


def dump_ctx(buf: bytes, off: int, radius: int = 128) -> str:
    s = max(0, off - radius)
    e = min(len(buf), off + radius)
    chunk = buf[s:e]
    hexline = chunk.hex(" ")
    ascii = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
    return f"@{off} (window {s}..{e})\n  hex: {hexline}\n  asc: {ascii}"


def stream_decompress(path: Path):
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf.", head[2:6]
        assert head[25] == 3, head[25]
        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError as e:
                    # Trailing non-zstd footer after the main frame.
                    print(f"  stop: {e}")
                    break
                if not block:
                    break
                yield block
        finally:
            reader.close()


def search_stream(patterns: dict[str, bytes], max_hits_per: int = 8):
    overlap = max(len(p) for p in patterns.values()) - 1
    carry = b""
    absolute = 0
    hits: dict[str, list[int]] = {k: [] for k in patterns}
    windows: dict[str, list[str]] = {k: [] for k in patterns}

    for block in stream_decompress(SAVE):
        data = carry + block
        for name, pat in patterns.items():
            if len(hits[name]) >= max_hits_per:
                continue
            start = 0
            while len(hits[name]) < max_hits_per:
                i = data.find(pat, start)
                if i < 0:
                    break
                # Skip matches that live only in the carry overlap region
                # except on first block — absolute accounts for carry.
                abs_off = absolute - len(carry) + i
                if abs_off < 0:
                    start = i + 1
                    continue
                # Deduplicate if already recorded (overlap re-scan)
                if hits[name] and hits[name][-1] == abs_off:
                    start = i + 1
                    continue
                windows[name].append(dump_ctx(data, i))
                hits[name].append(abs_off)
                start = i + 1
        absolute += len(block)
        if absolute % (64 * 1024 * 1024) < 8 * 1024 * 1024:
            print(f"  scanned ~{absolute:,}", flush=True)
        carry = data[-overlap:] if overlap > 0 else b""

    return hits, windows, absolute


def main() -> None:
    PLAYERS_PATH.write_text(
        json.dumps(PLAYERS, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("wrote fixture", PLAYERS_PATH)
    print("save:", SAVE, "size", SAVE.stat().st_size)

    patterns: dict[str, bytes] = {}
    for p in PLAYERS:
        for enc, b in encodings(p["uid"]).items():
            patterns[f"{p['name']}|uid|{enc}"] = b
        patterns[f"{p['name']}|name"] = p["name"].encode("utf-8")
        # length-prefixed UTF-8 (u32le + bytes) — SI string form seen earlier
        name_b = p["name"].encode("utf-8")
        patterns[f"{p['name']}|lp32"] = struct.pack("<I", len(name_b)) + name_b

    print("patterns:", len(patterns))
    hits, windows, total = search_stream(patterns, max_hits_per=6)
    print(f"\nDone. Total decompressed: {total:,}")

    lines: list[str] = []
    for key in sorted(hits):
        n = len(hits[key])
        lines.append(f"\n### {key}  hits={n}  offsets={hits[key]}")
        for win in windows[key]:
            lines.append(win)

    text = "\n".join(lines) if any(hits.values()) else "(no hits)"
    (OUT / "uid-hunt.txt").write_text(text, encoding="utf-8")
    print(text[:12000])
    print("\n... wrote", OUT / "uid-hunt.txt")

    print("\n=== SUMMARY ===")
    for p in PLAYERS:
        print(f"\n{p['name']}  uid={p['uid']}  det={p['det']} lea={p['lea']}")
        for enc in ("u32le", "u32be", "u64le", "u64be"):
            k = f"{p['name']}|uid|{enc}"
            print(f"  {enc}: {hits.get(k, [])}")
        print(f"  name: {hits.get(p['name'] + '|name', [])}")
        print(f"  lp32: {hits.get(p['name'] + '|lp32', [])}")


if __name__ == "__main__":
    main()
