#!/usr/bin/env python3
"""Fast loan hunt: per-UID reverse lookup of employment tags (no full-tail scan)."""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import tempfile
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "dynamics-b.fm"
EXTRACT_CANDIDATES = [
    ROOT / "tmp" / "dynamics-b-extract.json",
    ROOT / "tmp" / "probe-extract-out.json",
]
OUT = ROOT / "tmp" / "fm-spike" / "loan-employment-hunt.txt"
EMP_TAGS = (0x08, 0x09, 0x0A, 0x0B)


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def decompress(mod, save: Path) -> Path:
    zstd_off = int(mod.probe_container(save)["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-loan-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zstd_off)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    chunk = reader.read(8 << 20)
                except zstd.ZstdError:
                    break
                if not chunk:
                    break
                out.write(chunk)
        finally:
            reader.close()
    return tmp


def load_ft_players() -> list[dict]:
    for path in EXTRACT_CANDIDATES:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        players = data.get("players") or []
        if players:
            print(f"using extract {path.name} ({len(players)} players)", flush=True)
            return players
    return []


def jobs_for_uid(mm: mmap.mmap, uid: int, search_lo: int) -> set[int]:
    """Find all <tag> 02 <job> 02 <uid> for this person in the employment tail."""
    needle = b"\x02" + struct.pack("<I", uid)
    jobs: set[int] = set()
    pos = search_lo
    while True:
        j = mm.find(needle, pos)
        if j < 0:
            break
        # employment layout: tag 02 job 02 uid  → tag at j-6, job at j-4
        if j >= 6 and mm[j - 5] == 0x02 and mm[j - 6] in EMP_TAGS:
            job = struct.unpack_from("<I", mm, j - 4)[0]
            if 1_000 <= job <= 50_000_000:
                jobs.add(job)
        pos = j + 1
    return jobs


def main() -> int:
    players = load_ft_players()
    if not players:
        print("no FT extract JSON — run extract first")
        return 1
    if not SAVE.exists():
        print(f"missing {SAVE}")
        return 1

    ft_uids = [int(p["uid"]) for p in players if p.get("uid")]
    name_of = {int(p["uid"]): p.get("name") or f"uid:{p['uid']}" for p in players}
    job_of = {int(p["uid"]): int(p["jobId"]) for p in players if p.get("jobId")}
    ft_job_set = set(job_of.values())

    mod = load_extractor()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"decompress {SAVE.name}…", flush=True)
    tmp = decompress(mod, SAVE)
    lines = [f"# loan employment hunt · {SAVE.name}", f"ft_uids={len(ft_uids)}", ""]

    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                search_lo = max(0, len(mm) - mod.EMPLOYMENT_TAIL)
                hist: dict[int, int] = defaultdict(int)
                multi = []
                for idx, uid in enumerate(ft_uids):
                    if idx % 5 == 0:
                        print(f"  uid {idx + 1}/{len(ft_uids)}…", flush=True)
                    jset = jobs_for_uid(mm, uid, search_lo)
                    hist[len(jset)] += 1
                    primary = job_of.get(uid)
                    others = jset - ({primary} if primary else set())
                    outside_ft = jset - ft_job_set
                    if len(jset) != 1 or others or outside_ft:
                        multi.append(
                            (
                                uid,
                                primary,
                                sorted(jset),
                                sorted(others),
                                sorted(outside_ft),
                            )
                        )

                lines.append(f"## job-count histogram: {dict(sorted(hist.items()))}")
                lines.append(f"## UIDs with unusual job linkage: {len(multi)}")
                for uid, primary, jset, others, outside in multi:
                    lines.append(
                        f"  {name_of.get(uid)} ({uid}) primary={primary} "
                        f"jobs={jset} others={others} outsideFtList={outside}"
                    )
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
