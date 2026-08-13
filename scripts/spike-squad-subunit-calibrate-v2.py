#!/usr/bin/env python3
"""Calibrate subunit codes with updated Reserve/U19 UIDs + First Team fixtures."""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-subunit-calibrate-v2.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

KNOWN = {
    # Updated calibration (user-confirmed / preferred)
    "Reserve_II": 2002138129,
    "U19": 2002332550,
    # Prior candidates (may still be relevant)
    "Reserve_prev": 2002206353,
    "U19_prev": 2002423570,
}
for p in FIXTURE:
    KNOWN[p["name"]] = int(p["uid"])
NAME_BY = {v: k for k, v in KNOWN.items()}
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000
CLUB = 1_986_866_253


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


def stream_hits() -> dict[int, list[int]]:
    pats = {u: struct.pack("<I", u) for u in KNOWN.values()}
    hits = {u: [] for u in KNOWN.values()}
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
                for uid, pat in pats.items():
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        hits[uid].append(chunk_start + j)
                        start = j + 1
                abs_base += len(block)
                carry = data[-8:]
        finally:
            reader.close()
    for u in hits:
        hits[u] = sorted(set(hits[u]))
    return hits


def parse_club_relations(win: bytes, base: int) -> list[tuple[int, int, int, int, int]]:
    j = win.find(b"FC Schalke 04")
    after = win[j:]
    after_base = base + j
    entries: list[tuple[int, int, int, int, int]] = []
    i = 0
    while i + 12 <= len(after):
        if after[i] == 0x03 and after[i + 3] == 0x03 and after[i + 5] == 0x02:
            kind = after[i + 1]
            code = after[i + 2]
            sub = after[i + 4]
            val = struct.unpack_from("<I", after, i + 6)[0]
            if UID_LO <= val <= UID_HI:
                entries.append((after_base + i, kind, code, sub, val))
            i += 6
        else:
            i += 1
    return entries


def main() -> None:
    lines: list[str] = []

    def log(s: str = "") -> None:
        try:
            print(s)
        except UnicodeEncodeError:
            print(s.encode("ascii", "replace").decode("ascii"))
        lines.append(s)

    log("=== subunit calibrate v2 ===")
    for k, v in KNOWN.items():
        log(f"  {k}={v}")

    log("\npass1: club relations…")
    win = extract(CLUB, 120_000, before=256)
    entries = parse_club_relations(win, CLUB - 256)

    for name, uid in KNOWN.items():
        rows = [(a, k, c, s) for a, k, c, s, v in entries if v == uid]
        log(f"\n{name} ({uid}): {len(rows)} relations")
        for a, k, c, s in rows:
            log(f"  @{a} kind=0x{k:02X} code=0x{c:02X} sub={s}")

    by_bucket: dict[tuple[int, int], list[int]] = defaultdict(list)
    for a, k, c, s, v in entries:
        if v not in by_bucket[(k, c)]:
            by_bucket[(k, c)].append(v)

    log("\n======== buckets containing any known ========")
    interesting = []
    for (k, c), uids in by_bucket.items():
        known_here = [NAME_BY[u] for u in uids if u in NAME_BY]
        if not known_here:
            continue
        interesting.append((k, c, uids, known_here))

    for k, c, uids, known_here in sorted(
        interesting, key=lambda t: (-len(t[2]), t[1])
    ):
        log(f"\n## kind=0x{k:02X} code=0x{c:02X} n={len(uids)} known={known_here}")
        names = resolve_names(uids)
        for i, u in enumerate(uids):
            mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
            log(f"  [{i:02d}] {u} {names.get(u, '')}{mark}")

    # Focus: full code 0x2A / 0x2D / 0x0A lists even if not all known land there
    log("\n======== force-dump code 0x2A / 0x2D / 0x0A / 0x0B / 0x0C ========")
    for code in (0x2A, 0x2D, 0x0A, 0x0B, 0x0C, 0x16, 0x24, 0x07, 0x1F):
        uids = by_bucket.get((0x00, code), [])
        known_here = [NAME_BY[u] for u in uids if u in NAME_BY]
        log(f"\ncode=0x{code:02X} n={len(uids)} known={known_here}")
        if not uids:
            continue
        names = resolve_names(uids)
        for i, u in enumerate(uids):
            mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
            log(f"  [{i:02d}] {u} {names.get(u, '')}{mark}")

    # Co-occurrence of NEW reserve/u19 with FT fixtures
    log("\npass2: co-occurrence clusters (2KB)…")
    hits = stream_hits()
    for name, uid in KNOWN.items():
        log(f"  {name}: {len(hits[uid])} hits")

    events = [(o, u) for u, offs in hits.items() for o in offs]
    events.sort()
    window = 2048
    clusters = []
    i = 0
    while i < len(events):
        j = i
        set_u = {events[i][1]}
        while j + 1 < len(events) and events[j + 1][0] - events[i][0] <= window:
            j += 1
            set_u.add(events[j][1])
        if len(set_u) >= 2:
            names = sorted(NAME_BY[u] for u in set_u)
            clusters.append(
                {
                    "start": events[i][0],
                    "end": events[j][0],
                    "names": names,
                }
            )
        i += 1
        while i < len(events) and events[i][0] == events[i - 1][0]:
            i += 1

    def score(c):
        n = set(c["names"])
        ft = sum(
            x in n for x in ("Dennis Seimen", "Patrick Bandeira", "Robert Müller")
        )
        return (
            "Reserve_II" in n or "U19" in n,
            ft,
            "Reserve_II" in n,
            "U19" in n,
        )

    seen = set()
    shown = 0
    for c in sorted(clusters, key=score, reverse=True):
        key = (c["start"] // 512, tuple(c["names"]))
        if key in seen:
            continue
        seen.add(key)
        n = set(c["names"])
        if not (
            ("Reserve_II" in n or "U19" in n)
            and any(
                x in n
                for x in (
                    "Dennis Seimen",
                    "Patrick Bandeira",
                    "Robert Müller",
                    "Reserve_prev",
                    "U19_prev",
                )
            )
        ):
            # also show pure subunit mixes
            if not (
                ("Reserve_II" in n and "U19" in n)
                or ("Reserve_II" in n and "Reserve_prev" in n)
                or ("U19" in n and "U19_prev" in n)
            ):
                continue
        log(
            f"  @{c['start']}..{c['end']} span={c['end']-c['start']} {c['names']}"
        )
        shown += 1
        if shown >= 40:
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
