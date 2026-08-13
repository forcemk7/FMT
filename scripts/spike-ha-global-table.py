#!/usr/bin/env python3
"""
Global HA table hunt.

Idea: HAs live in a fixed-stride person table somewhere in the save.
Collect all UniqueID hits for the 5 calibration players, then look for
record strides / shared relative layouts where bytes fit the locked bands.
"""

from __future__ import annotations

import json
import mmap
import os
import struct
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-global-table.txt"
ZSTD_OFF = 26
# Scan a large head; full 2GB optional via env
SCAN_CAP = int(os.environ.get("FMT_HA_SCAN", str(512 * 1024 * 1024)))

PLAYERS = {
    "kizza": {"uid": 2002185604, "job": 285346},
    "paco": {"uid": 2000136577, "job": 106935},
    "tassinari": {"uid": 2002083070, "job": 182812},
    "seimen": {"uid": 2000175080, "job": 113517},
    "yoan": {"uid": 2002089146, "job": 188888},
}
TRIO = ["kizza", "paco", "tassinari"]
ALL = list(PLAYERS)

# Candidate HA attribute orders to test as contiguous 8×u8
ORDERS = {
    "user": [
        "professionalism",
        "pressure",
        "ambition",
        "importantMatches",
        "sportsmanship",
        "temperament",
        "loyalty",
        "controversy",
    ],
    "pro_tem": [
        "professionalism",
        "temperament",
        "pressure",
        "ambition",
        "loyalty",
        "sportsmanship",
        "controversy",
        "importantMatches",
    ],
    "gs1": [
        "professionalism",
        "ambition",
        "loyalty",
        "pressure",
        "temperament",
        "sportsmanship",
        "controversy",
        "importantMatches",
    ],
}


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-glob-", suffix=".bin")
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


def collect_hits(mm, uid: int, limit: int = 200) -> list[int]:
    pat = struct.pack("<I", uid)
    hits = []
    end = min(len(mm), SCAN_CAP)
    j = mm.find(pat, 0, end)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(pat, j + 1, end)
    return hits


def in_band(v, band):
    return band[0] <= v <= band[1]


def ok_tuple(raw8: bytes, bands: dict, order: list[str], locks: dict) -> bool:
    if len(raw8) < 8:
        return False
    for i, key in enumerate(order):
        v = raw8[i]
        if not (1 <= v <= 20):
            return False
        if not in_band(v, bands[key]):
            return False
        if key in locks and v != locks[key]:
            return False
    return True


def d5_tuple(raw8: bytes) -> bytes:
    return bytes(int(round(b / 5)) for b in raw8)


def main() -> int:
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    for k, info in PLAYERS.items():
        info["bands"] = cal[info["uid"]]["bands"]
        info["locks"] = cal[info["uid"]].get("locks") or {}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    t0 = time.perf_counter()
    print(f"decompress… scanCap={SCAN_CAP}", flush=True)
    tmp = decompress(SAVE)
    print(f"bytes={tmp.stat().st_size}", flush=True)

    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hits = {}
            for k, info in PLAYERS.items():
                hits[k] = collect_hits(mm, info["uid"])
                lines.append(f"{k}: uidHits={len(hits[k])} first={hits[k][:8]}")

            # Job ID hits
            for k, info in PLAYERS.items():
                jhits = collect_hits(mm, info["job"], limit=80)
                lines.append(f"{k}: jobHits={len(jhits)} first={jhits[:6]}")

            # --- Stride discovery between trio UID hits ---
            lines.append("\n=== stride candidates from UID hit deltas (trio) ===")
            # For each pair, consider differences between every hit of A and B
            # Keep deltas that are multiples of common strides 16..512
            stride_votes: Counter[int] = Counter()
            for a in TRIO:
                for b in TRIO:
                    if a >= b:
                        continue
                    for pa in hits[a][:60]:
                        for pb in hits[b][:60]:
                            d = abs(pb - pa)
                            if d == 0 or d > 5_000_000:
                                continue
                            for s in range(32, 513):
                                if d % s == 0:
                                    stride_votes[s] += 1
            top = stride_votes.most_common(25)
            lines.append(f"top strides by pair-hit divisibility: {top}")

            # Focus on promising strides (high votes, not tiny)
            candid_strides = [s for s, _c in top if s >= 48][:12]
            if 69 not in candid_strides:
                candid_strides.append(69)  # known CA card
            if 77 not in candid_strides:
                candid_strides.append(77)  # known sheet row

            # --- For each stride: treat each UID hit as record start or UID-at-offset ---
            lines.append("\n=== scan UID-relative HA tuples for strides ===")
            # Relative offsets from UID byte to putative 8-byte HA block
            rel_scan = list(range(-256, 257))

            for stride in candid_strides:
                # Also try: records aligned such that UIDs fall at same mod stride
                lines.append(f"\n-- stride={stride} --")
                # Group hits by mod stride
                buckets = {k: Counter(h % stride for h in hits[k]) for k in ALL}
                # Find residue class where all trio appear
                residues = set(buckets["kizza"]) 
                for k in TRIO[1:]:
                    residues &= set(buckets[k])
                lines.append(f"shared residues (trio): {sorted(residues)[:20]} (n={len(residues)})")

                # For each shared residue, pick one hit per player with that mod,
                # then scan relative offsets for HA tuple fit
                best = []
                for resid in list(sorted(residues))[:30]:
                    pos = {}
                    ok = True
                    for k in TRIO:
                        cands = [h for h in hits[k] if h % stride == resid]
                        if not cands:
                            ok = False
                            break
                        # Prefer mid-list hit
                        pos[k] = cands[len(cands) // 2]
                    if not ok:
                        continue
                    for rel in rel_scan:
                        for enc_name in ("raw", "d5"):
                            for ord_name, order in ORDERS.items():
                                vals_ok = True
                                decoded = {}
                                for k in TRIO:
                                    abs_off = pos[k] + rel
                                    if abs_off < 0 or abs_off + 8 > len(mm):
                                        vals_ok = False
                                        break
                                    raw = bytes(mm[abs_off : abs_off + 8])
                                    if enc_name == "d5":
                                        # need *5 raw bytes 5..100 approx then display
                                        disp = bytes(int(round(b / 5)) for b in raw)
                                        check = disp
                                    else:
                                        check = raw
                                    if not ok_tuple(
                                        check,
                                        PLAYERS[k]["bands"],
                                        order,
                                        PLAYERS[k]["locks"],
                                    ):
                                        vals_ok = False
                                        break
                                    decoded[k] = list(check)
                                if vals_ok:
                                    # validate all 5 if their residue hits exist
                                    all_ok = True
                                    decoded5 = dict(decoded)
                                    for k in ALL:
                                        cands = [h for h in hits[k] if h % stride == resid]
                                        if not cands:
                                            all_ok = False
                                            break
                                        pk = cands[len(cands) // 2]
                                        raw = bytes(mm[pk + rel : pk + rel + 8])
                                        check = (
                                            bytes(int(round(b / 5)) for b in raw)
                                            if enc_name == "d5"
                                            else raw
                                        )
                                        if not ok_tuple(
                                            check,
                                            PLAYERS[k]["bands"],
                                            order,
                                            PLAYERS[k]["locks"],
                                        ):
                                            all_ok = False
                                            break
                                        decoded5[k] = list(check)
                                    best.append(
                                        (
                                            all_ok,
                                            stride,
                                            resid,
                                            rel,
                                            enc_name,
                                            ord_name,
                                            decoded5 if all_ok else decoded,
                                            pos,
                                        )
                                    )
                best.sort(key=lambda t: (not t[0], abs(t[3])))
                lines.append(f"trio HA tuple hits: {len(best)}")
                for item in best[:20]:
                    all_ok, stride, resid, rel, enc, ord_name, decoded, pos = item
                    lines.append(
                        f"  all5={all_ok} resid={resid} rel={rel} enc={enc} order={ord_name}"
                    )
                    lines.append(f"    pos={pos}")
                    lines.append(f"    decoded={decoded}")

            # --- Brute: for each paco hit, search ±512 for 8-byte Pro-lock tuples,
            # then see if same rel from kizza/tassinari hits works ---
            lines.append("\n=== UID-hit relative transfer (no stride) ===")
            transfer_hits = []
            for ord_name, order in ORDERS.items():
                for enc_name in ("raw",):
                    for pa in hits["paco"][:40]:
                        for rel in range(-128, 129):
                            raw = bytes(mm[max(0, pa + rel) : pa + rel + 8])
                            if len(raw) < 8:
                                continue
                            if not ok_tuple(
                                raw, PLAYERS["paco"]["bands"], order, PLAYERS["paco"]["locks"]
                            ):
                                continue
                            # require Pro lock already in ok_tuple
                            # check kizza & tassinari at same rel from SOME hit
                            matched = {"paco": (pa, list(raw))}
                            for k in ("kizza", "tassinari"):
                                found_k = None
                                for hk in hits[k][:40]:
                                    rawk = bytes(mm[hk + rel : hk + rel + 8])
                                    if len(rawk) < 8:
                                        continue
                                    if ok_tuple(
                                        rawk,
                                        PLAYERS[k]["bands"],
                                        order,
                                        PLAYERS[k]["locks"],
                                    ):
                                        found_k = (hk, list(rawk))
                                        break
                                if not found_k:
                                    matched = None
                                    break
                                matched[k] = found_k
                            if matched and len(matched) == 3:
                                # try validators
                                all5 = dict(matched)
                                ok5 = True
                                for k in ("seimen", "yoan"):
                                    found_k = None
                                    for hk in hits[k][:40]:
                                        rawk = bytes(mm[hk + rel : hk + rel + 8])
                                        if len(rawk) < 8:
                                            continue
                                        if ok_tuple(
                                            rawk,
                                            PLAYERS[k]["bands"],
                                            order,
                                            PLAYERS[k]["locks"],
                                        ):
                                            found_k = (hk, list(rawk))
                                            break
                                    if not found_k:
                                        ok5 = False
                                        break
                                    all5[k] = found_k
                                transfer_hits.append((ok5, rel, ord_name, all5 if ok5 else matched))
            # dedupe by rel+order
            seen = set()
            uniq = []
            for item in transfer_hits:
                key = (item[0], item[1], item[2])
                if key in seen:
                    continue
                seen.add(key)
                uniq.append(item)
            uniq.sort(key=lambda t: (not t[0], abs(t[1])))
            lines.append(f"transfer hits unique: {len(uniq)}")
            for ok5, rel, ord_name, matched in uniq[:30]:
                lines.append(f"  all5={ok5} rel={rel} order={ord_name}")
                for k, (pos, vals) in matched.items():
                    lines.append(f"    {k}@{pos}: {vals}")

            # --- Single-attr global: find offsets where all trio's SOME uid-neighborhood
            # share a value — already failed near primary; try max over hits ---
            lines.append("\n=== single-byte max-over-hits Tem/Pro (trio) ===")
            for attr, need in (
                ("temperament", True),
                ("professionalism", True),
                ("controversy", False),
                ("pressure", False),
            ):
                # For each rel, for each player take ANY hit that satisfies band at that rel
                hits_rel = []
                for rel in range(-256, 257):
                    vals = {}
                    ok = True
                    positions = {}
                    for k in TRIO:
                        found = None
                        for hk in hits[k][:50]:
                            if hk + rel < 0 or hk + rel >= len(mm):
                                continue
                            v = mm[hk + rel]
                            if not (1 <= v <= 20):
                                continue
                            if not in_band(v, PLAYERS[k]["bands"][attr]):
                                continue
                            locks = PLAYERS[k]["locks"]
                            if attr in locks and v != locks[attr]:
                                continue
                            found = (hk, v)
                            break
                        if not found:
                            ok = False
                            break
                        positions[k], vals[k] = found
                    if ok:
                        # validators
                        ok5 = True
                        for k in ("seimen", "yoan"):
                            found = None
                            for hk in hits[k][:50]:
                                if hk + rel < 0 or hk + rel >= len(mm):
                                    continue
                                v = mm[hk + rel]
                                if not (1 <= v <= 20):
                                    continue
                                if not in_band(v, PLAYERS[k]["bands"][attr]):
                                    continue
                                found = (hk, v)
                                break
                            if not found:
                                ok5 = False
                                break
                            positions[k], vals[k] = found
                        hits_rel.append((ok5, rel, vals, positions))
                hits_rel.sort(key=lambda t: (not t[0], abs(t[1])))
                lines.append(f"{attr}: candidates={len(hits_rel)}")
                for ok5, rel, vals, positions in hits_rel[:12]:
                    lines.append(f"  all5={ok5} rel={rel} vals={vals}")

        finally:
            mm.close()

    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass

    lines.append(f"\nelapsedMs={int((time.perf_counter()-t0)*1000)}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    # print highlights
    for line in lines:
        if any(
            x in line
            for x in (
                "uidHits=",
                "top strides",
                "trio HA tuple",
                "all5=",
                "transfer hits",
                "candidates=",
                "shared residues",
                "-- stride",
            )
        ):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
