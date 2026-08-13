#!/usr/bin/env python3
"""
HA hunt v3: near ALL uid occurrences (not just doubles), prefer name-trail region,
require Kizza temperament==15, and find shared delta from UID for both anchors.
"""

from __future__ import annotations

import mmap
import os
import struct
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
OUT = ROOT / "tmp" / "fm-spike" / "ha-model-citizen-v3.txt"
ZSTD_OFF = 26

C_UID = 2002220356
K_UID = 2002185604

ORDERS = {
    "user": ["professionalism", "pressure", "ambition", "importantMatches", "sportsmanship", "temperament", "loyalty", "controversy"],
    "gs1": ["professionalism", "ambition", "loyalty", "pressure", "temperament", "sportsmanship", "controversy", "importantMatches"],
    "gs2": ["ambition", "loyalty", "pressure", "professionalism", "sportsmanship", "temperament", "controversy", "importantMatches"],
    "pro_amb_pre": ["professionalism", "ambition", "pressure", "importantMatches", "loyalty", "temperament", "sportsmanship", "controversy"],
}

BANDS_C = {
    "professionalism": (15, 20),
    "pressure": (15, 20),
    "ambition": (12, 20),
    "importantMatches": (1, 20),
    "sportsmanship": (15, 20),
    "temperament": (15, 20),
    "loyalty": (15, 20),
    "controversy": (1, 14),
}
BANDS_K = {**BANDS_C, "temperament": (15, 15)}


def d5(b: int) -> int:
    return int(round(b / 5))


def ok(vals: dict, bands: dict) -> bool:
    return all(lo <= vals[k] <= hi for k, (lo, hi) in bands.items())


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-ha3-", suffix=".bin")
    os.close(fd)
    tmp = Path(name)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(ZSTD_OFF)
        r = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = r.read(8 << 20)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                out.write(b)
        finally:
            r.close()
    return tmp


def find_uids(mm, uid: int, limit: int = 40) -> list[int]:
    pat = struct.pack("<I", uid)
    hits = []
    j = mm.find(pat)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(pat, j + 1)
    return hits


def scan_around(mm, uid_hits: list[int], bands: dict, radius: int = 1024):
    """Return list of (abs, delta_from_uid, order, enc, vals, uid_abs)."""
    found = []
    for uabs in uid_hits:
        lo = max(0, uabs - radius)
        hi = min(len(mm), uabs + radius)
        blob = bytes(mm[lo:hi])
        for ord_name, keys in ORDERS.items():
            ti = keys.index("temperament")
            for i in range(0, len(blob) - 7):
                raw = blob[i : i + 8]
                abs_off = lo + i
                delta = abs_off - uabs
                # skip if overlapping uid dword itself oddly — allow
                for enc, vals_fn in (
                    ("d5", lambda r: {keys[j]: d5(r[j]) for j in range(8)}),
                    ("raw", lambda r: {keys[j]: int(r[j]) for j in range(8)}),
                ):
                    vals = vals_fn(raw)
                    if "temperament" in bands and bands["temperament"][0] == bands["temperament"][1]:
                        if vals["temperament"] != bands["temperament"][0]:
                            continue
                    if not ok(vals, bands):
                        continue
                    found.append((abs_off, delta, ord_name, enc, vals, uabs))
    return found


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    t0 = time.perf_counter()
    print("decompress…", flush=True)
    tmp = decompress(SAVE)
    print(f"bytes={tmp.stat().st_size}", flush=True)

    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            c_hits = find_uids(mm, C_UID)
            k_hits = find_uids(mm, K_UID)
            lines.append(f"Contreras uid hits={len(c_hits)} first={c_hits[:8]}")
            lines.append(f"Kizza uid hits={len(k_hits)} first={k_hits[:8]}")

            c_found = scan_around(mm, c_hits, BANDS_C, radius=2048)
            k_found = scan_around(mm, k_hits, BANDS_K, radius=2048)
            lines.append(f"Contreras HA-like={len(c_found)} Kizza HA-like={len(k_found)}")

            # Shared (order, enc, delta_from_uid)
            c_keys = {(o, e, d): (a, v, u) for a, d, o, e, v, u in c_found}
            k_keys = {(o, e, d): (a, v, u) for a, d, o, e, v, u in k_found}
            shared = sorted(set(c_keys) & set(k_keys), key=lambda t: (abs(t[2]), t[0], t[1]))
            lines.append(f"shared (order,enc,delta)={len(shared)}")
            for key in shared[:60]:
                o, e, d = key
                ca, cv, cu = c_keys[key]
                ka, kv, ku = k_keys[key]
                lines.append(f"  order={o} enc={e} delta={d}")
                lines.append(f"    C abs={ca} uidAbs={cu} {cv}")
                lines.append(f"    K abs={ka} uidAbs={ku} {kv}")

            # If no shared delta, show best Kizza hits (tem=15 locked) for manual
            lines.append("\n=== top Kizza hits (tem lock) ===")
            # prefer deltas near name lp32 (+4..+200)
            k_found.sort(key=lambda t: (0 if 4 <= t[1] <= 400 else 1, abs(t[1])))
            for abs_off, delta, ord_name, enc, vals, uabs in k_found[:40]:
                lines.append(
                    f"  delta={delta} order={ord_name} enc={enc} abs={abs_off} uidAbs={uabs} {vals}"
                )

            lines.append("\n=== hex ±64 around each Kizza uid hit ===")
            for uabs in k_hits[:6]:
                blob = bytes(mm[max(0, uabs - 64) : uabs + 128])
                lines.append(f"uidAbs={uabs}")
                base = max(0, uabs - 64)
                for i in range(0, len(blob), 16):
                    chunk = blob[i : i + 16]
                    hx = " ".join(f"{b:02x}" for b in chunk)
                    dv = " ".join(f"{d5(b):2d}" for b in chunk)
                    lines.append(f"  {base+i:10d}: {hx} | {dv}")
        finally:
            mm.close()

    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass

    lines.append(f"\nelapsedMs={int((time.perf_counter()-t0)*1000)}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if line.startswith("Contreras uid") or line.startswith("Kizza uid") or "shared" in line or line.startswith("  order="):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
