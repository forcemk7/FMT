#!/usr/bin/env python3
"""Fast motif-first confirm of Sipho loanedOut → Legia 1456."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    data = json.loads(
        (ROOT / "tmp" / "dynamics-b-extract.json").read_text(encoding="utf-8-sig")
    )
    jobs = {int(p["jobId"]) for p in data["players"]} | {
        int(p["jobId"]) for p in data["reserves"]["players"]
    }
    parent = int(data["clubId"])
    save = ROOT / "data" / "saves" / "dynamics-b.fm"

    import mmap
    import os
    import tempfile

    import zstandard as zstd

    zoff = int(mod.probe_container(save)["zstdOffset"])
    fd, tmpn = tempfile.mkstemp(prefix="fmt-loanfast-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmpn)
    print("decompress…", flush=True)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zoff)
        r = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    c = r.read(8 << 20)
                except zstd.ZstdError:
                    break
                if not c:
                    break
                out.write(c)
        finally:
            r.close()
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hit = mod.detect_loaned_out_jobs(mm, jobs, parent)
        finally:
            mm.close()
    tmp.unlink(missing_ok=True)
    print("loaned_out", hit)
    sipho_job = next(
        int(p["jobId"]) for p in data["players"] if "Sithole" in (p.get("name") or "")
    )
    print("sipho_job", sipho_job, "→", hit.get(sipho_job))
    assert sipho_job in hit, "Sipho missing from loaned-out detect"
    assert hit[sipho_job] == 1456, f"expected Legia 1456, got {hit[sipho_job]}"
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
