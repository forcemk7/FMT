"""T038: one-session A/B — who else got Det/Lea on newest save, T014 tip vs hist=0.

Runs extract once, classifies FT+II+U19, writes a compact fixture, deletes
this session's decompress .bin and the bulky extract JSON. No extract wire.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GILSON_UID = 2002200653
GAP_MIN = 1_200
GAP_MAX = 14_000


def newest_save() -> Path:
    saves = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not saves:
        raise SystemExit("no .fm in data/saves")
    return saves[0]


def tip_of(p: dict) -> dict | None:
    hist = p.get("attributeHistory")
    if isinstance(hist, list) and hist:
        tip = hist[-1]
        return tip if isinstance(tip, dict) else None
    return None


def det_lea(p: dict) -> tuple[int | None, int | None]:
    mental = ((p.get("attributes") or {}).get("mental") or {})
    d, l = mental.get("determination"), mental.get("leadership")
    return (
        d if isinstance(d, int) else None,
        l if isinstance(l, int) else None,
    )


def classify(p: dict) -> str:
    det, lea = det_lea(p)
    hist = p.get("attributeHistory")
    hist_n = len(hist) if isinstance(hist, list) else 0
    tip = tip_of(p)
    meta = p.get("_extract") or {}
    compacted = bool(meta.get("historyCompacted"))
    raw_hist_n = int(meta.get("historyPoints") or hist_n)
    if compacted:
        raw_hist_n = max(raw_hist_n, 2)

    if det is None or lea is None:
        if hist_n == 0:
            return "hist0_missing"
        return "missing_with_hist"

    if not isinstance(tip, dict):
        return "det_lea_no_tip"

    u16 = int(tip.get("snapshotU16") or 0)
    gap = tip.get("gap")
    tech = tip.get("technical")
    tech_ok = isinstance(tech, dict) and tech
    in_band = isinstance(gap, int) and GAP_MIN <= gap <= GAP_MAX
    first_tip = hist_n == 1 and not compacted

    if u16 > 0 and in_band and not tech_ok:
        if first_tip or hist_n == 1:
            return "t014_first_wiped_tip"
        return "t014_wiped_tip_compacted"

    if tech_ok:
        return "live_or_history_card"

    return "det_lea_other"


def row(p: dict, unit: str) -> dict:
    det, lea = det_lea(p)
    tip = tip_of(p) or {}
    tech = tip.get("technical")
    return {
        "unit": unit,
        "name": p.get("name"),
        "uid": p.get("uid"),
        "kind": p.get("kind"),
        "det": det,
        "lea": lea,
        "class": classify(p),
        "historyPoints": (p.get("_extract") or {}).get("historyPoints"),
        "historyCompacted": bool((p.get("_extract") or {}).get("historyCompacted")),
        "gap": tip.get("gap"),
        "snapshotU16": tip.get("snapshotU16"),
        "b23": tip.get("b23"),
        "technicalPresent": bool(isinstance(tech, dict) and tech),
    }


def collect(payload: dict) -> list[dict]:
    out: list[dict] = []
    for p in payload.get("players") or []:
        out.append(row(p, "FT"))
    reserves = payload.get("reserves") or {}
    for p in reserves.get("players") or []:
        out.append(row(p, "II"))
    u19 = payload.get("u19") or {}
    for p in u19.get("players") or []:
        out.append(row(p, "U19"))
    return out


def delete_session_bins(before: set[Path]) -> list[str]:
    deleted: list[str] = []
    tmp = Path(tempfile.gettempdir())
    for p in tmp.glob("fmt-*.bin"):
        if p in before:
            continue
        try:
            p.unlink()
            deleted.append(p.name)
        except OSError:
            pass
    return deleted


def main() -> int:
    save = newest_save()
    print(f"save {save.name} mtime={save.stat().st_mtime} bytes={save.stat().st_size}", flush=True)
    tmpdir = Path(tempfile.gettempdir())
    before = set(tmpdir.glob("fmt-*.bin"))
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "extract-first-team-fast.py"),
            str(save),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    raw = proc.stdout or ""
    start = raw.rfind("\n{")
    if start < 0:
        start = raw.find("{")
    if start < 0:
        sys.stderr.write((proc.stderr or "")[-4000:] + "\n")
        print(f"extract failed exit={proc.returncode}", file=sys.stderr)
        delete_session_bins(before)
        return 1

    payload = json.loads(raw[start:])
    rows = collect(payload)

    by_class: dict[str, list[dict]] = {}
    for r in rows:
        by_class.setdefault(r["class"], []).append(r)

    t014 = [
        r
        for r in rows
        if r["class"] in ("t014_first_wiped_tip", "t014_wiped_tip_compacted")
        and r["uid"] != GILSON_UID
    ]
    gilson = [r for r in rows if r["uid"] == GILSON_UID]
    hist0 = [r for r in rows if r["class"] == "hist0_missing"]

    other_signing = t014[:]
    odd_paths = [
        r
        for r in rows
        if r["uid"] != GILSON_UID
        and r["det"] is not None
        and r["class"] not in (
            "live_or_history_card",
            "t014_first_wiped_tip",
            "t014_wiped_tip_compacted",
        )
    ]

    counts = {k: len(v) for k, v in sorted(by_class.items())}
    summary = {
        "layout": "t038-other-signing-det-lea-v1",
        "saveUsed": f"data/saves/{save.name}",
        "gameDate": payload.get("gameDate"),
        "extractExit": proc.returncode,
        "counts": counts,
        "gilson": gilson,
        "otherT014Tip": other_signing,
        "oddDetLeaPaths": odd_paths,
        "hist0Remaining": [
            {"unit": r["unit"], "name": r["name"], "uid": r["uid"], "kind": r["kind"]}
            for r in hist0
        ],
        "verdict": (
            "Gilson-only T014 tip this save"
            if not other_signing and not odd_paths
            else "other signing Det/Lea present — see otherT014Tip / oddDetLeaPaths"
        ),
    }

    fixture = ROOT / "data" / "fixtures" / "det-lea-t038-other-signing.json"
    fixture.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "save": save.name,
        "gameDate": payload.get("gameDate"),
        "counts": counts,
        "gilson": gilson,
        "otherT014Tip": other_signing,
        "oddDetLeaPaths": odd_paths,
        "hist0Count": len(hist0),
        "hist0Names": [f"{r['unit']}:{r['name']}" for r in hist0],
        "verdict": summary["verdict"],
        "fixture": str(fixture),
    }, indent=2, ensure_ascii=False), flush=True)

    deleted = delete_session_bins(before)
    print("deleted_bins", deleted, flush=True)
    return 0 if proc.returncode == 0 else proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
