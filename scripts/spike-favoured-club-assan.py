#!/usr/bin/env python3
"""Ground-truth hunt: Assan Ouedraogo favoured clubs.

Known:
  uid=2000188173  Assan Ouedraogo
  current club: Man City
  favoured: Schalke 04 (clubId 920), Man City (?)

Find every UID hit, dump neighborhoods, look for Schalke/Man City club ids,
and try to lock a reusable (person → favoured club) record shape.
"""

from __future__ import annotations

import struct
import time
from collections import Counter
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "favoured-club-assan.txt"

UID = 2000188173
NAME = "Assan Ouedraogo"
SCHALKE_ID = 920
# Man City DB unique id is typically small; resolve via string → nearby u32.
CITY_NAME_CANDIDATES = (
    "Man City",
    "Manchester City",
    "Manchester C",
)


def log(s: str = "") -> None:
    print(s, flush=True)


def stream_blocks(path: Path):
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf." and head[25] == 3
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            reader.close()


def find_city_club_id() -> list[tuple[int, str, int]]:
    """Return candidate (abs, name_hit, clubIdGuess) near Man City name strings."""
    hits: list[tuple[int, str, int]] = []
    needles = [(n, n.encode("utf-8")) for n in CITY_NAME_CANDIDATES]
    abs_base = 0
    carry = b""
    overlap = 128
    for block in stream_blocks(SAVE):
        data = carry + block
        for label, raw in needles:
            # lp32-prefixed preferred
            lp = struct.pack("<I", len(raw)) + raw
            start = 0
            while True:
                j = data.find(lp, start)
                if j < 0:
                    break
                abs_hit = abs_base - len(carry) + j
                # club id often immediately after short/long name pair — scan +0..+80
                after = data[j + len(lp) : j + len(lp) + 96]
                for off in range(0, max(0, len(after) - 3)):
                    v = struct.unpack_from("<I", after, off)[0]
                    if 1 <= v <= 50_000 and v != SCHALKE_ID:
                        hits.append((abs_hit + len(lp) + off, label, v))
                        break
                start = j + 1
        abs_base += len(block)
        carry = data[-overlap:]
        if abs_base > 200 * 1024 * 1024 and len(hits) >= 8:
            # enough early catalog hits
            break
    return hits


def hexdump(win: bytes, marks: dict[int, str], width: int = 16) -> list[str]:
    lines = []
    for i in range(0, len(win), width):
        chunk = win[i : i + width]
        hx = " ".join(f"{b:02x}" for b in chunk)
        lines.append(f"  +{i:04x}  {hx}")
        for rel, label in sorted(marks.items()):
            if i <= rel < i + width:
                lines.append("        " + " " * ((rel - i) * 3) + f"^^ {label}")
    return lines


def u32s_in(win: bytes, base_abs: int) -> list[tuple[int, int]]:
    out = []
    for i in range(0, len(win) - 3):
        v = struct.unpack_from("<I", win, i)[0]
        out.append((base_abs + i, v))
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Assan Ouedraogo favoured-club ground truth")
    lines.append(f"save={SAVE.name}")
    lines.append(f"uid={UID} name={NAME}")
    lines.append(f"favoured claimed: Schalke ({SCHALKE_ID}), Man City")
    lines.append("")

    log("resolving Man City clubId candidates…")
    city_hits = find_city_club_id()
    city_freq = Counter(v for _, _, v in city_hits)
    lines.append("## Man City clubId candidates (near name strings, early stream)")
    for v, n in city_freq.most_common(15):
        lines.append(f"  id={v}: {n}")
    # Prefer the most common small id near "Man City" / "Manchester City"
    city_id = city_freq.most_common(1)[0][0] if city_freq else None
    lines.append(f"using cityId={city_id}")
    log(f"cityId candidates top={city_freq.most_common(5)} -> using {city_id}")

    uid_b = struct.pack("<I", UID)
    sch_b = struct.pack("<I", SCHALKE_ID)
    city_b = struct.pack("<I", city_id) if city_id else None

    # Collect UID occurrences with wide windows
    WIN_BEFORE, WIN_AFTER = 256, 512
    uid_hits: list[dict] = []
    co_schalke = 0
    co_city = 0
    co_both = 0

    # Also: distances from UID to each clubId within windows
    sch_deltas: Counter[int] = Counter()
    city_deltas: Counter[int] = Counter()

    # Pattern hunt: shared bytes between (uid…schalke) and (uid…city) regions
    # Record for each UID hit whether clubs appear and relative layout.
    abs_base = 0
    carry = b""
    overlap = WIN_BEFORE + 8
    t0 = time.perf_counter()
    est = max(SAVE.stat().st_size * 3, 1)
    last = -1

    log("scanning for Assan UID…")
    for block in stream_blocks(SAVE):
        data = carry + block
        search_end = len(data) - (0 if abs_base == 0 else WIN_AFTER)
        start = max(0, len(carry) - overlap - 3) if abs_base else 0
        while True:
            j = data.find(uid_b, start, max(start, search_end) + 3)
            if j < 0 or j >= search_end:
                break
            abs_hit = abs_base - len(carry) + j
            lo = max(0, j - WIN_BEFORE)
            hi = min(len(data), j + 4 + WIN_AFTER)
            win = data[lo:hi]
            rel_uid = j - lo
            has_s = sch_b in win
            has_c = (city_b in win) if city_b else False
            if has_s:
                co_schalke += 1
                p = 0
                while True:
                    k = win.find(sch_b, p)
                    if k < 0:
                        break
                    sch_deltas[k - rel_uid] += 1
                    p = k + 1
            if has_c:
                co_city += 1
                p = 0
                while True:
                    k = win.find(city_b, p)
                    if k < 0:
                        break
                    city_deltas[k - rel_uid] += 1
                    p = k + 1
            if has_s and has_c:
                co_both += 1

            typed = j >= 1 and data[j - 1] == 0x02
            tag = None
            if j >= 2 and data[j - 1] == 0x02:
                tag = f"{data[j - 2]:02x}02"

            uid_hits.append(
                {
                    "abs": abs_hit,
                    "typed": typed,
                    "tag": tag,
                    "has_s": has_s,
                    "has_c": has_c,
                    "win": win if (has_s or has_c or typed) else None,
                    "rel_uid": rel_uid,
                }
            )
            start = j + 1

        abs_base += len(block)
        carry = data[-(WIN_BEFORE + WIN_AFTER) :]
        pct = int(min(99, abs_base * 100 / est))
        if pct != last and pct % 10 == 0:
            last = pct
            log(f"  … ~{pct}%  uidHits={len(uid_hits)} sch={co_schalke} city={co_city} both={co_both}")

    log(f"scan done {time.perf_counter() - t0:.1f}s  bytes={abs_base:,}")

    lines.append("")
    lines.append(
        f"## UID hits: {len(uid_hits)}  "
        f"withSchalke={co_schalke} withCity={co_city} withBoth={co_both}"
    )
    tag_hist = Counter(h["tag"] for h in uid_hits if h["tag"])
    lines.append(f"tag hist (byte before 02|uid): {dict(tag_hist.most_common(12))}")
    typed_n = sum(1 for h in uid_hits if h["typed"])
    lines.append(f"typed 02|uid: {typed_n}")

    lines.append("")
    lines.append("## delta (clubId_rel - uid_rel) when club in ±window")
    lines.append("Schalke:")
    for d, n in sch_deltas.most_common(20):
        lines.append(f"  delta={d:+d}: {n}")
    lines.append("Man City:")
    for d, n in city_deltas.most_common(20):
        lines.append(f"  delta={d:+d}: {n}")

    # Dump windows where BOTH clubs appear (gold), else Schalke-only
    gold = [h for h in uid_hits if h["has_s"] and h["has_c"] and h["win"] is not None]
    sch_only = [h for h in uid_hits if h["has_s"] and not h["has_c"] and h["win"] is not None]
    lines.append("")
    lines.append(f"## GOLD windows (UID + Schalke + Man City): {len(gold)}")
    for h in gold[:12]:
        win = h["win"]
        assert win is not None
        marks = {h["rel_uid"]: "Assan uid"}
        p = 0
        while True:
            k = win.find(sch_b, p)
            if k < 0:
                break
            marks[k] = "Schalke 920"
            p = k + 1
        if city_b:
            p = 0
            while True:
                k = win.find(city_b, p)
                if k < 0:
                    break
                marks[k] = f"City {city_id}"
                p = k + 1
        lines.append(
            f"\n### abs={h['abs']} typed={h['typed']} tag={h['tag']}"
        )
        lines.extend(hexdump(win, marks))

    lines.append("")
    lines.append(f"## Schalke-only windows (sample): {len(sch_only)}")
    for h in sch_only[:8]:
        win = h["win"]
        assert win is not None
        marks = {h["rel_uid"]: "Assan uid"}
        p = 0
        while True:
            k = win.find(sch_b, p)
            if k < 0:
                break
            marks[k] = "Schalke 920"
            p = k + 1
        lines.append(
            f"\n### abs={h['abs']} typed={h['typed']} tag={h['tag']}"
        )
        lines.extend(hexdump(win, marks))

    # Byte-signature around Schalke near Assan: common prefix/suffix
    lines.append("")
    lines.append("## bytes immediately before/after Schalke near Assan UID windows")
    before_hist: Counter[bytes] = Counter()
    after_hist: Counter[bytes] = Counter()
    for h in gold + sch_only:
        win = h["win"]
        if not win:
            continue
        p = 0
        while True:
            k = win.find(sch_b, p)
            if k < 0:
                break
            before_hist[win[max(0, k - 4) : k]] += 1
            after_hist[win[k + 4 : k + 8]] += 1
            p = k + 1
    lines.append("before (up to 4B):")
    for b, n in before_hist.most_common(15):
        lines.append(f"  {b.hex(' ')}: {n}")
    lines.append("after (4B):")
    for b, n in after_hist.most_common(15):
        lines.append(f"  {b.hex(' ')}: {n}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    for line in lines[:45]:
        log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
