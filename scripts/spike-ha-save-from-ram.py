#!/usr/bin/env python3
"""
Given locked HA values from live RAM (ha-live-locked.json), search the
decompressed .fm save for those exact byte sequences near each player's UID.
"""

from __future__ import annotations

import json
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
LOCKS = ROOT / "tmp" / "fm-spike" / "ha-live-locked.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-save-from-ram.txt"
ZSTD_OFF = 26

UIDS = {
    "kizza": 2002185604,
    "paco": 2000136577,
    "tassinari": 2002083070,
    "seimen": 2000175080,
    "yoan": 2002089146,
}


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-savelock-", suffix=".bin")
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


def main() -> int:
    if not LOCKS.exists():
        print(f"missing {LOCKS}")
        return 1
    locked = json.loads(LOCKS.read_text(encoding="utf-8"))
    lines = [f"mode={locked.get('mode')}"]

    # Build raw patterns from player values
    patterns = {}
    players = locked.get("players") or {}
    for name, info in players.items():
        vals = info.get("values") if isinstance(info, dict) and "values" in info else info
        if not isinstance(vals, dict):
            continue
        # preserve insertion order from JSON
        raw = bytes(vals.values())
        patterns[name] = {"raw": raw, "vals": vals, "uid": UIDS[name]}
        lines.append(f"{name}: pattern={list(raw)} keys={list(vals.keys())}")

    if not patterns:
        lines.append("no patterns")
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return 1

    print("decompress…", flush=True)
    tmp = decompress(SAVE)
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for name, meta in patterns.items():
                uid_pat = struct.pack("<I", meta["uid"])
                raw = meta["raw"]
                # find all pattern hits
                phits = []
                j = mm.find(raw, 0)
                while j >= 0 and len(phits) < 50:
                    phits.append(j)
                    j = mm.find(raw, j + 1)
                lines.append(f"\n{name}: patternHits={len(phits)}")
                # for each, distance to nearest UID
                uid_hits = []
                u = mm.find(uid_pat, 0)
                while u >= 0 and len(uid_hits) < 80:
                    uid_hits.append(u)
                    u = mm.find(uid_pat, u + 1)
                lines.append(f"  uidHits={len(uid_hits)}")
                near = []
                for p in phits:
                    if not uid_hits:
                        break
                    nearest = min(uid_hits, key=lambda u: abs(u - p))
                    near.append((abs(nearest - p), nearest - p, p, nearest))
                near.sort()
                for dist, delta, p, u in near[:15]:
                    lines.append(f"  pat@{p} uid@{u} delta={delta} dist={dist}")
                    # dump 32B around pattern
                    lo = max(0, p - 16)
                    blob = bytes(mm[lo : p + len(raw) + 16])
                    lines.append(f"    ctx={blob.hex(' ')}")

            # Shared relative delta: pattern to UID
            lines.append("\n=== shared pat-to-uid deltas ===")
            # for each player take deltas within 64KB
            delta_sets = {}
            for name, meta in patterns.items():
                uid_pat = struct.pack("<I", meta["uid"])
                raw = meta["raw"]
                phits = []
                j = mm.find(raw, 0)
                while j >= 0 and len(phits) < 100:
                    phits.append(j)
                    j = mm.find(raw, j + 1)
                uhits = []
                u = mm.find(uid_pat, 0)
                while u >= 0 and len(uhits) < 100:
                    uhits.append(u)
                    u = mm.find(uid_pat, u + 1)
                deltas = set()
                for p in phits:
                    for uh in uhits:
                        d = p - uh
                        if abs(d) <= 65536:
                            deltas.add(d)
                delta_sets[name] = deltas
                lines.append(f"{name}: near-deltas n={len(deltas)}")
            shared = None
            for name in patterns:
                shared = delta_sets[name] if shared is None else (shared & delta_sets[name])
            lines.append(f"shared deltas all players={sorted(shared)[:40] if shared else []}")
            if shared:
                lines.append("*** SAVE LAYOUT CANDIDATE ***")
                for d in sorted(shared, key=abs)[:20]:
                    lines.append(f"  delta={d}")
        finally:
            mm.close()
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
