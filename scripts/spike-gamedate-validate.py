#!/usr/bin/env python3
"""Assert discover_game_date → 2039-07-01 on the Schalke decomp."""

from __future__ import annotations

import importlib.util
import mmap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"


def main() -> None:
    spec = importlib.util.spec_from_file_location(
        "extract_ft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            got = mod.discover_game_date(mm)
        finally:
            mm.close()
    print(got)
    assert got is not None, "no gameDate"
    assert got["gameDate"] == "2039-07-01", got
    assert got["runLength"] >= 5, got
    print("OK")


if __name__ == "__main__":
    main()
