#!/usr/bin/env python3
"""
Hunt DOB encodings NEAR the person double-UID / CA / personality pack.

Prior mark+days sites are real but unlinked. This spike asks whether a second
copy (or alternate encoding) sits on the person record we already resolve.
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
EXTRACT = ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json"
OUT = ROOT / "tmp" / "fm-spike" / "dob-near-person.txt"
MARK = bytes.fromhex("01006c07")
EPOCH = date(1900, 1, 1)
GAME = date(2039, 7, 1)
PERSON_HEAD = 512 * 1024 * 1024
RADIUS = 4096


def doubles(mm: mmap.mmap, uid: int) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(mm), PERSON_HEAD)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < 16:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def best_double(mm: mmap.mmap, uid: int) -> int | None:
    ds = doubles(mm, uid)
    if not ds:
        return None

    def score(dab: int) -> int:
        blob = bytes(mm[dab : dab + 160])
        s = 0
        if b"\x01\x01\x01" in blob[8:120]:
            s += 5
        if MARK in blob:
            s += 3
        if len(blob) >= 35:
            pi = struct.unpack_from("<I", blob, 31)[0]
            if 0 < pi < 200_000:
                s += 4
        return s

    return sorted(ds, key=lambda d: (-score(d), d))[0]


def packed_fm_u16(dob: date) -> int:
    """Classic SI packed date: day + month*32 + (year-1900)*512."""
    return dob.day + (dob.month << 5) + ((dob.year - 1900) << 9)


def encodings(dob: date, age: int) -> dict[str, bytes]:
    days = (dob - EPOCH).days
    return {
        "days_u32": struct.pack("<I", days),
        "days_u16": struct.pack("<H", days & 0xFFFF),
        "days_i32": struct.pack("<i", days),
        "ymd_u8": bytes([dob.year - 1900, dob.month, dob.day]),
        "dmy_u8": bytes([dob.day, dob.month, dob.year - 1900]),
        "ymd_u16y": struct.pack("<HBB", dob.year, dob.month, dob.day),
        "packed_u16": struct.pack("<H", packed_fm_u16(dob)),
        "year_u16": struct.pack("<H", dob.year),
        "year_u8": bytes([dob.year - 1900]),
        "age_u8": bytes([age]),
        "age_u16": struct.pack("<H", age),
        "ole_double": struct.pack("<d", float(days)),
        "days_f32": struct.pack("<f", float(days)),
    }


def main() -> None:
    lines: list[str] = []
    extract_by_uid: dict[int, dict] = {}
    if EXTRACT.exists():
        body = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
        for p in body.get("players") or []:
            if p.get("uid") is not None:
                extract_by_uid[int(p["uid"])] = p

    # Consensus: encoding hits at shared relative offset from dab / pack / card
    consensus: dict[str, Counter[int]] = defaultdict(Counter)
    anchors = ("dab", "pack", "card")

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                dob = date(*map(int, p["dob"].split("-")))
                age = int(p["age"])
                uid = int(p["uid"])
                dab = best_double(mm, uid)
                ex = extract_by_uid.get(uid, {})
                meta = ex.get("extractMeta") or ex
                pack = meta.get("personalityPackAbs") or ex.get("personalityPackAbs")
                card = meta.get("cardAbs") or ex.get("cardAbs") or meta.get("caCardAbs")
                centers = {
                    "dab": dab,
                    "pack": pack,
                    "card": card,
                }
                encs = encodings(dob, age)
                lines.append(f"## {p['name']} dab={dab} pack={pack} card={card}")
                for aname, center in centers.items():
                    if center is None:
                        continue
                    lo = max(0, int(center) - RADIUS)
                    hi = min(len(mm), int(center) + RADIUS)
                    window = bytes(mm[lo:hi])
                    for ename, pat in encs.items():
                        if len(pat) > len(window):
                            continue
                        start = 0
                        hits_rel = []
                        while True:
                            j = window.find(pat, start)
                            if j < 0:
                                break
                            rel = lo + j - int(center)
                            hits_rel.append(rel)
                            consensus[f"{aname}:{ename}"][rel] += 1
                            start = j + 1
                            if len(hits_rel) >= 8:
                                break
                        if hits_rel:
                            lines.append(
                                f"  {aname}/{ename}: rel={hits_rel[:8]}"
                            )

                # Also try days ±1..3 (birthday boundary / leap quirks)
                days = (dob - EPOCH).days
                if dab is not None:
                    lo = max(0, dab - RADIUS)
                    hi = min(len(mm), dab + RADIUS)
                    window = bytes(mm[lo:hi])
                    near_days = []
                    for delta in range(-3, 4):
                        pat = struct.pack("<I", days + delta)
                        j = window.find(pat)
                        if j >= 0:
                            near_days.append((delta, lo + j - dab))
                    if near_days:
                        lines.append(f"  dab/days±3: {near_days}")

            lines.append("\n## CONSENSUS shared rel (≥10/25)")
            for key, ctr in sorted(consensus.items()):
                top = [(rel, n) for rel, n in ctr.most_common(8) if n >= 8]
                if top:
                    lines.append(f"  {key}: {top}")

            lines.append("\n## CONSENSUS top even if weak (≥5)")
            for key, ctr in sorted(consensus.items()):
                top = [(rel, n) for rel, n in ctr.most_common(5) if n >= 5]
                if top:
                    lines.append(f"  {key}: {top}")

            # Dump dab±64 hex for Seimen / Müller / Sangaré (young) for manual eye
            lines.append("\n## dab±96 hex dumps (sample)")
            for name in ("Dennis Seimen", "Robert Müller", "Désiré Sangaré", "Jannis Mandelkow"):
                p = next(x for x in PLAYERS if x["name"] == name)
                dab = best_double(mm, int(p["uid"]))
                if dab is None:
                    continue
                lo = max(0, dab - 96)
                hi = min(len(mm), dab + 96)
                blob = bytes(mm[lo:hi])
                lines.append(f"  {name} @{dab}")
                for i in range(0, len(blob), 16):
                    chunk = blob[i : i + 16]
                    rel = lo + i - dab
                    lines.append(
                        f"    {rel:+5d} {chunk.hex(' ')}"
                    )

        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
