#!/usr/bin/env python3
"""Dig co-occurrence clusters for new Reserve/U19 UIDs → squad-list layouts."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-subunit-clusters-v2.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

KNOWN = {
    "Reserve_II": 2002138129,
    "U19": 2002332550,
    "Reserve_prev": 2002206353,
    "U19_prev": 2002423570,
}
for p in FIXTURE:
    KNOWN[p["name"]] = int(p["uid"])
NAME_BY = {v: k for k, v in KNOWN.items()}
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000

# From calibrate-v2 co-occurrence hits
TARGETS = [
    ("Reserve+U19 new", 813_080_782),
    ("both Reserves", 848_552_282),
    ("FT+U19s near shortlists?", 1_007_151_258),
    ("Reserve pair near shortlists", 1_007_148_222),
]


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


def dump(b: bytes, base: int, n: int | None = None) -> list[str]:
    if n is not None:
        b = b[:n]
    lines = []
    for i in range(0, len(b), 32):
        chunk = b[i : i + 32]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"  {base+i:10d}  {hexs:<96}  {asc}")
    return lines


def resolve_names(uids: list[int]) -> dict[int, str]:
    resolved = dict(NAME_BY)
    remaining = [u for u in uids if u not in resolved]
    if not remaining:
        return resolved
    pats = {u: b"\x00\x02" + struct.pack("<I", u) for u in remaining}
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
                for uid in list(remaining):
                    j = data.find(pats[uid])
                    if j < 0:
                        continue
                    for off in range(j + 6, min(len(data) - 8, j + 140)):
                        ln = struct.unpack_from("<I", data, off)[0]
                        if 5 <= ln <= 48 and off + 4 + ln <= len(data):
                            raw = data[off + 4 : off + 4 + ln]
                            if raw.isascii() and all(32 <= b < 127 for b in raw):
                                name = raw.decode("ascii")
                                if name[0].isupper() and any(c.isalpha() for c in name):
                                    cur = resolved.get(uid, "")
                                    if " " in name or " " not in cur:
                                        resolved[uid] = name
                                    if " " in name and uid in remaining:
                                        remaining.remove(uid)
                                    break
                carry = data[-160:]
                abs_base += len(block)
                if not remaining:
                    break
        finally:
            reader.close()
    return resolved


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
                    out.append((base + i, s[:120]))
            i = j
        else:
            i += 1
    return out


def scan_u32_runs(blob: bytes, base: int, min_n: int = 8) -> list[tuple[int, int, list[int]]]:
    found: list[tuple[int, int, list[int]]] = []
    i = 0
    while i + 4 <= len(blob):
        v = struct.unpack_from("<I", blob, i)[0]
        if not (UID_LO <= v <= UID_HI):
            i += 1
            continue
        start = i
        vals = [v]
        i += 4
        while i + 4 <= len(blob) and len(vals) < 80:
            vv = struct.unpack_from("<I", blob, i)[0]
            if UID_LO <= vv <= UID_HI and vv not in vals:
                vals.append(vv)
                i += 4
            else:
                break
        if len(vals) >= min_n:
            found.append((base + start, len(vals), vals))
        i = max(i, start + 1)
    return found


def gapped_uid_scan(
    blob: bytes, base: int, max_gap: int = 24, min_n: int = 10
) -> list[tuple[int, int, list[int]]]:
    """UID sequence allowing small gaps between UniqueIDs."""
    found: list[tuple[int, int, list[int]]] = []
    i = 0
    while i + 4 <= len(blob):
        v = struct.unpack_from("<I", blob, i)[0]
        if not (UID_LO <= v <= UID_HI):
            i += 1
            continue
        start = i
        vals = [v]
        i += 4
        while i + 4 <= len(blob) and len(vals) < 80:
            advanced = False
            for gap in range(0, max_gap + 1):
                if i + gap + 4 > len(blob):
                    break
                vv = struct.unpack_from("<I", blob, i + gap)[0]
                if UID_LO <= vv <= UID_HI and vv not in vals:
                    vals.append(vv)
                    i = i + gap + 4
                    advanced = True
                    break
            if not advanced:
                break
        if len(vals) >= min_n:
            found.append((base + start, len(vals), vals))
        i = max(i, start + 1)
    return found


def main() -> None:
    lines: list[str] = []

    def log(s: str = "") -> None:
        try:
            print(s)
        except UnicodeEncodeError:
            print(s.encode("ascii", "replace").decode("ascii"))
        lines.append(s)

    # Confirm player names for new UIDs
    log("=== resolve new calibration UIDs ===")
    names = resolve_names(list(KNOWN.values()))
    for label, uid in KNOWN.items():
        log(f"  {label} {uid} -> {names.get(uid, '?')}")

    for label, abs_ in TARGETS:
        log(f"\n######## {label} @{abs_} ########")
        win = extract(abs_, 8192, before=512)
        base = abs_ - 512
        # dump around each known UID in window
        for name, uid in KNOWN.items():
            pat = struct.pack("<I", uid)
            start = 0
            while True:
                j = win.find(pat, start)
                if j < 0:
                    break
                a = base + j
                ctx = win[max(0, j - 48) : j + 80]
                log(f"\n{name} @{a} (delta={a-abs_:+d})")
                for row in dump(ctx, a - min(48, j), len(ctx)):
                    log(row)
                start = j + 1

        log("\nnearby ASCII (filter keywords):")
        for a, s in strings_in(win, base):
            if any(
                k.lower() in s.lower()
                for k in (
                    "Schalke",
                    "First",
                    "Squad",
                    "U19",
                    "Reserve",
                    "Player",
                    "Staff",
                    "filt",
                    "Team",
                    "II",
                )
            ):
                log(f"  @{a} {s!r}")

        packed = scan_u32_runs(win, base, 10)
        log(f"\npacked u32 runs (>=10): {len(packed)}")
        for start, n, vals in packed[:12]:
            flags = [NAME_BY[u] for u in vals if u in NAME_BY]
            log(f"  @{start} n={n} d={start-abs_:+d} flags={flags or '-'}")
            if flags:
                names2 = resolve_names(vals)
                for i, u in enumerate(vals):
                    mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
                    log(f"    [{i:02d}] {u} {names2.get(u,'')}{mark}")

        gapped = gapped_uid_scan(win, base, 32, 12)
        log(f"\ngapped UID runs (>=12, gap<=32): {len(gapped)}")
        for start, n, vals in gapped[:10]:
            flags = [NAME_BY[u] for u in vals if u in NAME_BY]
            log(f"  @{start} n={n} d={start-abs_:+d} flags={flags or '-'}")
            if flags and len(flags) >= 2:
                names2 = resolve_names(vals)
                for i, u in enumerate(vals):
                    mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
                    log(f"    [{i:02d}] {u} {names2.get(u,'')}{mark}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
