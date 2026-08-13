#!/usr/bin/env python3
"""Deep-dive Schalke First Team / U19 name objects found outside the Reserves string table."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-schalke-u19-ft-names.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

UIDS = {
    "Reserve_II": 2002206353,
    "U19": 2002423570,
}
for p in FIXTURE:
    UIDS[p["name"]] = int(p["uid"])
UID_BYTES = {k: struct.pack("<I", v) for k, v in UIDS.items()}
UID_DBL = {k: struct.pack("<Q", v) for k, v in UIDS.items()}


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


def find_ascii_stream(needle: bytes, limit: int = 40, max_abs: int | None = None) -> list[int]:
    hits: list[int] = []
    abs_base = 0
    carry = b""
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
                start = 0
                while len(hits) < limit:
                    j = data.find(needle, start)
                    if j < 0:
                        break
                    abs_ = chunk_start + j
                    if max_abs is None or abs_ < max_abs:
                        hits.append(abs_)
                    start = j + 1
                abs_base += len(block)
                carry = data[-(len(needle) - 1) :]
                if max_abs is not None and abs_base > max_abs and len(hits) >= 1:
                    # keep scanning a bit if we want all under max
                    if abs_base > max_abs + 8 * 1024 * 1024:
                        break
                if len(hits) >= limit:
                    break
        finally:
            reader.close()
    return hits


def dump(blob: bytes, base: int, n: int = 256) -> list[str]:
    lines: list[str] = []
    chunk = blob[:n]
    for off in range(0, len(chunk), 32):
        row = chunk[off : off + 32]
        hx = " ".join(f"{b:02x}" for b in row)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"  {base+off:10d}  {hx}  {asc}")
    return lines


def strings_in(blob: bytes, base: int, min_len: int = 4) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(blob):
        if 0x20 <= blob[i] < 0x7F:
            j = i
            while j < len(blob) and 0x20 <= blob[j] < 0x7F:
                j += 1
            if j - i >= min_len:
                s = blob[i:j].decode("ascii", "replace")
                if any(c.isalpha() for c in s):
                    out.append((base + i, s[:100]))
            i = j
        else:
            i += 1
    return out


def uid_hits_in(blob: bytes, base: int) -> dict[str, list[int]]:
    hits: dict[str, list[int]] = {}
    for name, nb in UID_BYTES.items():
        pos: list[int] = []
        start = 0
        while True:
            i = blob.find(nb, start)
            if i < 0:
                break
            pos.append(base + i)
            start = i + 1
        if pos:
            hits[name] = pos
    return hits


def dbl_hits_in(blob: bytes, base: int) -> dict[str, list[int]]:
    hits: dict[str, list[int]] = {}
    for name, nb in UID_DBL.items():
        pos: list[int] = []
        start = 0
        while True:
            i = blob.find(nb, start)
            if i < 0:
                break
            pos.append(base + i)
            start = i + 1
        if pos:
            hits[name] = pos
    return hits


def scan_dbl_arrays(blob: bytes, base: int, min_n: int = 8) -> list[tuple[int, int, list[int]]]:
    found: list[tuple[int, int, list[int]]] = []
    i = 0
    while i + 8 <= len(blob):
        v = struct.unpack_from("<Q", blob, i)[0]
        if not (1_900_000_000 <= v <= 2_200_000_000):
            i += 1
            continue
        start = i
        vals = [v]
        i += 8
        while i + 8 <= len(blob) and len(vals) < 80:
            advanced = False
            for gap in range(0, 25):
                if i + gap + 8 > len(blob):
                    break
                vv = struct.unpack_from("<Q", blob, i + gap)[0]
                if 1_900_000_000 <= vv <= 2_200_000_000 and vv not in vals:
                    vals.append(vv)
                    i = i + gap + 8
                    advanced = True
                    break
            if not advanced:
                break
        if len(vals) >= min_n:
            found.append((base + start, len(vals), vals))
        i = max(i, start + 1)
    return found


def scan_u32_arrays(blob: bytes, base: int, min_n: int = 8) -> list[tuple[int, int, list[int]]]:
    """Packed unique player-ish u32 runs."""
    found: list[tuple[int, int, list[int]]] = []
    i = 0
    while i + 4 <= len(blob):
        v = struct.unpack_from("<I", blob, i)[0]
        if not (1_900_000_000 <= v <= 2_200_000_000):
            i += 1
            continue
        start = i
        vals = [v]
        i += 4
        while i + 4 <= len(blob) and len(vals) < 80:
            vv = struct.unpack_from("<I", blob, i)[0]
            if 1_900_000_000 <= vv <= 2_200_000_000 and vv not in vals:
                vals.append(vv)
                i += 4
            else:
                break
        if len(vals) >= min_n:
            found.append((base + start, len(vals), vals))
        i = max(i, start + 1)
    return found


def main() -> None:
    lines: list[str] = []

    def log(s: str = "") -> None:
        print(s)
        lines.append(s)

    needles = [
        b"Schalke 04 U19",
        b"Schalke 04 II",
        b"FC Schalke 04 II",
        b"FC Schalke 04",
        b"Under 19",
        b"U19s",
    ]
    for needle in needles:
        hits = find_ascii_stream(needle, limit=25, max_abs=120_000_000)
        log(f"=== needle {needle!r}: {len(hits)} (abs<120M) ===")
        for h in hits:
            win = extract(h, 60, before=40)
            asc = "".join(chr(b) if 32 <= b < 127 else "." for b in win)
            log(f"  @{h}: {asc}")
        log()

    targets = [
        ("early FC Schalke 04", 3_431_104),
        ("Schalke 04 II name table", 10_087_063),
        ("Schalke 04 U19 area", 60_171_272),
    ]

    for label, abs_ in targets:
        log(f"\n######## {label} @{abs_} ########")
        win = extract(abs_, 400_000, before=200_000)
        base = abs_ - 200_000
        # center dump
        mid = 200_000
        for row in dump(win[mid - 64 : mid + 320], abs_ - 64, 384):
            log(row)
        log("nearby strings (±2KB):")
        local = win[mid - 2000 : mid + 2000]
        for a, s in strings_in(local, abs_ - 2000)[:50]:
            if any(
                k in s
                for k in (
                    "Schalke",
                    "U19",
                    "Under",
                    "First",
                    "Reserve",
                    "Squad",
                    "Team",
                )
            ):
                log(f"  @{a} {s!r}")
        uh = uid_hits_in(win, base)
        dh = dbl_hits_in(win, base)
        log("known u32 UIDs in ±200KB:")
        if not uh:
            log("  (none)")
        for n, pos in uh.items():
            log(f"  {n}: deltas={[p - abs_ for p in pos[:10]]} (n={len(pos)})")
        log("known double UIDs in ±200KB:")
        if not dh:
            log("  (none)")
        for n, pos in dh.items():
            log(f"  {n}: deltas={[p - abs_ for p in pos[:10]]} (n={len(pos)})")

        darr = scan_dbl_arrays(win, base, 10)
        log(f"double arrays (>=10) in ±200KB: {len(darr)}")
        for start, n, vals in darr[:15]:
            flags = [name for name, uid in UIDS.items() if uid in vals]
            log(
                f"  @{start} n={n} Δ={start-abs_:+d} flags={flags or '-'} "
                f"heads={vals[:3]}"
            )

        uarr = scan_u32_arrays(win, base, 12)
        log(f"packed u32 arrays (>=12) in ±200KB: {len(uarr)}")
        for start, n, vals in uarr[:15]:
            flags = [name for name, uid in UIDS.items() if uid in vals]
            log(
                f"  @{start} n={n} Δ={start-abs_:+d} flags={flags or '-'} "
                f"heads={vals[:3]}"
            )

    # Wider window around U19 name only — players may sit further from the string
    abs_u19 = 60_171_272
    log(f"\n######## WIDE U19 @{abs_u19} ±1MB ########")
    win = extract(abs_u19, 2_000_000, before=1_000_000)
    base = abs_u19 - 1_000_000
    uh = uid_hits_in(win, base)
    dh = dbl_hits_in(win, base)
    log("known u32:")
    for n, pos in uh.items():
        log(f"  {n}: n={len(pos)} first_deltas={[p-abs_u19 for p in pos[:8]]}")
    log("known dbl:")
    for n, pos in dh.items():
        log(f"  {n}: n={len(pos)} first_deltas={[p-abs_u19 for p in pos[:8]]}")
    # if U19 player found, dump context
    for name in ("U19", "Reserve_II", "Dennis Seimen"):
        for dmap in (uh, dh):
            if name in dmap:
                for p in dmap[name][:3]:
                    ctx = extract(p, 128, before=64)
                    log(f"\ncontext {name} @{p}:")
                    for row in dump(ctx, p - 64, 192):
                        log(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
