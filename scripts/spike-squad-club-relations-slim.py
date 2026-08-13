"""Slim club-object relation parse — no bulk name resolve."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-club-relations-slim.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
CLUB = 1986866253
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000


def extract(abs_target: int, length: int, before: int = 0) -> bytes:
    start = abs_target - before
    end = abs_target + length
    abs_base = 0
    carry = b""
    buf = bytearray()
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                chunk_start = abs_base - len(carry)
                if chunk_start < end and abs_base + len(block) > start:
                    already = len(buf)
                    want = start + already
                    lo = max(0, start - chunk_start, want - chunk_start)
                    hi = min(len(data), end - chunk_start)
                    if lo < hi:
                        buf.extend(data[lo:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= before + length:
                    break
        finally:
            reader.close()
    return bytes(buf)


def main() -> None:
    lines: list[str] = []
    win = extract(CLUB, 20000, before=256)
    base = CLUB - 256
    j = win.find(b"FC Schalke 04")
    lines.append(f"FC Schalke 04 @{base+j}")

    after = win[j:]
    after_base = base + j

    # typed 03 4f XX 03 YY 02 u32
    rels = []
    i = 0
    while i + 12 <= len(after):
        if after[i] == 0x03 and after[i + 1] == 0x4F:
            code = after[i + 2]
            if after[i + 3] == 0x03 and after[i + 5] == 0x02:
                val = struct.unpack_from("<I", after, i + 6)[0]
                rels.append((after_base + i, code, after[i + 4], val))
                i += 9
                continue
        i += 1

    lines.append(f"03 4f relations in +20KB: {len(rels)}")
    by: dict[int, list] = {}
    for a, code, sub, val in rels:
        by.setdefault(code, []).append((a, sub, val))

    for code, items in sorted(by.items()):
        ch = chr(code) if 32 <= code < 127 else "?"
        uid_items = [(a, s, v) for a, s, v in items if UID_LO <= v <= UID_HI]
        lines.append(
            f"  0x{code:02X}('{ch}') total={len(items)} uid_vals={len(uid_items)}"
        )
        for a, s, v in uid_items[:30]:
            mark = f" <<{NAME_BY[v]}" if v in NAME_BY else ""
            lines.append(f"    @{a} sub={s} uid={v}{mark}")

    # Also 03 00 XX pattern
    rels2 = []
    i = 0
    while i + 12 <= len(after):
        if after[i] == 0x03 and after[i + 1] == 0x00:
            code = after[i + 2]
            if after[i + 3] == 0x03 and after[i + 5] == 0x02:
                val = struct.unpack_from("<I", after, i + 6)[0]
                rels2.append((after_base + i, code, after[i + 4], val))
                i += 9
                continue
        i += 1
    lines.append(f"\n03 00 relations: {len(rels2)}")
    by2: dict[int, list] = {}
    for a, code, sub, val in rels2:
        by2.setdefault(code, []).append((a, sub, val))
    for code, items in sorted(by2.items()):
        uid_items = [(a, s, v) for a, s, v in items if UID_LO <= v <= UID_HI]
        lines.append(
            f"  0x{code:02X} total={len(items)} uid_vals={len(uid_items)}"
        )
        for a, s, v in uid_items[:20]:
            mark = f" <<{NAME_BY[v]}" if v in NAME_BY else ""
            lines.append(f"    @{a} sub={s} uid={v}{mark}")

    # Fixture positions relative to club
    lines.append("\nfixture UID offsets vs club:")
    for n, u in UIDS.items():
        pat = struct.pack("<I", u)
        start = 0
        found = []
        while len(found) < 8:
            p = win.find(pat, start)
            if p < 0:
                break
            found.append(base + p)
            start = p + 1
        lines.append(f"  {n}: {found}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
