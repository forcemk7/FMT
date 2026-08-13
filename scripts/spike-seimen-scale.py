"""Dump Seimen UID neighborhood and test attr scale encodings (*1,*5,*10)."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
SEIMEN = next(
    p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
    if p["uid"] == 2000175080
)
OUT = Path("tmp/fm-spike/seimen-scale.txt")

UID = struct.pack("<I", 2000175080)
# Known interesting hit from prior pass
TARGET = 157471994

FLAT = []
NAMES = []
for group, attrs in SEIMEN["attributes"].items():
    for k, v in attrs.items():
        FLAT.append(v)
        NAMES.append(f"{group}.{k}")


def stream_until(abs_target: int, before: int = 64, after: int = 512) -> bytes:
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        need_start = abs_target - before
        need_end = abs_target + after
        buf = bytearray()
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                # append
                data = carry + block
                # if this chunk overlaps region of interest, keep it
                chunk_start = abs_base - len(carry)
                chunk_end = abs_base + len(block)
                if chunk_end > need_start and chunk_start < need_end:
                    # copy overlapping part
                    lo = max(0, need_start - chunk_start)
                    hi = min(len(data), need_end - chunk_start)
                    # Only append new bytes beyond what we already have relative to need_start
                    already = len(buf)
                    want_from = need_start + already
                    lo2 = max(lo, want_from - chunk_start)
                    if lo2 < hi:
                        buf.extend(data[lo2:hi])
                abs_base += len(block)
                carry = data[-64:]
                if abs_base >= need_end + 8 * 1024 * 1024:
                    break
                if len(buf) >= before + after:
                    break
        finally:
            reader.close()
    return bytes(buf)


def find_sequence(hay: bytes, vals: list[int], max_gap: int = 0) -> list[int]:
    """Find start indexes where vals appear with at most max_gap between consecutive."""
    if not vals:
        return []
    starts = []
    first = vals[0]
    i = 0
    while True:
        i = hay.find(bytes([first]), i)
        if i < 0:
            break
        pos = i
        ok = True
        for v in vals[1:]:
            # search in (pos+1 .. pos+1+max_gap)
            found = -1
            for g in range(1, max_gap + 2):
                j = pos + g
                if j < len(hay) and hay[j] == v:
                    found = j
                    break
            if found < 0:
                ok = False
                break
            pos = found
        if ok:
            starts.append(i)
        i += 1
    return starts


def main() -> None:
    lines = []
    blob = stream_until(TARGET, before=32, after=768)
    lines.append(f"dumped {len(blob)} bytes around abs={TARGET}")
    lines.append(blob.hex(" "))
    lines.append("")
    lines.append("as u8:")
    lines.append(str(list(blob)))

    # mark UID location in blob (should be around offset 32)
    uid_at = blob.find(UID)
    lines.append(f"\nUID at blob_off={uid_at}")

    for scale in (1, 5, 10):
        lines.append(f"\n==== scale x{scale} ====")
        scaled = [v * scale for v in FLAT]
        # skip if any > 255
        if any(v > 255 for v in scaled):
            lines.append("  skip (overflow)")
            continue
        # consecutive
        pat = bytes(scaled)
        idx = blob.find(pat)
        lines.append(f"  full flat consecutive: {idx}")

        # mental only consecutive
        mental = [SEIMEN["attributes"]["mental"][k] * scale for k in SEIMEN["attributes"]["mental"]]
        gk = [SEIMEN["attributes"]["goalkeeping"][k] * scale for k in SEIMEN["attributes"]["goalkeeping"]]
        phys = [SEIMEN["attributes"]["physical"][k] * scale for k in SEIMEN["attributes"]["physical"]]
        for label, vals in (("mental", mental), ("gk", gk), ("phys", phys)):
            for gap in (0, 1, 2, 3, 4):
                hits = find_sequence(blob, vals, max_gap=gap)
                if hits:
                    lines.append(f"  {label} gap<={gap}: offs={hits[:8]}")
                    # show context for first
                    o = hits[0]
                    lines.append(f"    ctx: {list(blob[max(0,o-8):o+len(vals)*(gap+1)+8])}")

        # distinctive subset consecutive
        subset = [
            SEIMEN["attributes"]["mental"]["flair"] * scale,
            SEIMEN["attributes"]["mental"]["determination"] * scale,
            SEIMEN["attributes"]["mental"]["leadership"] * scale,
            SEIMEN["attributes"]["mental"]["offTheBall"] * scale,
        ]
        for gap in (0, 1, 2, 4, 8):
            hits = find_sequence(blob, subset, max_gap=gap)
            if hits:
                lines.append(f"  flair,det,lea,otb gap<={gap}: {hits[:10]}")

        # also lea,det order etc
        subset2 = [
            SEIMEN["attributes"]["mental"]["determination"] * scale,
            SEIMEN["attributes"]["mental"]["leadership"] * scale,
        ]
        hits = find_sequence(blob, subset2, max_gap=0)
        lines.append(f"  det,lea consecutive: {hits[:20]}")
        hits = [i for i, b in enumerate(blob) if b == SEIMEN["attributes"]["mental"]["determination"] * scale]
        lines.append(f"  det*{scale} positions: {hits[:30]}")

    # Global search for mental*5 consecutive (unique!)
    mental5 = bytes(
        [
            SEIMEN["attributes"]["mental"][k] * 5
            for k in (
                "aggression",
                "anticipation",
                "bravery",
                "composure",
                "concentration",
                "decisions",
                "determination",
                "flair",
                "leadership",
                "offTheBall",
                "positioning",
                "teamwork",
                "vision",
                "workRate",
            )
        ]
    )
    lines.append(f"\nglobal mental*5 pat: {mental5.hex(' ')}")
    # scan whole file
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        found = []
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                start = 0
                while len(found) < 10:
                    i = data.find(mental5, start)
                    if i < 0:
                        break
                    abs_off = abs_base - len(carry) + i
                    found.append(abs_off)
                    start = i + 1
                abs_base += len(block)
                carry = data[-64:]
                if len(found) >= 10:
                    break
        finally:
            reader.close()
    lines.append(f"mental*5 global hits: {found}")

    # same for gk*5
    gk5 = bytes([v * 5 for v in SEIMEN["attributes"]["goalkeeping"].values()])
    lines.append(f"gk*5 pat: {gk5.hex(' ')}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text[:8000])
    print("\n... wrote", OUT)


if __name__ == "__main__":
    main()
