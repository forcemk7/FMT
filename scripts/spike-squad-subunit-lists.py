#!/usr/bin/env python3
"""Find packed job-id squad lists containing Ermin (II) / James (U19)."""

from __future__ import annotations

import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-subunit-lists.txt")

JOB_ERMIN = 237871
JOB_JAMES = 439758
JOB_SANG = 540180
JOB_SEIMEN = 113517
TID_FT = 193616


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


def stream_hits(job: int) -> list[int]:
    pat = struct.pack("<I", job)
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
                while True:
                    j = data.find(pat, start)
                    if j < 0:
                        break
                    hits.append(chunk_start + j)
                    start = j + 1
                abs_base += len(block)
                carry = data[-4:]
        finally:
            reader.close()
    return hits


def looks_like_squad_list(win: bytes, job_rel: int) -> tuple[bool, int, list[int]]:
    """Walk backward/forward from a job id; require a run of ≥12 packed job-ish u32s."""
    # find start of run containing job_rel
    start = job_rel
    while start >= 4:
        v = struct.unpack_from("<I", win, start - 4)[0]
        if 100_000 <= v <= 800_000:
            start -= 4
        else:
            break
    vals = []
    i = start
    while i + 4 <= len(win) and len(vals) < 80:
        v = struct.unpack_from("<I", win, i)[0]
        if 100_000 <= v <= 800_000:
            vals.append(v)
            i += 4
        else:
            break
    ok = len(vals) >= 12
    return ok, start, vals


def main() -> None:
    lines: list[str] = []

    def out(s: str = "") -> None:
        log(s)
        lines.append(s)

    targets = {
        "Ermin/II": JOB_ERMIN,
        "James/U19": JOB_JAMES,
        "Sangaré/U19prev": JOB_SANG,
    }

    for label, job in targets.items():
        out(f"\n######## {label} job={job} ########")
        hits = stream_hits(job)
        out(f"hits: {len(hits)}")
        squad_sites = []
        for h in hits:
            win = extract(h, 512, before=256)
            base = h - 256
            job_rel = 256
            ok, start, vals = looks_like_squad_list(win, job_rel)
            if not ok:
                continue
            # header clues
            hdr = win[max(0, start - 64) : start]
            has_64ff = b"\x64\xff" in hdr
            has_tid_ft = struct.pack("<I", TID_FT) in hdr
            has_seimen = JOB_SEIMEN in vals
            has_ermin = JOB_ERMIN in vals
            has_james = JOB_JAMES in vals
            has_sang = JOB_SANG in vals
            # possible team id in header (100k-300k)
            tids = []
            for i in range(0, len(hdr) - 3):
                v = struct.unpack_from("<I", hdr, i)[0]
                if 100_000 <= v <= 300_000:
                    tids.append(v)
            squad_sites.append(
                {
                    "abs": base + start,
                    "n": len(vals),
                    "has_64ff": has_64ff,
                    "has_tid_ft": has_tid_ft,
                    "has_seimen": has_seimen,
                    "flags": (
                        ("Ermin" if has_ermin else ""),
                        ("James" if has_james else ""),
                        ("Sang" if has_sang else ""),
                        ("Seimen" if has_seimen else ""),
                    ),
                    "tids": list(dict.fromkeys(tids))[:6],
                    "vals": vals,
                    "hit": h,
                }
            )

        # prefer sites without Seimen (not FT), with 64ff framing, sensible size 12-45
        scored = []
        for s in squad_sites:
            score = 0
            if s["has_64ff"]:
                score += 5
            if not s["has_seimen"]:
                score += 3
            if 15 <= s["n"] <= 40:
                score += 3
            if s["has_tid_ft"]:
                score -= 5
            scored.append((score, s))
        scored.sort(key=lambda t: -t[0])

        out(f"squad-like sites: {len(squad_sites)}; top:")
        seen = set()
        shown = 0
        for score, s in scored:
            key = s["abs"] // 64
            if key in seen:
                continue
            seen.add(key)
            out(
                f"  score={score} list@{s['abs']} n={s['n']} "
                f"64ff={s['has_64ff']} tidFT={s['has_tid_ft']} "
                f"flags={ [x for x in s['flags'] if x] } tids={s['tids']}"
            )
            # dump header+start
            win = extract(s["abs"], 256, before=64)
            for row in dump(win, s["abs"] - 64, 192):
                out(row)
            out(f"  jobs: {s['vals'][:40]}")
            shown += 1
            if shown >= 6:
                break

    OUT.write_text("\n".join(lines), encoding="utf-8")
    out(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
