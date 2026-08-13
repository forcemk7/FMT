#!/usr/bin/env python3
"""Spike: discover managed First Team teamId without hardcoding + time early exits."""

from __future__ import annotations

import struct
import time
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
CHUNK = 8 * 1024 * 1024
SENTINEL = bytes.fromhex("7f02000000ffffffff")  # after any TID
JOB_LO, JOB_HI = 100_000, 800_000
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000


def main() -> None:
    print(f"save={SAVE.name}", flush=True)
    t0 = time.perf_counter()
    abs_base = 0
    carry = b""
    squad_lists: list[tuple[int, int, int, list[int]]] = []  # abs, tid, count, jobs
    # staff/manager style: 0b 02 <tid 100k-300k> 02 <uid>
    tid_to_uids: dict[int, list[int]] = defaultdict(list)
    bytes_out = 0

    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(CHUNK)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                chunk_start = abs_base - len(carry)
                bytes_out += len(block)

                # squad lists: <tid u32> + sentinel + count u16 + jobs
                start = 0
                while True:
                    j = data.find(SENTINEL, start)
                    if j < 0 or j < 4:
                        break
                    tid = struct.unpack_from("<I", data, j - 4)[0]
                    c_off = j + len(SENTINEL)
                    if c_off + 2 <= len(data):
                        count = struct.unpack_from("<H", data, c_off)[0]
                        jobs_off = c_off + 2
                        if 18 <= count <= 45 and jobs_off + 4 * count <= len(data):
                            jobs = [
                                struct.unpack_from("<I", data, jobs_off + 4 * k)[0]
                                for k in range(count)
                            ]
                            in_range = sum(1 for x in jobs if JOB_LO <= x <= JOB_HI)
                            if in_range >= count * 0.85:
                                squad_lists.append(
                                    (chunk_start + jobs_off, tid, count, jobs)
                                )
                    start = j + 1

                # employment-ish links for team-sized ids
                for i in range(0, len(data) - 11):
                    if data[i] != 0x0B or data[i + 1] != 0x02 or data[i + 6] != 0x02:
                        continue
                    tid = struct.unpack_from("<I", data, i + 2)[0]
                    if not (100_000 <= tid <= 300_000):
                        continue
                    uid = struct.unpack_from("<I", data, i + 7)[0]
                    if UID_LO <= uid <= UID_HI:
                        if len(tid_to_uids[tid]) < 8:
                            tid_to_uids[tid].append(uid)

                abs_base += len(block)
                carry = data[-(len(SENTINEL) + 4 + 2 + 4 * 45) :]

                # progress every ~200MB out
                if bytes_out and bytes_out % (200 * 1024 * 1024) < CHUNK:
                    print(
                        f"  …decomp {bytes_out/1e6:.0f}MB out, "
                        f"lists={len(squad_lists)} "
                        f"t={time.perf_counter()-t0:.1f}s",
                        flush=True,
                    )
        finally:
            reader.close()

    elapsed = time.perf_counter() - t0
    print(f"\nfull stream {bytes_out/1e6:.0f}MB in {elapsed:.1f}s", flush=True)
    print(f"squad-list hits: {len(squad_lists)}", flush=True)

    # unique by tid keep earliest largest
    by_tid: dict[int, tuple[int, int, list[int]]] = {}
    for abs_, tid, count, jobs in squad_lists:
        uniq = len(set(jobs))
        prev = by_tid.get(tid)
        if prev is None or uniq > len(set(prev[2])) or (
            uniq == len(set(prev[2])) and abs_ < prev[0]
        ):
            by_tid[tid] = (abs_, count, jobs)

    print(f"unique TIDs with squad lists: {len(by_tid)}", flush=True)
    # show TIDs that also have employment links
    linked = [(tid, by_tid[tid], tid_to_uids.get(tid, [])) for tid in by_tid]
    linked.sort(key=lambda t: (-len(t[2]), -t[1][1]))
    print("\nTop squad TIDs (prefer those with 0b02 employment links):", flush=True)
    for tid, (abs_, count, jobs), uids in linked[:20]:
        print(
            f"  tid={tid} abs={abs_} count={count} uniq={len(set(jobs))} "
            f"emp_uids={uids[:4]}",
            flush=True,
        )

    # How early is the first / Schalke-known list?
    if squad_lists:
        first = min(squad_lists, key=lambda x: x[0])
        print(
            f"\nearliest squad list: tid={first[1]} abs={first[0]} "
            f"(~{first[0]/bytes_out*100:.2f}% into stream)",
            flush=True,
        )
    # known from prior RE
    if 193616 in by_tid:
        abs_, count, jobs = by_tid[193616]
        print(f"known managed 193616: abs={abs_} count={count}", flush=True)


if __name__ == "__main__":
    main()
