#!/usr/bin/env python3
"""
Hunt DOB near employment/name markers: 00 02 <uid> (how extract resolves names).

Streams full save; locks shared relative offsets of DOB encodings vs the marker.
"""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from datetime import date
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-emp-stream-hunt.txt"
RADIUS_BEFORE = 256
RADIUS_AFTER = 512
BLOCK = 16 * 1024 * 1024
OVERLAP = RADIUS_BEFORE + RADIUS_AFTER + 32
MAX_MARKS = 10


def dob_pats(dob: date, age: int) -> dict[str, bytes]:
    yday0 = dob.timetuple().tm_yday - 1
    days1900 = (dob - date(1900, 1, 1)).days
    age_days = (date(2039, 7, 1) - dob).days
    return {
        "dmy": struct.pack("<BBH", dob.day, dob.month, dob.year),
        "ymd": struct.pack("<HBB", dob.year, dob.month, dob.day),
        "tcm_d0_y": struct.pack("<hh", yday0, dob.year),
        "tcm_y_d0": struct.pack("<hh", dob.year, yday0),
        "days1900": struct.pack("<I", days1900),
        "age_days_u16": struct.pack("<H", age_days),
        "age_u8": bytes([age]),
        "packed_dmy": struct.pack("<I", dob.day | (dob.month << 8) | (dob.year << 16)),
        "y1900_m_d": bytes([dob.year - 1900, dob.month, dob.day]),
        "d_m_y1900": bytes([dob.day, dob.month, dob.year - 1900]),
    }


def main() -> None:
    metas = []
    marker_map: dict[bytes, int] = {}
    for i, p in enumerate(PLAYERS):
        y, m, d = map(int, p["dob"].split("-"))
        dob = date(y, m, d)
        uid = int(p["uid"])
        marker = b"\x00\x02" + struct.pack("<I", uid)
        metas.append(
            {
                "name": p["name"],
                "uid": uid,
                "dob": dob,
                "age": int(p["age"]),
                "pats": dob_pats(dob, int(p["age"])),
                "marks": [],
            }
        )
        marker_map[marker] = i

    markers = list(marker_map.keys())
    print(f"streaming employment markers for {len(markers)} players…", flush=True)

    with SAVE.open("rb") as f:
        assert f.read(26)[2:6] == b"fmf."
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        try:
            while True:
                try:
                    chunk = reader.read(BLOCK)
                except zstd.ZstdError as err:
                    print(f"  zstd end @ {abs_base/1e9:.2f} GB: {err}", flush=True)
                    break
                if not chunk:
                    break
                data = carry + chunk
                for marker in markers:
                    pi = marker_map[marker]
                    if len(metas[pi]["marks"]) >= MAX_MARKS:
                        continue
                    start = 0
                    while len(metas[pi]["marks"]) < MAX_MARKS:
                        i = data.find(marker, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        metas[pi]["marks"].append(abs_off)
                        start = i + 1
                abs_base += len(chunk)
                carry = data[-OVERLAP:]
                if abs_base % (256 * 1024 * 1024) < BLOCK:
                    print(f"  … {abs_base/1e9:.2f} GB", flush=True)
        finally:
            reader.close()

    needed = {off for m in metas for off in m["marks"]}
    print(f"re-stream {len(needed)} mark windows…", flush=True)
    windows: dict[int, bytes] = {}
    win_len = RADIUS_BEFORE + RADIUS_AFTER

    with SAVE.open("rb") as f:
        f.read(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        pending = set(needed)
        try:
            while pending:
                try:
                    chunk = reader.read(BLOCK)
                except zstd.ZstdError:
                    break
                if not chunk:
                    break
                data = carry + chunk
                data_abs_start = abs_base - len(carry)
                done = []
                for off in list(pending):
                    lo = off - RADIUS_BEFORE
                    hi = off + RADIUS_AFTER
                    if lo >= data_abs_start and hi <= data_abs_start + len(data):
                        rel = lo - data_abs_start
                        windows[off] = data[rel : rel + win_len]
                        done.append(off)
                for off in done:
                    pending.discard(off)
                abs_base += len(chunk)
                carry = data[-OVERLAP:]
        finally:
            reader.close()

    lines = [f"save={SAVE.name}", ""]
    gap_players: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))

    for m in metas:
        lines.append(f"## {m['name']} marks={m['marks'][:6]}")
        if not m["marks"]:
            lines.append("  NO employment markers in stream")
            continue
        for off in m["marks"]:
            win = windows.get(off)
            if not win:
                lines.append(f"  @{off}: missing window")
                continue
            rel0 = RADIUS_BEFORE  # marker starts here
            found = []
            for enc, pat in m["pats"].items():
                if enc == "age_u8":
                    # only accept within ±64 to cut noise
                    start = max(0, rel0 - 64)
                    end = min(len(win), rel0 + 64)
                    region = win[start:end]
                    j = 0
                    while True:
                        k = region.find(pat, j)
                        if k < 0:
                            break
                        delta = (start + k) - rel0
                        found.append((enc, delta))
                        gap_players[enc][delta].add(m["name"])
                        j = k + 1
                    continue
                start = 0
                while True:
                    j = win.find(pat, start)
                    if j < 0:
                        break
                    delta = j - rel0
                    found.append((enc, delta))
                    gap_players[enc][delta].add(m["name"])
                    start = j + 1
            lines.append(f"  @{off}: {found[:14]}")

    lines.append("")
    lines.append("## LOCK shared emp→DOB deltas (≥8 players)")
    for enc, gaps in sorted(gap_players.items()):
        ranked = sorted(gaps.items(), key=lambda t: (-len(t[1]), t[0]))
        shown = 0
        for delta, names in ranked:
            if len(names) < 5:
                break
            tag = "LOCK" if len(names) >= 8 else "weak"
            lines.append(
                f"  {tag} {enc} @{delta:+d} n={len(names)} eg={sorted(names)[:8]}"
            )
            shown += 1
            if shown >= 8:
                break

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-60:]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
