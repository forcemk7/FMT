#!/usr/bin/env python3
"""Hunt squad lists keyed by internal job/record IDs (not UniqueIDs)."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-jobid-roster-hunt.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

# From person-record ASSOC: tag XX 02 <jobId> 02 <uid>
JOB = {
    "Dennis Seimen": 113517,
    "Patrick Bandeira": 334108,
    "Robert Müller": 366083,
    "Ermin Maric (II)": 237871,
    "James Solo (U19)": 439758,
    "Sangaré (U19_prev)": 540180,
}
JOB_BY = {v: k for k, v in JOB.items()}
FT_JOBS = [113517, 334108, 366083]
UID_BY_NAME = {p["name"]: int(p["uid"]) for p in FIXTURE}
UID_BY_NAME.update(
    {
        "Ermin Maric (II)": 2002138129,
        "James Solo (U19)": 2002332550,
        "Sangaré (U19_prev)": 2002423570,
    }
)
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


def resolve_job_via_uid_nearby(job_ids: list[int]) -> dict[int, str]:
    """Best-effort: names from JOB map only for now."""
    return {j: JOB_BY.get(j, "") for j in job_ids}


def main() -> None:
    lines: list[str] = []

    def out(s: str = "") -> None:
        log(s)
        lines.append(s)

    out("job IDs:")
    for n, j in JOB.items():
        out(f"  {n}: {j} ({j:#x})")

    pats = {j: struct.pack("<I", j) for j in JOB.values()}
    hits: dict[int, list[int]] = {j: [] for j in JOB.values()}

    out("\npass1: stream all job-id hits…")
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
                for j, pat in pats.items():
                    start = 0
                    while True:
                        i = data.find(pat, start)
                        if i < 0:
                            break
                        hits[j].append(chunk_start + i)
                        start = i + 1
                abs_base += len(block)
                carry = data[-8:]
                if abs_base % (128 * 1024 * 1024) < 8 * 1024 * 1024:
                    log(f"  scanned {abs_base/1e6:.0f}MB")
        finally:
            reader.close()

    for j, offs in hits.items():
        out(f"  {JOB_BY[j]}: {len(offs)} hits")

    # Co-occurrence clusters of FT job ids within 4KB
    out("\npass2: FT job-id co-occurrence (4KB)…")
    events = []
    for j in FT_JOBS:
        for o in hits[j]:
            events.append((o, j))
    events.sort()
    window = 4096
    clusters = []
    i = 0
    while i < len(events):
        j = i
        set_j = {events[i][1]}
        while j + 1 < len(events) and events[j + 1][0] - events[i][0] <= window:
            j += 1
            set_j.add(events[j][1])
        if len(set_j) >= 2:
            clusters.append(
                {
                    "start": events[i][0],
                    "end": events[j][0],
                    "jobs": sorted(set_j),
                    "n": len(set_j),
                }
            )
        i += 1
        while i < len(events) and events[i][0] == events[i - 1][0]:
            i += 1

    # unique by start bucket
    seen = set()
    best = []
    for c in sorted(clusters, key=lambda c: (-c["n"], c["end"] - c["start"])):
        key = (c["start"] // 512, tuple(c["jobs"]))
        if key in seen:
            continue
        seen.add(key)
        best.append(c)
    for c in best[:25]:
        names = [JOB_BY[j] for j in c["jobs"]]
        out(
            f"  @{c['start']}..{c['end']} span={c['end']-c['start']} "
            f"n={c['n']} {names}"
        )

    # Dig best clusters that have all 3 FT jobs
    full = [c for c in best if c["n"] >= 3]
    out(f"\nfull FT job clusters: {len(full)}")
    for c in full[:8]:
        abs_ = c["start"]
        out(f"\n######## FULL FT cluster @{abs_} ########")
        win = extract(abs_, c["end"] - c["start"] + 2048, before=256)
        base = abs_ - 256
        # also check subunit jobs/TID present
        present = []
        for name, jid in JOB.items():
            if struct.pack("<I", jid) in win:
                present.append(name)
        if struct.pack("<I", TID_FT) in win:
            present.append("TID_FT")
        out(f"present: {present}")
        for row in dump(win[:512], base, 512):
            out(row)

        # extract all job-range u32s that look packed (100000-700000)
        run = []
        runs = []
        for i in range(0, len(win) - 3):
            v = struct.unpack_from("<I", win, i)[0]
            if 100_000 <= v <= 700_000:
                if not run or i - run[-1][0] <= 24:
                    run.append((i, v))
                else:
                    if len(run) >= 8:
                        runs.append(run)
                    run = [(i, v)]
            else:
                if len(run) >= 8:
                    runs.append(run)
                run = []
        if len(run) >= 8:
            runs.append(run)
        out(f"job-like runs (>=8): {len(runs)}")
        for run in runs[:6]:
            vals = list(dict.fromkeys(v for _, v in run))
            flags = [JOB_BY[v] for v in vals if v in JOB_BY]
            out(f"  @{base+run[0][0]} n={len(vals)} flags={flags or '-'}")
            if flags:
                for i, v in enumerate(vals[:40]):
                    mark = f" <<{JOB_BY[v]}" if v in JOB_BY else ""
                    out(f"    [{i:02d}] {v}{mark}")

    # Mixed: FT jobs with Reserve / U19 nearby?
    out("\npass3: FT + subunit job proximity…")
    sub_events = []
    for j in FT_JOBS + [237871, 439758, 540180]:
        for o in hits[j][:200]:
            sub_events.append((o, j))
    sub_events.sort()
    mixed = []
    i = 0
    while i < len(sub_events):
        j = i
        set_j = {sub_events[i][1]}
        while j + 1 < len(sub_events) and sub_events[j + 1][0] - sub_events[i][0] <= 8192:
            j += 1
            set_j.add(sub_events[j][1])
        has_ft = len(set_j & set(FT_JOBS)) >= 2
        has_sub = bool(set_j & {237871, 439758, 540180})
        if has_ft and has_sub:
            mixed.append((sub_events[i][0], sub_events[j][0], sorted(set_j)))
        i += 1
        while i < len(sub_events) and sub_events[i][0] == sub_events[i - 1][0]:
            i += 1
    seen_m = set()
    shown = 0
    for a, b, jobs in mixed:
        key = (a // 1024, tuple(jobs))
        if key in seen_m:
            continue
        seen_m.add(key)
        out(f"  @{a}..{b} span={b-a} {[JOB_BY[x] for x in jobs]}")
        shown += 1
        if shown >= 20:
            break

    OUT.write_text("\n".join(lines), encoding="utf-8")
    out(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
