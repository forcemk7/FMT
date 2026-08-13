"""Extract co-located Unique-ID + name person records; score Det/Lead candidates."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike")
OUT.mkdir(parents=True, exist_ok=True)
FIXTURE = Path("data/fixtures/save-players.json")

PLAYERS = (
    json.loads(FIXTURE.read_text(encoding="utf-8-sig")) if FIXTURE.exists() else []
)


def stream_blocks(path: Path):
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf." and head[25] == 3
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                yield block
        finally:
            reader.close()


def find_person_records(uid: int, name: str, want: int = 4):
    """Find lp32(name) occurrences preceded within 160 bytes by uid u32le."""
    name_b = name.encode("utf-8")
    needle = struct.pack("<I", len(name_b)) + name_b
    uid_b = struct.pack("<I", uid & 0xFFFFFFFF)
    overlap = 512
    carry = b""
    abs_base = 0
    found: list[tuple[int, bytes]] = []

    for block in stream_blocks(SAVE):
        data = carry + block
        start = 0
        while len(found) < want:
            i = data.find(needle, start)
            if i < 0:
                break
            abs_off = abs_base - len(carry) + i
            # look behind for uid
            behind = data[max(0, i - 160) : i]
            if uid_b in behind:
                # export a wide window: 96 before name ... 256 after
                ws = max(0, i - 96)
                we = min(len(data), i + len(needle) + 256)
                found.append((abs_off, data[ws:we]))
            start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]
        if len(found) >= want:
            break
    return found


def score_attrs(window: bytes, det: int, lea: int) -> dict:
    """Look for det/lea as nearby u8 pairs / single bytes after the name."""
    # After full-name string, scan for (det, lea) as consecutive u8 or with gap≤4
    hits = []
    for i in range(len(window) - 1):
        if window[i] == det and window[i + 1] == lea:
            hits.append(("u8pair+0", i))
        if i + 2 < len(window) and window[i] == det and window[i + 2] == lea:
            hits.append(("u8pair+1", i))
        if i + 3 < len(window) and window[i] == det and window[i + 3] == lea:
            hits.append(("u8pair+2", i))
        if i + 4 < len(window) and window[i] == det and window[i + 4] == lea:
            hits.append(("u8pair+3", i))
    # also u32le of each
    det32 = struct.pack("<I", det)
    lea32 = struct.pack("<I", lea)
    return {
        "u8_pairs": hits[:20],
        "det_u32le_at": [i for i in range(len(window) - 3) if window[i : i + 4] == det32][:10],
        "lea_u32le_at": [i for i in range(len(window) - 3) if window[i : i + 4] == lea32][:10],
        "det_u8_count": window.count(bytes([det])),
        "lea_u8_count": window.count(bytes([lea])),
    }


def fmt_window(blob: bytes) -> str:
    return (
        blob.hex(" ")
        + "\n"
        + "".join(chr(b) if 32 <= b < 127 else "." for b in blob)
    )


def main() -> None:
    if not PLAYERS:
        raise SystemExit(f"missing fixture {FIXTURE}")

    report: list[str] = []
    for p in PLAYERS:
        report.append(
            f"\n======== {p['name']} uid={p['uid']} det={p['det']} lea={p['lea']} ========"
        )
        recs = find_person_records(p["uid"], p["name"], want=3)
        report.append(f"co-located records: {len(recs)}")
        for idx, (off, win) in enumerate(recs):
            report.append(f"\n--- record[{idx}] name@abs={off} window_len={len(win)} ---")
            report.append(fmt_window(win))
            scored = score_attrs(win, p["det"], p["lea"])
            report.append(f"attr scores: {json.dumps(scored)}")
            # highlight relative offset of uid and name inside window
            uid_b = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
            name_b = p["name"].encode("utf-8")
            report.append(
                f"uid_rel={win.find(uid_b)} name_rel={win.find(struct.pack('<I', len(name_b)) + name_b)}"
            )

    text = "\n".join(report)
    (OUT / "person-records.txt").write_text(text, encoding="utf-8")
    print(text)
    print("\nwrote", OUT / "person-records.txt")


if __name__ == "__main__":
    main()
