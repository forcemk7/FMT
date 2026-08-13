#!/usr/bin/env python3
"""Extract assoc IDs from person records of FT / Reserve / U19 calibration players."""

from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-person-assoc-ids.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

KNOWN = {
    "Reserve_II": 2002138129,  # Ermin Maric
    "U19": 2002332550,  # James Solo
    "Reserve_prev": 2002206353,
    "U19_prev": 2002423570,
}
for p in FIXTURE:
    KNOWN[p["name"]] = int(p["uid"])
NAME_BY = {v: k for k, v in KNOWN.items()}


def log(s: str = "") -> None:
    print(s, flush=True)


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


def find_person_anchors(uid: int, limit: int = 8) -> list[int]:
    marked = b"\x00\x02" + struct.pack("<I", uid)
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
                    j = data.find(marked, start)
                    if j < 0:
                        break
                    # prefer sites with a following lp32 name
                    abs_ = chunk_start + j
                    hits.append(abs_)
                    start = j + 1
                abs_base += len(block)
                carry = data[-8:]
                if len(hits) >= limit:
                    break
        finally:
            reader.close()
    return hits


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


def extract_assocs(win: bytes, base: int, uid: int) -> list[tuple[int, int, int, str]]:
    """Find patterns: <tag> 02 <id> 02 <uid> within window."""
    uidb = struct.pack("<I", uid)
    out = []
    start = 0
    while True:
        j = win.find(uidb, start)
        if j < 0:
            break
        # look back for 02 immediately before uid, and tag 02 id before that
        if j >= 1 and win[j - 1] == 0x02 and j >= 7:
            assoc = struct.unpack_from("<I", win, j - 5)[0]
            if win[j - 6] == 0x02:
                tag = win[j - 7]
                kind = f"tag=0x{tag:02X} 02 <id> 02 <uid>"
                out.append((base + j - 7, tag, assoc, kind))
        # also: 0b 02 <id> <uid> without intervening 02 (rare)
        if j >= 6 and win[j - 6 : j - 4] == b"\x0b\x02":
            assoc = struct.unpack_from("<I", win, j - 4)[0]
            out.append((base + j - 6, 0x0B, assoc, "0b02 <id> <uid>"))
        start = j + 1
    return out


def lp_strings(win: bytes, base: int) -> list[tuple[int, str]]:
    out = []
    for i in range(0, len(win) - 8):
        ln = struct.unpack_from("<I", win, i)[0]
        if 3 <= ln <= 48 and i + 4 + ln <= len(win):
            raw = win[i + 4 : i + 4 + ln]
            if raw.isascii() and all(32 <= b < 127 for b in raw):
                s = raw.decode("ascii")
                if s[:1].isupper() and any(c.isalpha() for c in s):
                    out.append((base + i, s))
    return out


def main() -> None:
    lines: list[str] = []

    def out(s: str = "") -> None:
        log(s)
        lines.append(s)

    # id -> which players reference it
    id_players: dict[int, set[str]] = defaultdict(set)
    player_ids: dict[str, list[int]] = defaultdict(list)

    for label, uid in KNOWN.items():
        out(f"\n######## {label} {uid} ########")
        anchors = find_person_anchors(uid, limit=6)
        out(f"0002+uid anchors: {len(anchors)} {anchors[:4]}")
        seen_local = set()
        for h in anchors[:4]:
            win = extract(h, 384, before=96)
            base = h - 96
            names = lp_strings(win, base)
            name_hit = [s for _, s in names if any(c.islower() for c in s)]
            out(f"\n--- @{h} names={name_hit[:6]} ---")
            for row in dump(win, base, 192):
                out(row)
            for a, tag, assoc, kind in extract_assocs(win, base, uid):
                key = (tag, assoc)
                if key in seen_local:
                    continue
                seen_local.add(key)
                out(f"  ASSOC @{a} {kind} id={assoc}")
                if 1_000 <= assoc <= 2_000_000:
                    id_players[assoc].add(label)
                    player_ids[label].append(assoc)

    out("\n======== shared assoc IDs across players ========")
    # group players into FT / Reserve / U19
    groups = {
        "FT": {"Dennis Seimen", "Patrick Bandeira", "Robert Müller"},
        "Reserve": {"Reserve_II", "Reserve_prev"},
        "U19": {"U19", "U19_prev"},
    }
    for assoc, players in sorted(id_players.items(), key=lambda kv: -len(kv[1])):
        if len(players) < 2:
            continue
        out(f"  id={assoc} players={sorted(players)}")
        for gname, gset in groups.items():
            inter = players & gset
            if inter:
                out(f"    in {gname}: {sorted(inter)}")

    out("\n======== per-player assoc id sets ========")
    for label, ids in player_ids.items():
        c = Counter(ids)
        out(f"  {label}: {dict(c)}")

    # Cross-check: for promising shared IDs, count 0b02/xx02 links globally
    promising = [
        assoc
        for assoc, players in id_players.items()
        if len(players) >= 2 and 10_000 <= assoc <= 1_000_000
    ]
    out(f"\n======== global link counts for promising ids {promising[:20]} ========")
    if promising:
        pats = []
        for assoc in promising[:15]:
            for tag in (0x0B, 0x09, 0x08, 0x0A, 0x07):
                pats.append(
                    (
                        assoc,
                        tag,
                        bytes([tag, 0x02]) + struct.pack("<I", assoc) + b"\x02",
                    )
                )
        counts: dict[tuple[int, int], list[int]] = defaultdict(list)
        abs_base = 0
        carry = b""
        max_pat = max(len(p[2]) for p in pats)
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
                    for assoc, tag, pat in pats:
                        start = 0
                        while True:
                            j = data.find(pat, start)
                            if j < 0:
                                break
                            if j + len(pat) + 4 <= len(data):
                                uid = struct.unpack_from("<I", data, j + len(pat))[0]
                                if 1_900_000_000 <= uid <= 2_100_000_000:
                                    counts[(assoc, tag)].append(uid)
                            start = j + 1
                    abs_base += len(block)
                    carry = data[-(max_pat + 3) :]
                    if abs_base % (128 * 1024 * 1024) < 8 * 1024 * 1024:
                        log(f"  scanned {abs_base/1e6:.0f}MB")
            finally:
                reader.close()
        for (assoc, tag), uids in sorted(counts.items()):
            uniq = list(dict.fromkeys(uids))
            known = [NAME_BY[u] for u in uniq if u in NAME_BY]
            out(
                f"  id={assoc} tag=0x{tag:02X} n={len(uniq)} known={known}"
            )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    out(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
