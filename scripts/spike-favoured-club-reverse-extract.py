#!/usr/bin/env python3
"""Confirm favoured-club record + club-side reverse extract.

Locked shape (Assan Ouedraogo, both Schalke + Man City):
  4e 64 01 03 02 <clubId u32le>
where 0x64 = affinity 100.

Also probe 4e <aff:1-100> 01 03 02 <clubId> for variable affinity.
"""

from __future__ import annotations

import json
import struct
import time
from collections import Counter
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "favoured-club-reverse-extract.txt"
EXTRACT = ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json"

SCH, CITY = 920, 679
ASSAN = 2000188173
UID_LO, UID_HI = 2_000_000_000, 2_004_000_000

# Fixed high-affinity favourite-club marker
FAV100_PREFIX = bytes.fromhex("4e64010302")  # 4e 64 01 03 02


def log(s: str = "") -> None:
    print(s, flush=True)


def load_ft() -> set[int]:
    if not EXTRACT.exists():
        return set()
    d = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    return {int(p["uid"]) for p in d.get("players") or [] if p.get("uid")}


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


def read_lp_ascii(buf: bytes, off: int) -> str | None:
    if off + 4 > len(buf):
        return None
    n = struct.unpack_from("<I", buf, off)[0]
    if not (2 <= n <= 48) or off + 4 + n > len(buf):
        return None
    raw = buf[off + 4 : off + 4 + n]
    if not raw.isascii() and not all(32 <= b < 127 or b >= 128 for b in raw):
        # allow utf-8-ish for Ouedraogo-style names: be lenient on high bytes
        pass
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            s = raw.decode("latin-1")
        except Exception:
            return None
    if s and s[0].isalpha() and any(c.isalpha() for c in s):
        return s
    return None


def nearest_uid_before(buf: bytes, at: int, lookback: int = 400) -> int | None:
    """Walk backward for typed 02|<core uid> before the fav record."""
    lo = max(0, at - lookback)
    best = None
    best_dist = 10**9
    i = at - 5
    while i >= lo:
        if buf[i] == 0x02:
            uid = struct.unpack_from("<I", buf, i + 1)[0]
            if UID_LO <= uid <= UID_HI:
                dist = at - i
                if dist < best_dist:
                    best_dist = dist
                    best = uid
                    # prefer closest; keep scanning for closer
        i -= 1
    return best


def name_near(buf: bytes, at: int, uid: int | None) -> str | None:
    lo = max(0, at - 500)
    hi = min(len(buf), at + 80)
    chunk = buf[lo:hi]
    # Prefer full "First Last" after uid bytes if present
    if uid is not None:
        ub = struct.pack("<I", uid)
        p = chunk.rfind(ub)
        if p >= 0:
            for off in range(p + 4, min(len(chunk) - 4, p + 80)):
                nm = read_lp_ascii(chunk, off)
                if nm and " " in nm:
                    return nm
    # Fallback: any lp name in lookback
    for off in range(len(chunk) - 4 - 20, -1, -1):
        nm = read_lp_ascii(chunk, off)
        if nm and " " in nm:
            return nm
    return None


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ft = load_ft()
    lines: list[str] = []
    lines.append("# favoured-club reverse extract (4e 64 01 03 02)")
    lines.append(f"save={SAVE.name}")
    lines.append("")

    needles = {
        "Schalke100": FAV100_PREFIX + struct.pack("<I", SCH),
        "City100": FAV100_PREFIX + struct.pack("<I", CITY),
    }

    # Also affinity-flexible: 4e <aff> 01 03 02 <club>
    aff_hist_sch: Counter[int] = Counter()
    aff_hist_city: Counter[int] = Counter()

    results: dict[str, list[dict]] = {k: [] for k in needles}
    seen_uid: dict[str, set[int]] = {k: set() for k in needles}

    abs_base = 0
    carry = b""
    overlap = 512
    t0 = time.perf_counter()
    est = max(SAVE.stat().st_size * 3, 1)
    last = -1

    log("scanning fav100 markers…")
    for block in stream_blocks(SAVE):
        data = carry + block
        search_end = len(data) - (0 if abs_base == 0 else 64)
        start0 = max(0, len(carry) - overlap - 3) if abs_base else 0

        # Affinity histogram for Sch/City via flexible prefix
        for club, hist, cb in (
            (SCH, aff_hist_sch, struct.pack("<I", SCH)),
            (CITY, aff_hist_city, struct.pack("<I", CITY)),
        ):
            # find 01 03 02 club, check for 4e aff before
            needle = bytes.fromhex("010302") + cb
            start = start0
            while True:
                j = data.find(needle, start, search_end + 8)
                if j < 0 or j >= search_end:
                    break
                if j >= 2 and data[j - 2] == 0x4E:
                    aff = data[j - 1]
                    if 1 <= aff <= 100:
                        hist[aff] += 1
                start = j + 1

        for label, needle in needles.items():
            start = start0
            while True:
                j = data.find(needle, start, search_end + len(needle))
                if j < 0 or j >= search_end:
                    break
                abs_hit = abs_base - len(carry) + j
                uid = nearest_uid_before(data, j, lookback=450)
                nm = name_near(data, j, uid)
                employed = uid in ft if uid else False
                rec = {
                    "abs": abs_hit,
                    "uid": uid,
                    "name": nm,
                    "employed": employed,
                }
                results[label].append(rec)
                if uid:
                    seen_uid[label].add(uid)
                start = j + 1

        abs_base += len(block)
        carry = data[-overlap:]
        pct = int(min(99, abs_base * 100 / est))
        if pct != last and pct % 10 == 0:
            last = pct
            log(
                f"  … ~{pct}% sch={len(results['Schalke100'])} "
                f"city={len(results['City100'])}"
            )

    log(f"done {time.perf_counter() - t0:.1f}s")

    for label, hist in (("Schalke", aff_hist_sch), ("City", aff_hist_city)):
        lines.append(f"## affinity hist for 4e <aff> 01 03 02 |{label}")
        for aff, n in sorted(hist.items()):
            lines.append(f"  aff={aff}: {n}")
        lines.append("")

    for label in needles:
        rows = results[label]
        uids = seen_uid[label]
        external = [r for r in rows if r["uid"] and r["uid"] not in ft]
        ext_uids = {r["uid"] for r in external}
        lines.append(f"## {label}")
        lines.append(f"hits={len(rows)} distinctUid={len(uids)}")
        lines.append(f"externalHits={len(external)} distinctExternal={len(ext_uids)}")
        assan_hits = [r for r in rows if r["uid"] == ASSAN]
        lines.append(f"Assan hits={len(assan_hits)} {'FOUND' if assan_hits else 'MISSING'}")
        lines.append("sample external:")
        # unique by uid
        shown = set()
        for r in external:
            if r["uid"] in shown:
                continue
            shown.add(r["uid"])
            lines.append(
                f"  uid={r['uid']} name={r['name']!r} abs={r['abs']}"
            )
            if len(shown) >= 40:
                break
        lines.append("")

    # Intersection idea: Schalke fav AND not FT — the scouting list
    sch_ext = sorted(u for u in seen_uid["Schalke100"] if u not in ft)
    lines.append(f"## SCOUT LIST: Schalke fav100, not in FT ({len(sch_ext)})")
    # Attach best name from results
    name_by = {}
    for r in results["Schalke100"]:
        if r["uid"] and r["name"] and r["uid"] not in name_by:
            name_by[r["uid"]] = r["name"]
    for u in sch_ext:
        mark = " <-- ASSAN" if u == ASSAN else ""
        lines.append(f"  {u}  {name_by.get(u, '?')}{mark}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    for line in lines[:80]:
        log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
