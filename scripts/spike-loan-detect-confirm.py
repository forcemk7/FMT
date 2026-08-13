#!/usr/bin/env python3
"""Confirm: 64 ff 26 near job ⇒ loanedOut; extract duplicate clubId as loan club."""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "dynamics-b.fm"
EXTRACT = ROOT / "tmp" / "dynamics-b-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "loan-64ff26-extract.txt"
PARENT = 920


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
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-64x-", suffix=".bin")
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


def detect_loan(mm: mmap.mmap, job: int, parent_club: int) -> dict | None:
    """Return loan info if job site has 64 ff 26 motif."""
    jb = struct.pack("<I", job)
    pos = 0
    while True:
        j = mm.find(jb, pos)
        if j < 0:
            return None
        w = mm[j : j + 128]
        i = w.find(b"\x64\xff\x26")
        if 0 <= i <= 48:
            # After motif, look for duplicated clubId (loan club ×2)
            loan_club = None
            scan = mm[j + i : j + i + 96]
            for off in range(0, len(scan) - 7):
                a = struct.unpack_from("<I", scan, off)[0]
                b = struct.unpack_from("<I", scan, off + 4)[0]
                if a == b and 50 <= a <= 100_000 and a != parent_club and a != job:
                    loan_club = a
                    break
            # Fallback: any foreign clubId after motif
            if loan_club is None:
                for off in range(0, len(scan) - 3, 1):
                    a = struct.unpack_from("<I", scan, off)[0]
                    if 50 <= a <= 100_000 and a not in (parent_club, job, 255, 581):
                        loan_club = a
                        break
            return {
                "status": "loanedOut",
                "site": j,
                "motifRel": i,
                "loanClubId": loan_club,
                "parentClubId": parent_club,
            }
        pos = j + 1


def main() -> int:
    mod = load_extractor()
    data = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    parent = int(data.get("clubId") or PARENT)
    players = list(data["players"]) + list(data["reserves"]["players"])
    print("decompress…", flush=True)
    tmp = decompress(mod, SAVE)
    lines = [f"# loan detect · parent={parent}", ""]
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                hits = []
                for p in players:
                    hit = detect_loan(mm, int(p["jobId"]), parent)
                    if hit:
                        hits.append((p.get("name"), int(p["uid"]), int(p["jobId"]), hit))
                        lines.append(
                            f"LOANED OUT {p.get('name')} uid={p['uid']} job={p['jobId']} "
                            f"loanClub={hit['loanClubId']} site@{hit['site']} motif+{hit['motifRel']}"
                        )
                lines.append(f"\ntotalLoanedOut={len(hits)}")
                # sanity: Sipho must be present with 1456
                sipho = next((h for h in hits if "Sithole" in (h[0] or "")), None)
                lines.append(f"sipho={sipho}")
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
