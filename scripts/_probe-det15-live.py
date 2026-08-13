#!/usr/bin/env python3
"""Probe Sipho/Abbe CA cards for missing Det=15 live tips."""
from __future__ import annotations

import importlib.util
import mmap
import os
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "eft", ROOT / "scripts" / "extract-first-team-fast.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

TARGETS = {
    2002282525: "Sipho Sithole",
    2002266504: "Lukas Abbe",
}


def decompress(save: Path) -> Path:
    container = mod.probe_container(save)
    zstd_off = container.get("zstdOffset")
    if zstd_off is None:
        raise SystemExit(f"no zstd offset: {container}")
    print("layout", container.get("inferredLayout"), "zstd", zstd_off)
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-probe-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)
    out_bytes = 0
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(int(zstd_off))
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    chunk = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError as e:
                    if out_bytes == 0:
                        raise
                    print("zstd trailing error after", out_bytes, type(e).__name__)
                    break
                if not chunk:
                    break
                out.write(chunk)
                out_bytes += len(chunk)
        finally:
            reader.close()
    print("decompressed", out_bytes)
    return tmp


def dump_player(mm: mmap.mmap, uid: int, name: str) -> None:
    doubles = mod.collect_doubles(mm, uid)
    print(f"\n==== {name} uid={uid} doubles={len(doubles)}")
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
        quality, win_off, rec = scored
        key = quality
        if best is None or key > best[0]:
            best = (key, dab, lo, window, history, tip, quality, win_off, rec)

    if best is None:
        print("  no scored window")
        return

    _key, dab, lo, window, history, tip, quality, win_off, rec = best
    tip_det = ((tip or {}).get("mental") or {}).get("determination")
    tip_cmp = ((tip or {}).get("mental") or {}).get("composure")
    live = mod._ca_point_from_rec(rec, gap=dab - (lo + win_off))
    live_det = ((live or {}).get("mental") or {}).get("determination")
    hist2, status = mod.ensure_live_ca_on_history(
        history, rec, gap=dab - (lo + win_off)
    )
    tip2 = (hist2 or [])[-1] if hist2 else None
    tip2_det = ((tip2 or {}).get("mental") or {}).get("determination")
    print(
        f"  chosen double@{dab} q={quality} hist={len(history)} "
        f"tipDet={tip_det} tipCmp={tip_cmp} liveDet={live_det} "
        f"ensure={status} finalTipDet={tip2_det}"
    )

    cards = mod._collect_attr_cards(window)
    win_len = len(window)
    rows = []
    for off, crec in cards:
        gap = win_len - off
        pt = mod._ca_point_from_rec(crec, gap=gap)
        if pt is None:
            continue
        m = pt.get("mental") or {}
        det = m.get("determination")
        cmp_ = m.get("composure")
        lea = m.get("leadership")
        u16 = pt.get("snapshotU16")
        b23 = pt.get("b23")
        l1 = mod._history_l1(tip, pt) if tip else None
        in_band = mod.ATTR_CARD_GAP_MIN <= gap <= mod.ATTR_CARD_GAP_MAX
        rows.append((gap, det, cmp_, lea, u16, b23, l1, in_band))

    rows.sort(key=lambda r: r[0])
    print("  nearest 30 cards:")
    for gap, det, cmp_, lea, u16, b23, l1, in_band in rows[:30]:
        mark = ""
        if det == 15:
            mark += " DET15"
        if l1 is not None and l1 <= 80:
            mark += " CONT"
        if not in_band:
            mark += " OOB"
        print(
            f"    gap={gap:5d} Det={det} Lea={lea} Cmp={cmp_} u16={u16} b23={b23} L1={l1}{mark}"
        )

    det15 = [r for r in rows if r[0] and r[1] == 15]
    print(f"  Det=15 in chosen window: {len(det15)}")
    for gap, det, cmp_, lea, u16, b23, l1, in_band in det15[:25]:
        print(
            f"    gap={gap:5d} Lea={lea} Cmp={cmp_} u16={u16} b23={b23} L1={l1} in_band={in_band}"
        )

    # Scan every double for Det=15 continuous cards with small gap
    extras = []
    for dab2 in doubles:
        lo2 = max(0, dab2 - mod.ATTR_LOOKBACK)
        w2 = bytes(mm[lo2:dab2])
        hist = mod.build_ca_history(w2)
        tip2b = hist[-1] if hist else None
        for off, crec in mod._collect_attr_cards(w2):
            gap = len(w2) - off
            pt = mod._ca_point_from_rec(crec, gap=gap)
            if not pt:
                continue
            m = pt.get("mental") or {}
            if m.get("determination") != 15:
                continue
            l1 = mod._history_l1(tip2b, pt) if tip2b else None
            extras.append(
                (
                    dab2,
                    gap,
                    m.get("leadership"),
                    m.get("composure"),
                    pt.get("snapshotU16"),
                    pt.get("b23"),
                    l1,
                    tip2b and ((tip2b.get("mental") or {}).get("determination")),
                )
            )
    extras.sort(key=lambda t: (t[1], t[0]))
    print(f"  Det=15 across all doubles: {len(extras)}")
    for row in extras[:20]:
        print(
            f"    dab={row[0]} gap={row[1]} Lea={row[2]} Cmp={row[3]} "
            f"u16={row[4]} b23={row[5]} L1={row[6]} tipDet={row[7]}"
        )


def main() -> int:
    saves = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    save = saves[0]
    print("save", save.name)
    tmp = decompress(save)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for uid, name in TARGETS.items():
                    dump_player(mm, uid, name)
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
