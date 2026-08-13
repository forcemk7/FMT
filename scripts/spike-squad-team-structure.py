"""Hunt team subunits under Schalke club + global 'First Team' strings."""

from __future__ import annotations

import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-team-structure.txt")

NEEDLES_LATIN = [
    b"First Team",
    b"Reserves",
    b"Reserve",
    b"U19",
    b"U18",
    b"U21",
    b"Youth Team",
    b"B-Team",
    b"II",
    b"Amateure",
    b"Senior",
    b"FC Schalke 04",
    b"Schalke 04",
]
NEEDLES_U16 = [s.decode() for s in NEEDLES_LATIN]


def main() -> None:
    lines: list[str] = []
    hits: list[tuple[int, str, bytes]] = []

    abs_base = 0
    carry = b""
    print("scanning strings…", flush=True)
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

                for needle in NEEDLES_LATIN:
                    start = 0
                    while True:
                        j = data.find(needle, start)
                        if j < 0:
                            break
                        abs_i = chunk_start + j
                        ctx = data[max(0, j - 32) : j + len(needle) + 64]
                        hits.append((abs_i, "L:" + needle.decode("latin-1", "replace"), ctx))
                        start = j + 1

                for s in NEEDLES_U16:
                    needle = s.encode("utf-16le")
                    start = 0
                    while True:
                        j = data.find(needle, start)
                        if j < 0:
                            break
                        abs_i = chunk_start + j
                        ctx = data[max(0, j - 32) : j + len(needle) + 64]
                        hits.append((abs_i, "U:" + s, ctx))
                        start = j + 1

                abs_base += len(block)
                carry = data[-128:]
        finally:
            reader.close()

    # dedupe exact abs
    seen = set()
    uniq = []
    for h in sorted(hits, key=lambda t: t[0]):
        if h[0] in seen:
            continue
        seen.add(h[0])
        uniq.append(h)

    lines.append(f"string hits: {len(uniq)}")
    by_label: dict[str, int] = {}
    for abs_i, lab, ctx in uniq:
        by_label[lab] = by_label.get(lab, 0) + 1
    for lab, n in sorted(by_label.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {lab}: {n}")

    # Show First Team / Reserves / U19 specifically
    for want in ("First Team", "Reserves", "Reserve", "U19", "U18", "U21", "Youth Team"):
        lines.append(f"\n## {want}")
        for abs_i, lab, ctx in uniq:
            if want not in lab:
                continue
            s = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
            lines.append(f"  @{abs_i} {lab}")
            lines.append(f"    {s}")
            lines.append(f"    hex={ctx.hex()}")

    # Schalke club object expansion: find main "FC Schalke 04" name record
    # Prefer the one near relation list we saw (~1986866253)
    schalke = [h for h in uniq if h[1].endswith("FC Schalke 04")]
    lines.append(f"\n## FC Schalke 04 latin hits: {len(schalke)}")
    for abs_i, lab, ctx in schalke[:20]:
        s = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
        lines.append(f"  @{abs_i} {s}")

    # Dump structure around best club hit using a streaming extract
    club = 1986866253
    lines.append(f"\n======== club object dump around {club} ========")
    # Extract ±8KB with one stream
    start = club - 2048
    end = club + 16384
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
                if len(buf) >= end - start:
                    break
        finally:
            reader.close()

    base = start
    # Find printable lp32 strings in club window
    lines.append("lp32 strings in club± window:")
    i = 0
    while i + 8 <= len(buf):
        ln = struct.unpack_from("<I", buf, i)[0]
        if 3 <= ln <= 60 and i + 4 + ln <= len(buf):
            raw = buf[i + 4 : i + 4 + ln]
            if raw.isascii() and all(32 <= b < 127 for b in raw):
                s = raw.decode("ascii")
                if any(c.isalpha() for c in s):
                    lines.append(f"  @{base+i} len={ln} {s!r}")
                    i += 4 + ln
                    continue
        i += 1

    # Find typed relation blocks like 03 4f XX 03 0y 02 <u32>
    lines.append("\ntyped 03 4f ## relations (sample):")
    i = 0
    rels = []
    while i + 12 <= len(buf):
        if buf[i] == 0x03 and buf[i + 1] == 0x4F:
            code = buf[i + 2]
            # expect 03 ?? 02 UID
            if buf[i + 3] == 0x03 and buf[i + 5] == 0x02:
                uid = struct.unpack_from("<I", buf, i + 6)[0]
                rels.append((base + i, code, buf[i + 4], uid))
            i += 3
        else:
            i += 1
    lines.append(f"  count={len(rels)}")
    # group by code
    by_code: dict[int, list] = {}
    for a, code, sub, uid in rels:
        by_code.setdefault(code, []).append((a, sub, uid))
    for code, items in sorted(by_code.items()):
        lines.append(f"  code=0x{code:02X} ('{chr(code) if 32<=code<127 else '?'}') n={len(items)}")
        for a, sub, uid in items[:8]:
            lines.append(f"    @{a} sub={sub} uid/val={uid}")

    # Also 03 00 ## pattern from earlier dump
    lines.append("\ntyped 03 00 ## relations:")
    i = 0
    rels2 = []
    while i + 12 <= len(buf):
        if buf[i] == 0x03 and buf[i + 1] == 0x00:
            code = buf[i + 2]
            if buf[i + 3] == 0x03 and buf[i + 5] == 0x02:
                uid = struct.unpack_from("<I", buf, i + 6)[0]
                rels2.append((base + i, code, buf[i + 4], uid))
            i += 3
        else:
            i += 1
    by_code2: dict[int, list] = {}
    for a, code, sub, uid in rels2:
        by_code2.setdefault(code, []).append((a, sub, uid))
    for code, items in sorted(by_code2.items()):
        lines.append(f"  code=0x{code:02X} n={len(items)}")
        for a, sub, uid in items[:6]:
            lines.append(f"    @{a} sub={sub} val={uid}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
