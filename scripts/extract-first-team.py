#!/usr/bin/env python3
"""Extract First Team squad JSON from a career .fm save (Python zstd + locked jobId layout)."""

from __future__ import annotations

import json
import struct
import sys
import time
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]

FIRST_TEAM_ID = 193616
TID_PREFIX = struct.pack("<I", FIRST_TEAM_ID) + bytes.fromhex("7f02000000ffffffff")
FIXTURE_UIDS = [2000175080, 2002234366, 2002266341]
JOB_LO, JOB_HI = 100_000, 800_000
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000
CHUNK = 8 * 1024 * 1024


def resolve_save() -> Path:
    if len(sys.argv) >= 2:
        p = Path(sys.argv[1])
        if not p.is_file():
            raise SystemExit(f"Save not found: {p}")
        return p
    saves = sorted(
        Path(ROOT, "data", "saves").glob("*.fm"),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    if not saves:
        raise SystemExit("No .fm in data/saves")
    return saves[0]


def stream_chunks(path: Path, overlap: int):
    abs_base = 0
    carry = b""
    with path.open("rb") as f:
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
                yield chunk_start, data
                abs_base += len(block)
                carry = data[-overlap:] if overlap else b""
        finally:
            reader.close()


def score(jobs: list[int]) -> int:
    if not (15 <= len(jobs) <= 50):
        return -1
    in_range = sum(1 for j in jobs if JOB_LO <= j <= JOB_HI)
    if in_range < len(jobs) * 0.85:
        return -1
    return len(set(jobs)) * 10 + in_range


def find_lists(save: Path) -> tuple[int, int, list[int]]:
    best = None
    overlap = len(TID_PREFIX) + 2 + 4 * 50
    for abs0, data in stream_chunks(save, overlap):
        start = 0
        while True:
            i = data.find(TID_PREFIX, start)
            if i < 0:
                break
            c_off = i + len(TID_PREFIX)
            if c_off + 2 > len(data):
                break
            count = struct.unpack_from("<H", data, c_off)[0]
            jobs_off = c_off + 2
            if not (15 <= count <= 50) or jobs_off + 4 * count > len(data):
                start = i + 1
                continue
            jobs = [
                struct.unpack_from("<I", data, jobs_off + 4 * k)[0]
                for k in range(count)
            ]
            sc = score(jobs)
            if sc >= 0 and (best is None or sc > best[0]):
                best = (sc, abs0 + jobs_off, count, jobs)
            start = i + 1
    if not best:
        raise SystemExit("No First Team job list found")
    return best[1], best[2], best[3]


def resolve(save: Path, jobs: list[int]) -> dict[int, tuple[int, str]]:
    wanted = set(jobs)
    job_uid: dict[int, int] = {}
    uid_name: dict[int, str] = {}
    tags = {0x0B, 0x09, 0x0A, 0x08}

    def read_lp(buf: bytes, off: int):
        if off + 4 > len(buf):
            return None
        ln = struct.unpack_from("<I", buf, off)[0]
        if not (1 <= ln <= 48) or off + 4 + ln > len(buf):
            return None
        raw = buf[off + 4 : off + 4 + ln]
        # Names may be UTF-8 (e.g. Müller) — reject only control/NUL bytes.
        if any(b < 0x20 and b not in (0x09,) for b in raw):
            return None
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            s = raw.decode("latin-1", errors="replace")
        if not any(c.isalpha() for c in s):
            return None
        return s, off + 4 + ln

    for _abs0, data in stream_chunks(save, 64):
        for i in range(0, len(data) - 11):
            if data[i] not in tags or data[i + 1] != 0x02 or data[i + 6] != 0x02:
                continue
            job = struct.unpack_from("<I", data, i + 2)[0]
            if job not in wanted or job in job_uid:
                continue
            uid = struct.unpack_from("<I", data, i + 7)[0]
            if UID_LO <= uid <= UID_HI:
                job_uid[job] = uid
        pending = {
            u for u in job_uid.values() if u not in uid_name or " " not in uid_name[u]
        }
        if pending:
            for i in range(0, len(data) - 16):
                if data[i] != 0x00 or data[i + 1] != 0x02:
                    continue
                uid = struct.unpack_from("<I", data, i + 2)[0]
                if uid not in pending:
                    continue
                off = i + 6
                if (
                    off + 5 <= len(data)
                    and data[off] == 0x02
                    and data[off + 1 : off + 5] == b"\xff\xff\xff\xff"
                ):
                    off += 5
                first = read_lp(data, off)
                if not first:
                    continue
                s1, n1 = first
                last = read_lp(data, n1)
                name = f"{s1} {last[0]}" if last and last[0][:1].isupper() else s1
                if not name[:1].isupper():
                    continue
                cur = uid_name.get(uid, "")
                if not cur or (" " in name and " " not in cur):
                    uid_name[uid] = name
        if len(job_uid) >= len(wanted) and all(
            " " in uid_name.get(u, "") for u in job_uid.values()
        ):
            break

    out: dict[int, tuple[int, str]] = {}
    for job in jobs:
        uid = job_uid.get(job, 0)
        name = uid_name.get(uid, f"job:{job}" if uid == 0 else f"uid:{uid}")
        out[job] = (uid, name)
    return out


def main() -> int:
    t0 = time.time()
    save = resolve_save()
    print(f"Extracting First Team from:\n  {save}", file=sys.stderr, flush=True)
    list_abs, count, jobs_raw = find_lists(save)
    jobs: list[int] = []
    seen: set[int] = set()
    for j in jobs_raw:
        if j in seen or not (JOB_LO <= j <= JOB_HI):
            continue
        seen.add(j)
        jobs.append(j)
    print(
        f"list @{list_abs} header_count={count} unique_jobs={len(jobs)}",
        file=sys.stderr,
        flush=True,
    )
    print("resolving jobId → UniqueID → name…", file=sys.stderr, flush=True)
    resolved = resolve(save, jobs)
    players = []
    for j in jobs:
        uid, name = resolved[j]
        if uid == 0:
            # Occasional non-person u32 at list head; drop rather than fake a player.
            continue
        players.append({"jobId": j, "uid": uid, "name": name})
    present = [u for u in FIXTURE_UIDS if any(p["uid"] == u for p in players)]
    missing = [u for u in FIXTURE_UIDS if u not in present]
    result = {
        "savePath": str(save),
        "saveName": save.name,
        "teamId": FIRST_TEAM_ID,
        "listAbs": list_abs,
        "countHeader": count,
        "players": players,
        "fixtureCheck": {
            "requiredUids": FIXTURE_UIDS,
            "present": present,
            "missing": missing,
            "ok": len(missing) == 0,
        },
        "elapsedMs": int((time.time() - t0) * 1000),
    }
    print(
        f"done in {result['elapsedMs']}ms — {len(players)} players · fixture ok={result['fixtureCheck']['ok']}",
        file=sys.stderr,
        flush=True,
    )
    if missing:
        print(f"missing fixtures: {missing}", file=sys.stderr, flush=True)
    print(json.dumps(result, indent=2))
    return 0 if result["fixtureCheck"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
