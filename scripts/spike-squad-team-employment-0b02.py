#!/usr/bin/env python3
"""Validate 0b02 <teamId> 02 <uid> employment links — single-pass stream."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-team-employment-0b02.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

TID = {
    "FirstTeam": 193616,
    "Reserve_cand": 237871,  # near Ermin Maric
    "U19_cand": 439758,  # near James Solo
}

KNOWN = {
    "Reserve_II": 2002138129,  # Ermin Maric
    "U19": 2002332550,  # James Solo
    "Reserve_prev": 2002206353,
    "U19_prev": 2002423570,
}
for p in FIXTURE:
    KNOWN[p["name"]] = int(p["uid"])
NAME_BY = {v: k for k, v in KNOWN.items()}
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000


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
                        if 3 <= ln <= 48 and off + 4 + ln <= len(data):
                            raw = data[off + 4 : off + 4 + ln]
                            if raw.isascii() and all(32 <= b < 127 for b in raw):
                                name = raw.decode("ascii")
                                if name[:1].isupper() and any(c.isalpha() for c in name):
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


def main() -> None:
    lines: list[str] = []

    def out(s: str = "") -> None:
        log(s)
        lines.append(s)

    # Build search patterns once
    pats = {
        label: b"\x0b\x02" + struct.pack("<I", tid) + b"\x02"
        for label, tid in TID.items()
    }
    # also alternate tag 09 02 (seen near Bandeira)
    pats09 = {
        label: b"\x09\x02" + struct.pack("<I", tid) + b"\x02"
        for label, tid in TID.items()
    }

    rosters: dict[str, list[tuple[int, int]]] = {k: [] for k in TID}
    rosters09: dict[str, list[tuple[int, int]]] = {k: [] for k in TID}

    out("pass1: single stream scan for 0b02/09xx team links…")
    abs_base = 0
    carry = b""
    max_pat = max(len(p) for p in list(pats.values()) + list(pats09.values()))
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
                for label, pat in pats.items():
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        if j + len(pat) + 4 <= len(data):
                            uid = struct.unpack_from("<I", data, j + len(pat))[0]
                            if UID_LO <= uid <= UID_HI:
                                rosters[label].append((chunk_start + j, uid))
                        start = j + 1
                for label, pat in pats09.items():
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        if j + len(pat) + 4 <= len(data):
                            uid = struct.unpack_from("<I", data, j + len(pat))[0]
                            if UID_LO <= uid <= UID_HI:
                                rosters09[label].append((chunk_start + j, uid))
                        start = j + 1
                abs_base += len(block)
                carry = data[-(max_pat + 3) :]
                if abs_base % (64 * 1024 * 1024) < 8 * 1024 * 1024:
                    log(f"  …scanned {abs_base/1e6:.0f}MB")
        finally:
            reader.close()

    def uniq(rows: list[tuple[int, int]]) -> list[tuple[int, int]]:
        seen = set()
        out_rows = []
        for a, u in rows:
            if u in seen:
                continue
            seen.add(u)
            out_rows.append((a, u))
        return out_rows

    for tagname, bag in (("0b02", rosters), ("09xx", rosters09)):
        out(f"\n===== tag {tagname} =====")
        for label, tid in TID.items():
            rows = uniq(bag[label])
            out(f"\n## {label}={tid} n={len(rows)}")
            uids = [u for _, u in rows]
            known_here = [NAME_BY[u] for u in uids if u in NAME_BY]
            out(f"known: {known_here}")
            names = resolve_names(uids)
            for i, (a, u) in enumerate(rows):
                mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
                out(f"  [{i:02d}] {u}  {names.get(u, '')}{mark}  @{a}")

            # name near a few TID plain hits (not just employment)
            if label.endswith("_cand") or label == "FirstTeam":
                samples = 0
                for a, u in rows[:3]:
                    win = extract(a, 300, before=150)
                    for i in range(0, len(win) - 8):
                        ln = struct.unpack_from("<I", win, i)[0]
                        if 5 <= ln <= 40 and i + 4 + ln <= len(win):
                            raw = win[i + 4 : i + 4 + ln]
                            if raw.isascii() and all(32 <= b < 127 for b in raw):
                                s = raw.decode("ascii")
                                if any(
                                    k in s
                                    for k in ("Schalke", "U19", " II", "First", "Under")
                                ):
                                    out(f"  near link @{a}: {s!r}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    out(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
