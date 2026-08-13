#!/usr/bin/env python3
"""Verify dob_from_personality_pack against screenshot fixtures + cached decomp."""

from __future__ import annotations

import json
import mmap
import struct
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYERS = json.loads(
    (ROOT / "tmp" / "fm-spike" / "age-hunt-players.json").read_text(encoding="utf-8")
)
EXTRACT = json.loads(
    (ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json").read_text(encoding="utf-8-sig")
)
DECOMP = ROOT / "tmp" / "fm-spike" / "dob-lock-decomp.bin"


def dob_from_personality_pack(buf, pack_abs: int | None) -> str | None:
    if pack_abs is None or pack_abs < 21:
        return None
    doy = struct.unpack_from("<H", buf, pack_abs - 21)[0]
    year = struct.unpack_from("<H", buf, pack_abs - 19)[0]
    if not (1970 <= year <= 2035):
        return None
    if not (1 <= doy <= 366):
        return None
    try:
        dob = date(year, 1, 1) + timedelta(days=doy - 1)
    except Exception:
        return None
    if dob.year != year:
        return None
    return dob.isoformat()


def main() -> None:
    by = {int(p["uid"]): p for p in EXTRACT.get("players") or []}
    ok = 0
    total = 0
    with DECOMP.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                ex = by.get(int(p["uid"]), {})
                pack = ex.get("personalityPackAbs")
                got = dob_from_personality_pack(mm, pack)
                exp = p["dob"]
                if pack is None:
                    print(f"SKIP {p['name']}: no pack")
                    continue
                total += 1
                match = got == exp
                if match:
                    ok += 1
                status = "OK" if match else "FAIL"
                line = f"{status} {p['name']}: got={got} exp={exp}"
                print(line.encode("ascii", "replace").decode("ascii"))
        finally:
            mm.close()
    print(f"LOCK {ok}/{total}")


if __name__ == "__main__":
    main()
