#!/usr/bin/env python3
"""Single-pass stream: shared UID↔DOB distance consensus across screenshot players."""

from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "dob-hunt-players.json").read_text(encoding="utf-8")
)
OUT = ROOT / "tmp" / "fm-spike" / "dob-hunt-stream.txt"
MAX_HITS = 60
NEAR = 8192

KINDS = (
    "days_y1900",
    "days_excel",
    "dmy",
    "ymd",
    "y1900_m_d",
    "d_m_y1900",
    "bits",
    "tag02_days",
)


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
    days_excel = (dob - date(1899, 12, 30)).days
    return {
        "days_y1900": struct.pack("<I", days),
        "days_excel": struct.pack("<I", days_excel),
        "dmy": struct.pack("<BBH", d, m, y),
        "ymd": struct.pack("<HBB", y, m, d),
        "y1900_m_d": bytes([y1900, m, d]),
        "d_m_y1900": bytes([d, m, y1900]),
        "bits": struct.pack("<H", (y1900 << 9) | (m << 5) | d),
        "tag02_days": b"\x02" + struct.pack("<I", days),
    }


def main() -> None:
    # pat bytes -> list of (player_name, kind|'uid')
    labels: dict[bytes, list[tuple[str, str]]] = defaultdict(list)
    for p in PLAYERS:
        name = p["name"]
        labels[struct.pack("<I", int(p["uid"]) & 0xFFFFFFFF)].append((name, "uid"))
        for kind, pat in encodings(p["dob"]).items():
            labels[pat].append((name, kind))

    hits: dict[bytes, list[int]] = {pat: [] for pat in labels}
    overlap = max(len(p) for p in hits) + 8
    carry = b""
    abs_base = 0
    print(f"streaming {SAVE.name} ({len(hits)} unique patterns)…", flush=True)

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

    print(f"streamed ~{abs_base/1e9:.2f} GB decompressed", flush=True)

    # Expand to per-player lists
    uid_offs: dict[str, list[int]] = defaultdict(list)
    dob_offs: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for pat, abs_list in hits.items():
        for name, kind in labels[pat]:
            if kind == "uid":
                uid_offs[name].extend(abs_list)
            else:
                dob_offs[name][kind].extend(abs_list)

    lines = [
        f"save={SAVE.name}",
        f"players={len(PLAYERS)}",
        f"near={NEAR}",
        f"decompBytes≈{abs_base}",
        "",
        "## nearest UID→DOB delta consensus",
    ]

    for kind in KINDS:
        delta_players: dict[int, set[str]] = defaultdict(set)
        delta_hits: Counter[int] = Counter()
        for p in PLAYERS:
            name = p["name"]
            uoffs = uid_offs.get(name, [])
            doffs = dob_offs.get(name, {}).get(kind, [])
            if not uoffs or not doffs:
                continue
            for dabs in doffs:
                best = None
                for uabs in uoffs:
                    delta = dabs - uabs
                    if abs(delta) <= NEAR and (best is None or abs(delta) < abs(best)):
                        best = delta
                if best is not None:
                    delta_hits[best] += 1
                    delta_players[best].add(name)

        scored = sorted(
            ((len(delta_players[d]), delta_hits[d], d) for d in delta_players),
            reverse=True,
        )
        lines.append(f"\n### {kind}")
        if not scored:
            lines.append("  (no co-located hits)")
            continue
        for n_players, n_hit, d in scored[:15]:
            names = sorted(delta_players[d])
            lines.append(
                f"  delta={d:+d} players={n_players} hits={n_hit} e.g. {names[:10]}"
            )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
