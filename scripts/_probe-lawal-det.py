#!/usr/bin/env python3
"""One-shot: Lawal live Det vs history tip (+ L1) from a names-only extract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UID = 2002331939
NAME = "Samuel Lawal"


def resolve_save() -> Path:
    saves = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not saves:
        raise SystemExit("no .fm in data/saves")
    return saves[0]


def l1(a: dict | None, b: dict | None) -> int | None:
    if not a or not b:
        return None
    va: dict[str, int] = {}
    vb: dict[str, int] = {}
    for nest in ("mental", "physical", "technical", "goalkeeping"):
        for src, dst in ((a, va), (b, vb)):
            block = src.get(nest) or {}
            if not isinstance(block, dict):
                continue
            for k, v in block.items():
                if isinstance(v, int):
                    dst[f"{nest}.{k}"] = v
    keys = set(va) | set(vb)
    return sum(abs(va.get(k, 0) - vb.get(k, 0)) for k in keys)


def main() -> int:
    save = resolve_save()
    print(f"Extracting {save.name} …", flush=True)
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "extract-first-team-fast.py"),
            str(save),
            "--names-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    raw = proc.stdout
    start = raw.rfind("\n{")
    if start < 0:
        start = raw.find("{")
    if start < 0:
        sys.stderr.write(proc.stdout[-3000:] + "\n")
        sys.stderr.write(proc.stderr[-3000:] + "\n")
        print(f"extract failed exit={proc.returncode}", file=sys.stderr)
        return 1

    payload = json.loads(raw[start:])
    (ROOT / "tmp" / "lawal-extract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    players = payload.get("players") or []
    hit = next(
        (
            p
            for p in players
            if p.get("uid") == UID or NAME in (p.get("name") or "")
        ),
        None,
    )
    if not hit:
        print(f"player not found among {len(players)}", file=sys.stderr)
        return 2

    attrs = hit.get("attributes") or {}
    hist = hit.get("attributeHistory") or []
    tip = hist[-1] if hist else None
    mental = attrs.get("mental") or {}
    tip_mental = (tip or {}).get("mental") or {}
    tip_tech = (tip or {}).get("technical") or {}

    summary = {
        "uid": hit.get("uid"),
        "name": hit.get("name"),
        "liveDet": mental.get("determination"),
        "liveLea": mental.get("leadership"),
        "historyLen": len(hist),
        "tipDet": tip_mental.get("determination"),
        "tipLea": tip_mental.get("leadership"),
        "tipIndex": (tip or {}).get("index"),
        "tipSnapshotU16": (tip or {}).get("snapshotU16"),
        "tipB23": (tip or {}).get("b23"),
        "tipGap": (tip or {}).get("gap"),
        "detSeries": [((p.get("mental") or {}).get("determination")) for p in hist],
        "liveVsTipL1_usingSlimAttrs": l1(attrs, tip),
        "tipPen": tip_tech.get("penaltyTaking"),
        "tipCmp": tip_mental.get("composure"),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
