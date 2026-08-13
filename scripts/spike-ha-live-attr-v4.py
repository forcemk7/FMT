#!/usr/bin/env python3
"""
Live HA probe v4 — decode the sparse record near jobId:

  05 ?? ?? 01 AA BB 01 CC CC 01 ff ff

Hypothesis from Tassinari dump:
  AA=Leadership, BB=Determination, CC=Temperament (duplicated)

Also hunt surrounding personality HAs once this marker is locked.
Then emit definite values for .fm pattern search.
"""

from __future__ import annotations

import ctypes
import json
import struct
import sys
from collections import Counter, defaultdict
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-live-attr-v4.txt"
LOCKS_OUT = ROOT / "tmp" / "fm-spike" / "ha-live-locked.json"
DUMP_DIR = ROOT / "tmp" / "fm-spike" / "live-windows-v4"

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PLAYERS = {
    "kizza": {"uid": 2002185604, "job": 285346, "det": 16, "lea": 15, "tem_lock": 15},
    "paco": {"uid": 2000136577, "job": 106935, "det": 19, "lea": 14, "pro_lock": 20},
    "tassinari": {"uid": 2002083070, "job": 182812, "det": 15, "lea": 13},
    "seimen": {"uid": 2000175080, "job": 113517, "det": 18, "lea": 16},
    "yoan": {"uid": 2002089146, "job": 188888, "det": 15, "lea": 17},
}


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
ReadProcessMemory.restype = wintypes.BOOL
VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [
    wintypes.HANDLE, wintypes.LPCVOID, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t,
]
VirtualQueryEx.restype = ctypes.c_size_t
CloseHandle = kernel32.CloseHandle


def read_mem(handle, addr, size):
    buf = (ctypes.c_char * size)()
    nread = ctypes.c_size_t(0)
    if not ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(nread)):
        return None
    return bytes(buf[: nread.value])


def regions(handle):
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while addr < 0x7FFFFFFFFFFF:
        if not VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if size == 0:
            break
        if mbi.State == MEM_COMMIT and mbi.Protect in (0x02, 0x04, 0x08, 0x20, 0x40, 0x80):
            yield base, size
        nxt = base + size
        if nxt <= addr:
            break
        addr = nxt


def collect_hits(handle, value: int, limit=60):
    pat = struct.pack("<I", value)
    hits = []
    for base, size in regions(handle):
        off = 0
        chunk = 4 << 20
        while off < size and len(hits) < limit:
            n = min(chunk, size - off)
            data = read_mem(handle, base + off, n)
            if data:
                start = 0
                while True:
                    j = data.find(pat, start)
                    if j < 0:
                        break
                    hits.append(base + off + j)
                    if len(hits) >= limit:
                        return hits
                    start = j + 1
            off += n
    return hits


def find_sparse_recs(blob: bytes):
    """
    Find 05 ?? ?? 01 AA BB 01 CC CC 01 ff ff
    Returns list of dicts with offsets and fields.
    """
    out = []
    i = 0
    while i < len(blob) - 12:
        if blob[i] != 0x05:
            i += 1
            continue
        # 05 id_lo id_hi 01 AA BB 01 CC CC 01 ff ff
        if blob[i + 3] != 0x01:
            i += 1
            continue
        if blob[i + 6] != 0x01:
            i += 1
            continue
        if blob[i + 9] != 0x01:
            i += 1
            continue
        if blob[i + 10] != 0xFF or blob[i + 11] != 0xFF:
            i += 1
            continue
        aa, bb = blob[i + 4], blob[i + 5]
        cc, dd = blob[i + 7], blob[i + 8]
        if not all(1 <= v <= 20 for v in (aa, bb, cc, dd)):
            i += 1
            continue
        out.append({
            "off": i,
            "id16": blob[i + 1] | (blob[i + 2] << 8),
            "aa": aa,
            "bb": bb,
            "cc": cc,
            "dd": dd,
            "raw": list(blob[i : i + 12]),
        })
        i += 12
    return out


def find_lea_det_tem(blob, lea, det, tem=None):
    """Exact 01 lea det 01 tem tem 01 ff ff (with optional leading 05 id)."""
    hits = []
    if tem is not None:
        pat = bytes([0x01, lea, det, 0x01, tem, tem, 0x01, 0xFF, 0xFF])
        start = 0
        while True:
            j = blob.find(pat, start)
            if j < 0:
                break
            hits.append({"off": j, "lea": lea, "det": det, "tem": tem, "exact": True})
            start = j + 1
    # any tem with lea/det
    pat2 = bytes([0x01, lea, det, 0x01])
    start = 0
    while True:
        j = blob.find(pat2, start)
        if j < 0:
            break
        if j + 9 <= len(blob) and blob[j + 5] == blob[j + 4] and blob[j + 6] == 0x01 and blob[j + 7:j + 9] == b"\xff\xff":
            hits.append({
                "off": j,
                "lea": lea,
                "det": det,
                "tem": blob[j + 4],
                "exact": tem is not None and blob[j + 4] == tem,
            })
        start = j + 1
    # dedupe by off
    uniq = {h["off"]: h for h in hits}
    return list(uniq.values())


def scan_ha_near(blob, center, bands, locks, radius=96):
    """Scan byte packs near a locked sparse marker for full HA bands."""
    orders = {
        "classic_pers": [
            "ambition", "loyalty", "pressure", "professionalism",
            "sportsmanship", "temperament", "controversy", "importantMatches",
        ],
        "user": [
            "professionalism", "pressure", "ambition", "importantMatches",
            "sportsmanship", "temperament", "loyalty", "controversy",
        ],
        "cm_from_amb": [
            "ambition", "loyalty", "pressure", "professionalism",
            "sportsmanship", "temperament",
        ],
    }
    lo = max(0, center - radius)
    hi = min(len(blob), center + radius)
    window = blob[lo:hi]
    cands = []
    for oname, keys in orders.items():
        n = len(keys)
        for i in range(0, len(window) - n + 1):
            raw = window[i : i + n]
            if len(set(raw)) <= 2:
                continue
            ok = True
            vals = {}
            for j, k in enumerate(keys):
                v = raw[j]
                if not (1 <= v <= 20):
                    ok = False
                    break
                if k in bands and not (bands[k][0] <= v <= bands[k][1]):
                    ok = False
                    break
                if k in locks and v != locks[k]:
                    ok = False
                    break
                vals[k] = v
            if not ok:
                continue
            # must satisfy a lock or sharp band attribute in pack
            sharp = False
            for j, k in enumerate(keys):
                if k in locks and raw[j] == locks[k]:
                    sharp = True
                b = bands.get(k)
                if b and b[1] - b[0] <= 4:
                    sharp = True
            if not sharp:
                continue
            cands.append({
                "order": oname,
                "rel": (lo + i) - center,
                "values": vals,
                "raw": list(raw),
            })
    return cands


def main() -> int:
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 13220
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    lines = [f"pid={pid}"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    DUMP_DIR.mkdir(parents=True, exist_ok=True)

    h = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print(f"OpenProcess failed {ctypes.get_last_error()}")
        return 1

    locked = {}
    try:
        for name, meta in PLAYERS.items():
            bands = cal[meta["uid"]]["bands"]
            locks = dict(cal[meta["uid"]].get("locks") or {})
            print(f"scan {name}…", flush=True)
            lines.append(f"\n=== {name} det={meta['det']} lea={meta['lea']} ===")

            lea_det_hits = []
            sparse_near = []
            dumped = 0

            for kind, key in (("job", "job"), ("uid", "uid")):
                for abs_hit in collect_hits(h, meta[key], limit=40):
                    blob = read_mem(h, abs_hit - 8192, 32768)
                    if not blob:
                        continue
                    base = abs_hit - 8192
                    tem_hint = locks.get("temperament") or meta.get("tem_lock")
                    found = find_lea_det_tem(blob, meta["lea"], meta["det"], tem_hint)
                    for f in found:
                        f["abs"] = base + f["off"]
                        f["anchor"] = abs_hit
                        f["kind"] = kind
                        f["anchor_rel"] = f["abs"] - abs_hit
                        lea_det_hits.append(f)
                        # dump neighborhood
                        if dumped < 4:
                            lo = max(0, f["off"] - 64)
                            hi = min(len(blob), f["off"] + 128)
                            path = DUMP_DIR / f"{name}_{kind}_{f['abs']:x}.bin"
                            path.write_bytes(blob[lo:hi])
                            lines.append(
                                f"  HIT {kind}@{abs_hit:#x} abs={f['abs']:#x} "
                                f"anchor_rel={f['anchor_rel']} tem={f['tem']} exact={f['exact']}"
                            )
                            lines.append(
                                f"    hex={blob[f['off']-3:f['off']+12].hex(' ')}"
                            )
                            # HA scan near marker
                            for c in scan_ha_near(blob, f["off"], bands, locks)[:5]:
                                lines.append(f"    HA? {c}")
                            dumped += 1

                    # also collect all sparse 05 records and see if AA/BB match lea/det
                    for rec in find_sparse_recs(blob):
                        if rec["aa"] == meta["lea"] and rec["bb"] == meta["det"]:
                            sparse_near.append({
                                **rec,
                                "abs": base + rec["off"],
                                "anchor": abs_hit,
                                "kind": kind,
                                "tem": rec["cc"],
                            })

            lines.append(f"  lea_det_tem_hits={len(lea_det_hits)} sparse_lea_det={len(sparse_near)}")

            # consensus temperament from lea/det markers
            tems = Counter(h["tem"] for h in lea_det_hits)
            lines.append(f"  tem histogram: {dict(tems.most_common(8))}")

            if lea_det_hits:
                # prefer exact lock / most common tem / closest to job
                preferred = sorted(
                    lea_det_hits,
                    key=lambda x: (
                        0 if x.get("exact") else 1,
                        -tems[x["tem"]],
                        0 if x["kind"] == "job" else 1,
                        abs(x["anchor_rel"]),
                    ),
                )[0]
                # also grab best HA near any hit with this tem
                ha_vals = {}
                ha_votes = Counter()
                for hit in lea_det_hits:
                    if hit["tem"] != preferred["tem"]:
                        continue
                    blob = read_mem(h, hit["abs"] - 128, 256)
                    if not blob:
                        continue
                    for c in scan_ha_near(blob, 128, bands, locks, radius=96):
                        key = (c["order"], tuple(sorted(c["values"].items())))
                        ha_votes[key] += 1
                        ha_vals[key] = c

                locked[name] = {
                    "confidence": "high" if preferred.get("exact") or tems[preferred["tem"]] >= 2 else "medium",
                    "layout": "01 lea det 01 tem tem 01 ff ff",
                    "leadership": preferred["lea"],
                    "determination": preferred["det"],
                    "temperament": preferred["tem"],
                    "tem_count": tems[preferred["tem"]],
                    "n_hits": len(lea_det_hits),
                    "sample_abs": preferred["abs"],
                    "sample_kind": preferred["kind"],
                    "anchor_rel": preferred["anchor_rel"],
                }
                if ha_votes:
                    best_ha = ha_votes.most_common(1)[0][0]
                    locked[name]["ha_near"] = ha_vals[best_ha]
                    locked[name]["ha_near_n"] = ha_votes[best_ha]
                lines.append(f"  LOCK {locked[name]}")
            else:
                lines.append("  NO lea/det/tem sparse marker")

            # Paco Pro=20 hunt: search 01 .. .. with Pro nearby
            if name == "paco":
                pro_hits = 0
                for abs_hit in collect_hits(h, meta["job"], limit=40) + collect_hits(h, meta["uid"], limit=30):
                    blob = read_mem(h, abs_hit - 4096, 16384)
                    if not blob:
                        continue
                    # look for 01 lea det 01 ?? ?? 01
                    needle = bytes([0x01, meta["lea"], meta["det"], 0x01])
                    start = 0
                    while True:
                        j = blob.find(needle, start)
                        if j < 0:
                            break
                        lines.append(
                            f"  paco partial @{abs_hit:#x}+{j-4096}: "
                            f"{blob[j:j+16].hex(' ')}"
                        )
                        pro_hits += 1
                        start = j + 1
                        if pro_hits > 8:
                            break
                # also search 14 19 (lea det contiguous) near byte 20
                for abs_hit in collect_hits(h, meta["uid"], limit=25):
                    blob = read_mem(h, abs_hit - 8192, 32768)
                    if not blob:
                        continue
                    for i in range(len(blob) - 8):
                        if blob[i] == 14 and blob[i + 1] == 19:
                            window = blob[max(0, i - 32) : i + 48]
                            if 20 in window:
                                lines.append(
                                    f"  paco lea|det contiguous + Pro20 near uid "
                                    f"rel={i-8192}: {window.hex(' ')}"
                                )
                                break

        payload = {
            "mode": "sparse_lea_det_tem",
            "players": locked,
            "note": (
                "Temperament from RAM sparse marker 01 Lea Det 01 Tem Tem 01 FF FF. "
                "Use these definite values to pattern-search the .fm save."
            ),
        }
        LOCKS_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        lines.append(f"\nwrote {LOCKS_OUT}")
    finally:
        CloseHandle(h)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in (
            "===", "HIT ", "LOCK ", "NO lea", "tem hist", "lea_det",
            "wrote ", "paco ", "HA?",
        )):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
