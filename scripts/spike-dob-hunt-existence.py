#!/usr/bin/env python3
"""Count whether each DOB encoding exists at all; pair with DOUBLE-UID only."""

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
    (ROOT / "tmp" / "fm-spike" / "dob-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-hunt-existence.txt"
MAX_HITS = 200
NEAR = 16384


def stream_blocks(path: Path):
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf." and head[25] == 3
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            reader.close()


def encodings(dob_s: str) -> dict[str, bytes]:
    y, m, d = map(int, dob_s.split("-"))
    dob = date(y, m, d)
    y1900 = y - 1900
    days = (dob - date(1900, 1, 1)).days
    return {
        "days_y1900": struct.pack("<I", days),
        "dmy": struct.pack("<BBH", d, m, y),
        "ymd": struct.pack("<HBB", y, m, d),
        "y1900_m_d": bytes([y1900, m, d]),
        "bits": struct.pack("<H", (y1900 << 9) | (m << 5) | d),
        "year_u16": struct.pack("<H", y),
    }


def main() -> None:
    labels: dict[bytes, list[tuple[str, str]]] = defaultdict(list)
    for p in PLAYERS:
        name = p["name"]
        uid = int(p["uid"]) & 0xFFFFFFFF
        labels[struct.pack("<II", uid, uid)].append((name, "double"))
        for kind, pat in encodings(p["dob"]).items():
            labels[pat].append((name, kind))

    hits: dict[bytes, list[int]] = {pat: [] for pat in labels}
    overlap = max(len(p) for p in hits) + 8
    carry = b""
    abs_base = 0
    print(f"patterns={len(hits)} streaming…", flush=True)
    for block in stream_blocks(SAVE):
        data = carry + block
        for pat, bucket in hits.items():
            if len(bucket) >= MAX_HITS:
                continue
            start = 0
            while len(bucket) < MAX_HITS:
                i = data.find(pat, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                if bucket and bucket[-1] == abs_off:
                    start = i + 1
                    continue
                bucket.append(abs_off)
                start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]
    print(f"done decomp≈{abs_base/1e9:.2f}GB", flush=True)

    double_offs: dict[str, list[int]] = defaultdict(list)
    dob_offs: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for pat, abs_list in hits.items():
        for name, kind in labels[pat]:
            if kind == "double":
                double_offs[name].extend(abs_list)
            else:
                dob_offs[name][kind].extend(abs_list)

    lines = [f"decompBytes≈{abs_base}", ""]
    lines.append("## hit counts per player/encoding (cap {})".format(MAX_HITS))
    for p in PLAYERS:
        name = p["name"]
        parts = [f"double={len(double_offs.get(name, []))}"]
        for kind in ("days_y1900", "dmy", "ymd", "y1900_m_d", "bits", "year_u16"):
            parts.append(f"{kind}={len(dob_offs.get(name, {}).get(kind, []))}")
        lines.append(f"  {name}: " + " ".join(parts))

    lines.append("\n## double→DOB deltas (|d|<=16384), require encoding to exist")
    for kind in ("days_y1900", "dmy", "ymd", "y1900_m_d", "bits"):
        delta_players: dict[int, set[str]] = defaultdict(set)
        for p in PLAYERS:
            name = p["name"]
            dabs_list = dob_offs.get(name, {}).get(kind, [])
            uabs_list = double_offs.get(name, [])
            if not dabs_list or not uabs_list:
                continue
            for dabs in dabs_list:
                best = None
                for uabs in uabs_list:
                    delta = dabs - uabs
                    if abs(delta) <= NEAR and (best is None or abs(delta) < abs(best)):
                        best = delta
                if best is not None:
                    delta_players[best].add(name)
        scored = sorted(((len(ns), d) for d, ns in delta_players.items()), reverse=True)
        lines.append(f"\n### {kind}")
        if not scored:
            lines.append("  (none)")
            continue
        for n, d in scored[:12]:
            lines.append(f"  delta={d:+d} players={n} {sorted(delta_players[d])[:8]}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
