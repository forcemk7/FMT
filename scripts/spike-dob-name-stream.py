#!/usr/bin/env python3
"""
Lean full-save name→DOB hunt.

Only rare last-name UTF-16LE needles; cap hits per player; tolerate zstd EOF.
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
OUT = ROOT / "tmp" / "fm-spike" / "dob-name-stream-hunt.txt"
RADIUS = 1024
BLOCK = 16 * 1024 * 1024
OVERLAP = RADIUS * 2 + 64
MAX_HITS = 8

# Avoid common/short tokens that explode matches.
SKIP_TOKENS = {
    "jones",
    "robert",
    "rodrig",
    "rodri",
    "it",
    "itu",
}


def last_token(name: str) -> str:
    parts = name.replace("-", " ").split()
    return parts[-1] if parts else name


def dob_pats(dob: date) -> dict[str, bytes]:
    yday0 = dob.timetuple().tm_yday - 1
    days1900 = (dob - date(1900, 1, 1)).days
    return {
        "dmy": struct.pack("<BBH", dob.day, dob.month, dob.year),
        "ymd": struct.pack("<HBB", dob.year, dob.month, dob.day),
        "tcm_d0_y": struct.pack("<hh", yday0, dob.year),
        "days1900": struct.pack("<I", days1900),
        "packed_dmy": struct.pack("<I", dob.day | (dob.month << 8) | (dob.year << 16)),
    }


def main() -> None:
    metas = []
    needle_map: dict[bytes, list[int]] = defaultdict(list)
    for i, p in enumerate(PLAYERS):
        y, m, d = map(int, p["dob"].split("-"))
        dob = date(y, m, d)
        last = last_token(p["name"])
        metas.append(
            {
                "name": p["name"],
                "last": last,
                "uid": int(p["uid"]),
                "dob": dob,
                "pats": dob_pats(dob),
                "uid_pat": struct.pack("<I", int(p["uid"])),
                "hits": [],  # abs offs
                "skipped": last.lower() in SKIP_TOKENS or len(last) < 5,
            }
        )
        if metas[-1]["skipped"]:
            continue
        raw = last.encode("utf-16le")
        needle_map[raw].append(i)

    needles = list(needle_map.keys())
    print(
        f"streaming {SAVE.name} needles={len(needles)} "
        f"active={sum(1 for m in metas if not m['skipped'])}/{len(metas)}",
        flush=True,
    )

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
                for needle in needles:
                    start = 0
                    while True:
                        i = data.find(needle, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        for pi in needle_map[needle]:
                            if len(metas[pi]["hits"]) < MAX_HITS:
                                metas[pi]["hits"].append(abs_off)
                        start = i + 1
                        # if all capped for this needle, stop scanning it in this chunk
                        if all(len(metas[pi]["hits"]) >= MAX_HITS for pi in needle_map[needle]):
                            break
                abs_base += len(chunk)
                carry = data[-OVERLAP:]
                if abs_base % (128 * 1024 * 1024) < BLOCK:
                    print(f"  … {abs_base/1e9:.2f} GB", flush=True)
        finally:
            reader.close()

    needed = {off for m in metas for off in m["hits"]}
    print(f"re-stream {len(needed)} windows…", flush=True)
    windows: dict[int, bytes] = {}  # abs -> win centered on name

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
                    lo = off - RADIUS
                    hi = off + RADIUS
                    if lo >= data_abs_start and hi <= data_abs_start + len(data):
                        rel = lo - data_abs_start
                        windows[off] = data[rel : rel + 2 * RADIUS]
                        done.append(off)
                for off in done:
                    pending.discard(off)
                abs_base += len(chunk)
                carry = data[-OVERLAP:]
        finally:
            reader.close()

    lines = [f"save={SAVE.name}", f"radius=±{RADIUS}", ""]
    gap_players: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))

    for m in metas:
        lines.append(
            f"## {m['name']} last={m['last']} skipped={m['skipped']} "
            f"hits={m['hits'][:6]}"
        )
        if m["skipped"] or not m["hits"]:
            continue
        for off in m["hits"]:
            win = windows.get(off)
            if not win:
                lines.append(f"  @{off}: missing window")
                continue
            rel0 = RADIUS
            found = []
            for enc, pat in m["pats"].items():
                start = 0
                while True:
                    j = win.find(pat, start)
                    if j < 0:
                        break
                    delta = j - rel0
                    found.append((enc, delta))
                    gap_players[enc][delta].add(m["name"])
                    start = j + 1
            uid_rel = []
            start = 0
            while True:
                j = win.find(m["uid_pat"], start)
                if j < 0:
                    break
                uid_rel.append(j - rel0)
                start = j + 1
            lines.append(f"  @{off}: dob={found[:10]} uid_rel={uid_rel[:6]}")

    lines.append("")
    lines.append("## LOCK shared name→DOB deltas (≥6 players)")
    any_lock = False
    for enc, gaps in sorted(gap_players.items()):
        ranked = sorted(gaps.items(), key=lambda t: (-len(t[1]), t[0]))
        for delta, names in ranked[:6]:
            if len(names) >= 6:
                any_lock = True
                lines.append(
                    f"  {enc} @{delta:+d} n={len(names)} eg={sorted(names)[:8]}"
                )
            elif len(names) >= 3:
                lines.append(
                    f"  weak {enc} @{delta:+d} n={len(names)} eg={sorted(names)[:6]}"
                )
    if not any_lock:
        lines.append("  (no ≥6-player lock)")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-50:]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
