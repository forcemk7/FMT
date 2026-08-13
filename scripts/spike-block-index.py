"""Deep-dive Seimen's promising 05 8c 0c block; hunt index-keyed attr tables."""

from __future__ import annotations

import json
import struct
from collections import Counter
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}
OUT = Path("tmp/fm-spike/seimen-block-and-index.txt")

# Promising Seimen marker hit (iid ~81 bytes before)
SEIMEN_MARKER_ABS = 149201119
# Double-UID record abs
DOUBLE = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}
INDEX = {
    "Dennis Seimen": 0x06FE,  # 1790
    "Patrick Bandeira": 0x04AE,  # 1198
    "Robert Müller": 0x04D1,  # 1233
}
INTERNAL = {
    "Dennis Seimen": 0x0001BB6D,
    "Patrick Bandeira": 0x0005191C,
    "Robert Müller": 0x00059603,
}


def extract(abs_target: int, length: int = 512, before: int = 0) -> bytes:
    start = abs_target - before
    end = abs_target + length
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        buf = bytearray()
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
                    lo = max(0, start - chunk_start)
                    hi = min(len(data), end - chunk_start)
                    already = len(buf)
                    want_from = start + already
                    lo2 = max(lo, want_from - chunk_start)
                    if lo2 < hi:
                        buf.extend(data[lo2:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= before + length:
                    break
                if abs_base > end + 8 * 1024 * 1024:
                    break
        finally:
            reader.close()
    return bytes(buf)


def stream_blocks():
    with SAVE.open("rb") as f:
        f.seek(26)
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


def find_pattern(pat: bytes, limit: int = 30) -> list[int]:
    hits = []
    abs_base = 0
    carry = b""
    ov = max(64, len(pat))
    for block in stream_blocks():
        data = carry + block
        start = 0
        while len(hits) < limit:
            i = data.find(pat, start)
            if i < 0:
                break
            abs_off = abs_base - len(carry) + i
            if not hits or hits[-1] != abs_off:
                hits.append(abs_off)
            start = i + 1
        abs_base += len(block)
        carry = data[-ov:]
        if len(hits) >= limit:
            break
    return hits


def map_blob_to_attrs(blob: bytes, p: dict, label: str, lines: list[str]) -> None:
    flat = []
    for g, attrs in p["attributes"].items():
        for k, v in attrs.items():
            flat.append((f"{g}.{k}", v))
    lines.append(f"\n-- map {label} ({len(blob)} bytes) --")
    # For each offset, if byte matches exactly one distinctive attr, note it
    by_val: dict[int, list[str]] = {}
    for name, v in flat:
        by_val.setdefault(v, []).append(name)

    # Try: treat contiguous runs of 1..20 as candidates; score vs attr multiset
    need = Counter(v for _, v in flat)
    best = []
    for i in range(len(blob)):
        for L in (20, 30, 40, 50, 60, 70, 80):
            if i + L > len(blob):
                break
            win = blob[i : i + L]
            # only consider windows that are mostly 1..20
            in_range = sum(1 for b in win if 1 <= b <= 20)
            if in_range < L * 0.7:
                continue
            have = Counter(win)
            covered = sum(min(have[v], c) for v, c in need.items())
            score = covered / sum(need.values())
            if score >= 0.85:
                best.append((score, covered, i, L, list(win)))
    best.sort(reverse=True)
    lines.append(f"  high multiset-cover windows (>=85%): n={len(best)}")
    for score, covered, i, L, win in best[:8]:
        lines.append(f"  score={score:.2f} cov={covered}/{sum(need.values())} @{i} L={L}")
        lines.append(f"    {win}")

    # GK/mental ordered with gap
    groups = []
    if "goalkeeping" in p["attributes"]:
        groups.append(("gk", list(p["attributes"]["goalkeeping"].values())))
    groups.append(
        (
            "mental",
            [
                p["attributes"]["mental"][k]
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
            ],
        )
    )
    groups.append(
        (
            "phys",
            [
                p["attributes"]["physical"][k]
                for k in (
                    "acceleration",
                    "agility",
                    "balance",
                    "jumpingReach",
                    "naturalFitness",
                    "pace",
                    "stamina",
                    "strength",
                )
            ],
        )
    )

    def ordered(blob: bytes, vals: list[int], max_gap: int) -> list[list[int]] | None:
        paths = []

        def rec(vi, pos, path):
            if len(paths) >= 3:
                return
            if vi == len(vals):
                paths.append(path[:])
                return
            if vi == 0:
                s = 0
                while len(paths) < 3:
                    j = blob.find(bytes([vals[0]]), s)
                    if j < 0:
                        break
                    rec(1, j + 1, [j])
                    s = j + 1
                return
            for j in range(pos, min(len(blob), pos + max_gap + 1)):
                if blob[j] == vals[vi]:
                    path.append(j)
                    rec(vi + 1, j + 1, path)
                    path.pop()

        rec(0, 0, [])
        return paths

    for gname, vals in groups:
        for gap in (0, 1, 2, 3, 4):
            paths = ordered(blob, vals, gap)
            if paths:
                lines.append(f"  ordered {gname} gap<={gap}: {paths[0]}")
                break
        # also *5
        vals5 = [v * 5 for v in vals]
        for gap in (0, 1, 2):
            paths = ordered(blob, vals5, gap)
            if paths:
                lines.append(f"  ordered {gname}*5 gap<={gap}: {paths[0]}")
                break


def main() -> None:
    lines: list[str] = []
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # 1) Wide dump around Seimen marker
    blob = extract(SEIMEN_MARKER_ABS, length=400, before=120)
    lines.append(f"Seimen marker neighborhood len={len(blob)}")
    lines.append(f"hex before+after:\n{blob.hex(' ')}")
    lines.append(f"u8: {list(blob)}")
    # marker at offset 120 in this blob
    map_blob_to_attrs(blob[120:], PLAYERS["Dennis Seimen"], "post-marker", lines)
    map_blob_to_attrs(blob, PLAYERS["Dennis Seimen"], "full-neighborhood", lines)

    # Identify the double-id before the marker
    pre = blob[:120]
    # look for repeated 4-byte patterns
    for i in range(len(pre) - 8):
        if pre[i : i + 4] == pre[i + 4 : i + 8] and pre[i : i + 4] != b"\x00\x00\x00\x00":
            uidish = struct.unpack_from("<I", pre, i)[0]
            lines.append(f"  double-4byte @{i}: {pre[i:i+4].hex(' ')} = {uidish}")

    # 2) Hunt outfield-style blocks: 01 02 00 01 05 0c ?? 05 8c 0c near each UID
    lines.append("\n\n======== UID near outfield-style attr header ========")
    header_variants = [
        bytes.fromhex("01020001050c"),
        bytes.fromhex("01010001050c"),
        bytes.fromhex("01000001050c"),
    ]
    for name, abs_d in DOUBLE.items():
        # search whole file is heavy; instead scan for UID then header in +/-512 of each UID hit
        pass

    # Single pass: UID then header within 128, or header then UID
    uid_header_hits = {n: [] for n in PLAYERS}
    abs_base = 0
    carry = b""
    HEADER = bytes.fromhex("050c")  # short prefix before 058c0c variants
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
                for name, p in PLAYERS.items():
                    if len(uid_header_hits[name]) >= 8:
                        continue
                    uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
                    # Prefer double UID
                    for needle, tag in ((uid + uid, "double"), (uid, "single")):
                        start = 0
                        while len(uid_header_hits[name]) < 8:
                            i = data.find(needle, start)
                            if i < 0:
                                break
                            abs_off = abs_base - len(carry) + i
                            win = data[i : i + 256]
                            # find 05 8c 0c in following 200
                            j = win.find(bytes.fromhex("058c0c"))
                            # also find classic prelude 01 ?? 00 01 05 0c
                            prelude = -1
                            for k in range(min(120, len(win) - 6)):
                                if (
                                    win[k] == 1
                                    and win[k + 2] == 0
                                    and win[k + 3] == 1
                                    and win[k + 4] == 5
                                    and win[k + 5] == 0x0C
                                ):
                                    prelude = k
                                    break
                            if j >= 0 or prelude >= 0:
                                uid_header_hits[name].append(
                                    {
                                        "abs": abs_off,
                                        "tag": tag,
                                        "marker_rel": j if j >= 0 else None,
                                        "prelude_rel": prelude if prelude >= 0 else None,
                                        "blob": win[:200],
                                    }
                                )
                            start = i + 1
                abs_base += len(block)
                carry = data[-300:]
        finally:
            reader.close()

    for name, rows in uid_header_hits.items():
        lines.append(f"\n## {name} uid→marker/prelude hits={len(rows)}")
        for r in rows:
            lines.append(
                f"  abs={r['abs']} tag={r['tag']} marker={r['marker_rel']} "
                f"prelude={r['prelude_rel']}"
            )
            lines.append(f"    hex: {r['blob'][:120].hex(' ')}")
            if r["marker_rel"] is not None:
                post = r["blob"][r["marker_rel"] :]
                map_blob_to_attrs(post, PLAYERS[name], f"{name}@marker", lines)

    # 3) Index-keyed table hunt
    # For record sizes 32..256 step 4, find base such that:
    #   bytes at base+idx_b*S and base+idx_m*S match lea 14 vs 17 at SAME relative offset
    lines.append("\n\n======== index-table probe (sampling large pools) ========")
    # Strategy: find all occurrences of Band idx as u16 LE (ae 04) that are followed
    # within S bytes by Mull's pattern — too vague.
    # Better: extract a big contiguous DB slice and test.
    # Use double-UID person indices: pick a 4MB window from ~career DB mid and test alignments.

    # Grab 8MB starting from Seimen double-UID - 1MB as candidate table region
    # (attributes often in same DB section as player records)
    sample_start = 150_000_000
    sample = extract(sample_start, length=4_000_000, before=0)
    lines.append(f"sample@{sample_start} len={len(sample)}")

    ib, im, is_ = INDEX["Patrick Bandeira"], INDEX["Robert Müller"], INDEX["Dennis Seimen"]
    lea_b, lea_m = 14, 17
    nf_b, nf_m = 16, 9
    det = 16
    otb_s = 1

    found_sizes = []
    for S in range(32, 257, 4):
        # Need sample large enough for index 1790
        need = (is_ + 1) * S
        if need > len(sample):
            continue
        # Try every base offset 0..S-1 within first S bytes such that all indices land in sample
        for base in range(S):
            # max index offset
            if base + is_ * S + S > len(sample):
                continue
            # Check relative offsets 0..S-1 for lea match and nf match simultaneously OR separately
            lea_offs = []
            nf_offs = []
            det_offs = []
            for off in range(S):
                bb = sample[base + ib * S + off]
                mm = sample[base + im * S + off]
                ss = sample[base + is_ * S + off]
                if bb == lea_b and mm == lea_m:
                    lea_offs.append(off)
                if bb == nf_b and mm == nf_m:
                    nf_offs.append(off)
                if bb == det and mm == det:
                    det_offs.append(off)
            if lea_offs and nf_offs:
                # also check Seimen otb if off available
                found_sizes.append((S, base, lea_offs[:5], nf_offs[:5], det_offs[:5]))
        if len(found_sizes) >= 20:
            break

    lines.append(f"index-table candidates with BOTH lea+nf matches: n={len(found_sizes)}")
    for row in found_sizes[:15]:
        S, base, lea_offs, nf_offs, det_offs = row
        lines.append(
            f"  S={S} base={base} lea_offs={lea_offs} nf_offs={nf_offs} det_offs={det_offs}"
        )
        # dump those records
        if lea_offs:
            off = lea_offs[0]
            for name, idx in (
                ("Band", ib),
                ("Mull", im),
                ("Seim", is_),
            ):
                rec = sample[base + idx * S : base + idx * S + S]
                lines.append(f"    {name} rec: {list(rec)}")

    # Also try *5 in index table
    found5 = []
    for S in range(32, 257, 4):
        for base in range(min(S, 64)):  # limit base search for speed
            if base + is_ * S + S > len(sample):
                continue
            lea_offs = []
            nf_offs = []
            for off in range(S):
                bb = sample[base + ib * S + off]
                mm = sample[base + im * S + off]
                if bb == lea_b * 5 and mm == lea_m * 5:
                    lea_offs.append(off)
                if bb == nf_b * 5 and mm == nf_m * 5:
                    nf_offs.append(off)
            if lea_offs and nf_offs:
                found5.append((S, base, lea_offs[:3], nf_offs[:3]))
        if len(found5) >= 10:
            break
    lines.append(f"index-table *5 lea+nf candidates: n={len(found5)}")
    for row in found5[:10]:
        lines.append(f"  {row}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text[:10000])
    print(f"\n... wrote {OUT} ({len(text)} chars)")


if __name__ == "__main__":
    main()
