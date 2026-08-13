#!/usr/bin/env python3
"""Compare Sipho Det tip on 19.11 vs 22.11 and hunt Det=15 continuous cards."""
from __future__ import annotations

import importlib.util
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("eft", ROOT / "scripts" / "extract-first-team-fast.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

UIDS = {
    2002282525: "Sipho Sithole",
    2002266504: "Lukas Abbe",
}


def decompress(save: Path) -> Path:
    zstd_off = int(mod.probe_container(save)["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-p-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)
    n = 0
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zstd_off)
        r = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    chunk = r.read(8 << 20)
                except zstd.ZstdError:
                    if n == 0:
                        raise
                    break
                if not chunk:
                    break
                out.write(chunk)
                n += len(chunk)
        finally:
            r.close()
    return tmp


def analyze(mm: mmap.mmap, uid: int, name: str) -> None:
    doubles = mod.collect_doubles(mm, uid)
    print(f"\n==== {name} doubles={len(doubles)}")
    if not doubles:
        return
    best = None
    for dab in doubles:
        lo = max(0, dab - mod.ATTR_LOOKBACK)
        window = bytes(mm[lo:dab])
        history = mod.build_ca_history(window)
        tip = history[-1] if history else None
        scored = mod.score_attr_window(window, tip=tip)
        if not scored:
            continue
        q, win_off, rec = scored
        if best is None or q > best[0]:
            best = (q, dab, lo, window, history, tip, win_off, rec)
    if not best:
        print(" no score")
        return
    q, dab, lo, window, history, tip, win_off, rec = best
    hist2, status = mod.ensure_live_ca_on_history(history, rec, gap=dab - (lo + win_off))
    tip2 = (hist2 or [None])[-1]
    def det(p):
        return ((p or {}).get("mental") or {}).get("determination")
    def lea(p):
        return ((p or {}).get("mental") or {}).get("leadership")
    def cmp_(p):
        return ((p or {}).get("mental") or {}).get("composure")
    print(
        f" tipDet={det(tip)} lea={lea(tip)} cmp={cmp_(tip)} nHist={len(history)} "
        f"ensure={status} finalDet={det(tip2)}"
    )
    # last 8 change points
    for i, p in enumerate(history[-8:]):
        m = p.get("mental") or {}
        print(
            f"  hist[{len(history)-8+i}] gap={p.get('gap')} u16={p.get('snapshotU16')} "
            f"b23={p.get('b23')} Det={m.get('determination')} Lea={m.get('leadership')} Cmp={m.get('composure')}"
        )

    # all Det=15 cards with L1 to tip and to last hist
    cards = mod._collect_attr_cards(window)
    tip_ref = tip
    det15 = []
    for off, crec in cards:
        gap = len(window) - off
        pt = mod._ca_point_from_rec(crec, gap=gap)
        if not pt:
            continue
        m = pt.get("mental") or {}
        if m.get("determination") != 15:
            continue
        l1 = mod._history_l1(tip_ref, pt) if tip_ref else None
        det15.append((gap, m.get("leadership"), m.get("composure"), pt.get("snapshotU16"), pt.get("b23"), l1))
    print(f" Det15 in lookback: {len(det15)}")
    for row in sorted(det15)[:15]:
        print("  ", row)

    # Soft attrish: seal+00, band>=8, Det=15
    soft = []
    region = window
    start = 0
    while True:
        z = region.find(b"\x00\x00", start)
        if z < 0 or z + 35 > len(region):
            break
        i = z - 34
        if i >= 0 and z == i + 34 and i + 69 <= len(region):
            if region[i + 43] == 1 and region[i + 34] == 0 and region[i + 35] == 0:
                band = sum(1 for x in region[i : i + 22] if 25 <= x <= 105)
                det_v = round(region[i + 5] / 5) if region[i + 5] % 5 == 0 else None
                if det_v == 15 and band >= 8:
                    soft.append((len(region) - i, band, mod.is_attrish(region, i), list(region[i : i + 14])))
        start = z + 1
    print(f" soft Det15 (band>=8): {len(soft)}")
    for row in soft[:10]:
        print("  ", row[0], "band", row[1], "attrish", row[2], "disp", [round(x/5) for x in row[3]])

    # forward
    fwd = bytes(mm[dab : dab + 30_000])
    fdet = []
    for off, crec in mod._collect_attr_cards(fwd):
        pt = mod._ca_point_from_rec(crec)
        if not pt:
            continue
        m = pt.get("mental") or {}
        if m.get("determination") == 15:
            fdet.append((off, m.get("leadership"), m.get("composure"), pt.get("snapshotU16"), pt.get("b23")))
    print(f" forward Det15: {len(fdet)}")
    for row in fdet[:10]:
        print("  ", row)


def main() -> int:
    save = sorted((ROOT / "data" / "saves").glob("*.fm"), key=lambda p: p.stat().st_mtime, reverse=True)[0]
    print("save", save.name)
    tmp = decompress(save)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for uid, name in UIDS.items():
                    analyze(mm, uid, name)
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
