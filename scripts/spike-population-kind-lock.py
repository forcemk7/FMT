#!/usr/bin/env python3
"""Lock: REAL vs NEWGEN via UID magnitude (regen_only personality gate)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location(
    "extract_ft",
    ROOT / "scripts" / "extract-first-team-fast.py",
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FIXTURE = ROOT / "data" / "fixtures" / "save-players.json"
OUT = ROOT / "tmp" / "fm-spike" / "population-kind-lock.txt"


def main() -> int:
    players = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    lines = [
        f"# population kind lock · floor={mod.NEWGEN_UID_FLOOR}",
        "",
    ]
    fails = 0
    for p in players:
        uid = int(p["uid"])
        want = p["kind"]
        got = mod.person_population_kind(uid)
        ok = got == want
        if not ok:
            fails += 1
        lines.append(
            f"{'OK' if ok else 'FAIL'} {want}→{got} uid={uid} {p['name']}"
        )
        print(lines[-1], flush=True)

    # Spot-check Mercenary targets from user report (must be NEWGEN).
    for name, uid in (
        ("Martin Přibyl", 2002266332),
        ("Felix Heynke", 2002439142),  # from earlier U19 resolve; verify below
    ):
        got = mod.person_population_kind(uid)
        lines.append(f"SPOT {name} uid={uid} → {got}")
        print(lines[-1], flush=True)
        if got != "NEWGEN":
            fails += 1

    lines.append("")
    lines.append(f"fails={fails}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} fails={fails}", flush=True)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
