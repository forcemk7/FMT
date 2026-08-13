#!/usr/bin/env python3
"""
Compare job-object neighborhoods: at-club jobIds vs orphan (gap) jobIds.
Look for parent=920 + secondary clubId / zero loan field in ±96 of job u32 hits
that are NOT the squad-list slots themselves.
"""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import tempfile
from collections import Counter
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "dynamics-b.fm"
EXTRACT = ROOT / "tmp" / "dynamics-b-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-job-object.txt"
PARENT = 920
CLUB_LO, CLUB_HI = 1, 200_000


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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-jobobj-", suffix=".bin")
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


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 80) -> list[int]:
    out = []
    pos = 0
    while len(out) < limit:
        j = mm.find(needle, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    return out


def hex_row(mm: mmap.mmap, off: int, radius: int = 64) -> str:
    lo, hi = max(0, off - radius), min(len(mm), off + radius)
    chunk = mm[lo:hi]
    parts = []
    for i in range(0, len(chunk), 16):
        base = lo + i
        c = chunk[i : i + 16]
        hx = " ".join(f"{b:02x}" for b in c)
        mark = ">" if base <= off < base + 16 else " "
        parts.append(f"  {mark}{base:08x}  {hx}")
    return "\n".join(parts)


def scan_window_clubs(mm: mmap.mmap, center: int, radius: int = 96) -> list[tuple[int, int]]:
    lo, hi = max(0, center - radius), min(len(mm) - 3, center + radius)
    hits = []
    p = lo & ~3
    while p <= hi:
        v = struct.unpack_from("<I", mm, p)[0]
        if CLUB_LO <= v <= CLUB_HI:
            hits.append((p - center, v))
        p += 4
    return hits


def classify_hit(mm: mmap.mmap, j: int, list_abs: int, list_end: int) -> str:
    if list_abs <= j < list_end:
        return "squad_list"
    # emp-like: tag 02 job 02 uid
    if j >= 2 and mm[j - 1] == 0x02 and mm[j - 2] in (0x08, 0x09, 0x0A, 0x0B):
        if j + 5 <= len(mm) and mm[j + 4] == 0x02:
            return "emp_tag"
    if j >= 1 and mm[j - 1] == 0x02:
        return "xx02_job"
    return "other"


def analyze_job(
    mm: mmap.mmap,
    job: int,
    label: str,
    list_spans: list[tuple[int, int]],
    *,
    dump_hex: bool,
) -> list[str]:
    lines = [f"### {label} job={job}"]
    hits = find_all(mm, struct.pack("<I", job), limit=60)
    by_kind: Counter[str] = Counter()
    interesting = []
    for j in hits:
        kind = "other"
        for a, b in list_spans:
            if a <= j < b:
                kind = "squad_list"
                break
        if kind == "other":
            kind = classify_hit(mm, j, 0, 0)
        by_kind[kind] += 1
        clubs = scan_window_clubs(mm, j, 96)
        has_parent = any(c == PARENT for _d, c in clubs)
        others = sorted({c for _d, c in clubs if c != PARENT})
        zeros_near = 0
        for delta in range(-32, 36, 4):
            k = j + delta
            if 0 <= k <= len(mm) - 4 and struct.unpack_from("<I", mm, k)[0] == 0:
                zeros_near += 1
        interesting.append((j, kind, has_parent, others[:8], zeros_near))
    lines.append(f"  hits={len(hits)} kinds={dict(by_kind)}")
    # Prefer non-list hits with parent club nearby
    ranked = sorted(
        interesting,
        key=lambda r: (
            0 if r[1] != "squad_list" else 1,
            0 if r[2] else 1,
            -len(r[3]),
        ),
    )
    for j, kind, has_p, others, z in ranked[:8]:
        lines.append(
            f"  @{j} kind={kind} parent920={has_p} otherClubs={others} zeros±32={z}"
        )
        if dump_hex and kind != "squad_list" and (has_p or others):
            lines.append(hex_row(mm, j, 48))
    return lines


def main() -> int:
    mod = load_extractor()
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    lines = [f"# job-object parent/loan · {SAVE.name}", ""]
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                ft_abs, ft_n = int(data["listAbs"]), int(data["countHeader"])
                ii_abs, ii_n = int(data["reserves"]["listAbs"]), int(
                    data["reserves"]["countHeader"]
                )
                spans = [
                    (ft_abs, ft_abs + 2 + 4 * ft_n),
                    (ii_abs, ii_abs + 2 + 4 * ii_n),
                ]
                # 3 at-club controls
                controls = [
                    (int(p["jobId"]), p.get("name") or "?")
                    for p in data["players"][:3]
                ]
                gaps = [
                    (215122, "FT-gap0"),
                    (382374, "FT-gap22"),
                    (315711, "FT-gap23"),
                    (317202, "II-gap"),
                    (351592, "II-gap2"),
                ]
                lines.append("## At-club controls")
                for job, name in controls:
                    lines.extend(
                        analyze_job(mm, job, f"at-club {name}", spans, dump_hex=True)
                    )
                    lines.append("")
                lines.append("## Orphan / gap jobs")
                for job, name in gaps:
                    lines.extend(
                        analyze_job(mm, job, name, spans, dump_hex=True)
                    )
                    lines.append("")
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text[:12000])
    print(f"\n… wrote {OUT} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
