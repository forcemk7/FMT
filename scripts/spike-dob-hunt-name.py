#!/usr/bin/env python3
"""Hunt compact DOB near name-colocated UID records."""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "dob-hunt-players.json").read_text(encoding="utf-8")
)
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
OUT = ROOT / "tmp" / "fm-spike" / "dob-hunt-name.txt"
PERSON_HEAD = 512 * 1024 * 1024


def find_name_records(buf: mmap.mmap, uid: int, name: str, want: int = 6) -> list[int]:
    """Abs offsets of lp32(full name) preceded within 160 bytes by uid."""
    name_b = name.encode("utf-8")
    needle = struct.pack("<I", len(name_b)) + name_b
    uid_b = struct.pack("<I", uid & 0xFFFFFFFF)
    found: list[int] = []
    end = min(len(buf), PERSON_HEAD)
    start = 0
    while len(found) < want:
        i = buf.find(needle, start, end)
        if i < 0:
            break
        behind = bytes(buf[max(0, i - 160) : i])
        if uid_b in behind:
            found.append(i)
        start = i + 1
    return found


def pack_variants(y: int, m: int, d: int) -> dict[str, bytes]:
    from datetime import date as _date

    y1900 = y - 1900
    days = (_date(y, m, d) - _date(1900, 1, 1)).days
    return {
        "dmy_u8u8u16": struct.pack("<BBH", d, m, y),
        "ymd_u16u8u8": struct.pack("<HBB", y, m, d),
        "mdy_u8u8u16": struct.pack("<BBH", m, d, y),
        "ydm_u16u8u8": struct.pack("<HBB", y, d, m),
        "d_m_y1900": bytes([d, m, y1900]),
        "y1900_m_d": bytes([y1900, m, d]),
        "m_d_y1900": bytes([m, d, y1900]),
        "bits_y9m4d5": struct.pack("<H", (y1900 << 9) | (m << 5) | d),
        "bits_be": struct.pack(">H", (y1900 << 9) | (m << 5) | d),
        "year_u16": struct.pack("<H", y),
        "days_y1900": struct.pack("<I", days),
        "tag02_days": b"\x02" + struct.pack("<I", days),
    }


def main() -> None:
    lines: list[str] = []
    # pattern -> list of (rel_to_name, player)
    hits_by_pat: dict[str, list[tuple[int, str]]] = defaultdict(list)

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                uid = int(p["uid"])
                y, m, d = map(int, p["dob"].split("-"))
                names = find_name_records(mm, uid, p["name"])
                lines.append(f"## {p['name']} uid={uid} dob={p['dob']} nameHits={names[:4]}")
                if not names:
                    # try last-token name for multipart names
                    last = p["name"].split()[-1]
                    names = find_name_records(mm, uid, last)
                    lines.append(f"  fallback last='{last}' hits={names[:4]}")
                if not names:
                    continue
                name_abs = names[-1]  # prefer later (person directory tends late)
                lo = max(0, name_abs - 256)
                hi = min(len(mm), name_abs + 256)
                win = bytes(mm[lo:hi])
                rel0 = name_abs - lo
                for kind, pat in pack_variants(y, m, d).items():
                    start = 0
                    found_any = False
                    while True:
                        i = win.find(pat, start)
                        if i < 0:
                            break
                        rel = i - rel0
                        hits_by_pat[kind].append((rel, p["name"]))
                        lines.append(f"  {kind} @{rel}")
                        found_any = True
                        start = i + 1
                        if start > 0 and kind == "year_u16":
                            # year alone is noisy; keep a few
                            if sum(1 for _k, n in hits_by_pat[kind] if n == p["name"]) >= 4:
                                break
                    if kind != "year_u16" and not found_any:
                        pass
        finally:
            mm.close()

    lines.append("\n## SHARED rel-to-name offsets")
    for kind, rows in sorted(hits_by_pat.items()):
        by_off: dict[int, set[str]] = defaultdict(set)
        for rel, name in rows:
            by_off[rel].add(name)
        shared = {off: names for off, names in by_off.items() if len(names) >= 5}
        if shared:
            top = sorted(shared.items(), key=lambda kv: -len(kv[1]))[:10]
            lines.append(f"  {kind}: {[(off, len(names), sorted(list(names))[:6]) for off, names in top]}")
        else:
            # majority
            ctr = Counter(rel for rel, _ in rows)
            maj = [(off, n) for off, n in ctr.most_common(8) if n >= 4]
            if maj:
                lines.append(f"  {kind} majority: {maj}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
