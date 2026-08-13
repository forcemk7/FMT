#!/usr/bin/env python3
"""
Live HA probe v3 — lock only packs near a real Det/Lea pair.

Filters that kill v2 noise:
- |HA_off - DetLea_off| <= PROX (default 192)
- cm_full determination must equal known Det
- discard runs of identical values (fill/noise)
- require lock keys when known (Tem=15 Kizza, Pro=20 Paco)
- consensus: same order + same ment_rel (+/-4) across ≥2 anchors → lock
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
OUT = ROOT / "tmp" / "fm-spike" / "ha-live-attr-v3.txt"
LOCKS_OUT = ROOT / "tmp" / "fm-spike" / "ha-live-locked.json"
DUMP_DIR = ROOT / "tmp" / "fm-spike" / "live-windows-v3"

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PROX = 192

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PLAYERS = {
    "kizza": {"uid": 2002185604, "job": 285346, "det": 16, "lea": 15},
    "paco": {"uid": 2000136577, "job": 106935, "det": 19, "lea": 14},
    "tassinari": {"uid": 2002083070, "job": 182812, "det": 15, "lea": 13},
    "seimen": {"uid": 2000175080, "job": 113517, "det": 18, "lea": 16},
    "yoan": {"uid": 2002089146, "job": 188888, "det": 15, "lea": 17},
}

# personality HAs we care about (plus determination when present in CM packs)
HA_KEYS = {
    "professionalism", "pressure", "ambition", "importantMatches",
    "sportsmanship", "temperament", "loyalty", "controversy",
}

ORDERS = {
    "classic_pers": [
        "ambition", "loyalty", "pressure", "professionalism",
        "sportsmanship", "temperament", "controversy", "importantMatches",
    ],
    "user": [
        "professionalism", "pressure", "ambition", "importantMatches",
        "sportsmanship", "temperament", "loyalty", "controversy",
    ],
    "cm_from_loy": ["loyalty", "pressure", "professionalism", "sportsmanship", "temperament"],
    "cm_full": [
        "adaptability", "ambition", "determination", "loyalty",
        "pressure", "professionalism", "sportsmanship", "temperament",
    ],
    "pro_tem": [
        "professionalism", "temperament", "pressure", "ambition",
        "loyalty", "sportsmanship", "controversy", "importantMatches",
    ],
    # FM community / staff-adjacent variants seen in older titles
    "cm_loy_first_8": [
        "loyalty", "pressure", "professionalism", "sportsmanship",
        "temperament", "controversy", "ambition", "adaptability",
    ],
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


def collect_hits(handle, value: int, limit=50):
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


def in_band(v, band):
    return band[0] <= v <= band[1]


def is_fill(raw: bytes) -> bool:
    if len(raw) < 3:
        return False
    # all same, or ≥75% same value
    c = Counter(raw)
    most = c.most_common(1)[0][1]
    return most >= max(3, (len(raw) * 3) // 4)


def ok_ha(raw, keys, bands, locks, det):
    if is_fill(raw):
        return False
    for i, key in enumerate(keys):
        v = raw[i]
        if not (1 <= v <= 20):
            return False
        if key == "determination":
            if v != det:
                return False
            continue
        if key == "adaptability":
            continue
        if key not in bands:
            continue
        if not in_band(v, bands[key]):
            return False
        if key in locks and v != locks[key]:
            return False
    # must touch at least one lock or a sharp-band HA
    touched = False
    for i, key in enumerate(keys):
        if key in locks and raw[i] == locks[key]:
            touched = True
        if key in ("temperament", "professionalism", "controversy", "pressure"):
            band = bands.get(key)
            if band and band[1] - band[0] <= 5 and in_band(raw[i], band):
                touched = True
    return touched or not locks  # if no locks, sharp-band check still required above


def find_mental_pairs(blob, det, lea):
    hits = []
    for i in range(len(blob) - 2):
        if blob[i] == det and blob[i + 2] == lea:
            hits.append((i, "raw_gap2"))
        if blob[i] == det * 5 and blob[i + 2] == lea * 5:
            hits.append((i, "x5_gap2"))
    # contiguous raw det|lea
    for i in range(len(blob) - 1):
        if blob[i] == det and blob[i + 1] == lea:
            hits.append((i, "raw_adj"))
        if blob[i] == det * 5 and blob[i + 1] == lea * 5:
            hits.append((i, "x5_adj"))
    det_i = struct.pack("<I", det)
    lea_i = struct.pack("<I", lea)
    start = 0
    while True:
        j = blob.find(det_i, start)
        if j < 0:
            break
        window = blob[j : j + 64]
        k = window.find(lea_i)
        if k >= 0:
            hits.append((j, f"i32_gap{k}"))
        start = j + 1
    return hits


def score_near_ments(blob, abs_base, ments, bands, locks, det):
    out = []
    for ment_off, ment_mode in ments:
        for ord_name, keys in ORDERS.items():
            n = len(keys)
            lo = max(0, ment_off - PROX)
            hi = min(len(blob) - n + 1, ment_off + PROX + 1)
            for i in range(lo, hi):
                raw = blob[i : i + n]
                if not ok_ha(raw, keys, bands, locks, det):
                    continue
                values = {k: raw[j] for j, k in enumerate(keys) if k in HA_KEYS or k == "determination"}
                out.append({
                    "order": ord_name,
                    "abs": abs_base + i,
                    "off": i,
                    "values": values,
                    "full": dict(zip(keys, list(raw))),
                    "ment_rel": i - ment_off,
                    "ment_mode": ment_mode,
                    "ment_off": ment_off,
                })
    return out


def consensus_key(c):
    # bucket ment_rel to nearest 4
    rel = (c["ment_rel"] // 4) * 4
    vals = tuple(sorted((k, v) for k, v in c["values"].items() if k in HA_KEYS))
    return (c["order"], rel, vals)


def main() -> int:
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 13220
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    lines = [f"pid={pid} PROX={PROX}"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    DUMP_DIR.mkdir(parents=True, exist_ok=True)

    h = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print(f"OpenProcess failed {ctypes.get_last_error()}")
        return 1

    all_scored: dict[str, list] = {}
    try:
        for name, meta in PLAYERS.items():
            bands = cal[meta["uid"]]["bands"]
            locks = cal[meta["uid"]].get("locks") or {}
            print(f"scan {name}…", flush=True)
            uid_hits = collect_hits(h, meta["uid"], limit=30)
            job_hits = collect_hits(h, meta["job"], limit=25)
            lines.append(f"\n=== {name} uid={len(uid_hits)} job={len(job_hits)} locks={locks} ===")

            scored = []
            dumped = 0
            for kind, hits in (("uid", uid_hits), ("job", job_hits)):
                for abs_hit in hits:
                    # ±16KB around anchor — HA should be near Det/Lea which is near attrs
                    win = 16384
                    blob = read_mem(h, abs_hit - win // 2, win)
                    if not blob:
                        continue
                    base = abs_hit - win // 2
                    ments = find_mental_pairs(blob, meta["det"], meta["lea"])
                    if not ments:
                        continue
                    lines.append(
                        f"  {kind}@{abs_hit:#x} mental_pairs={len(ments)} "
                        f"modes={sorted({m for _, m in ments})}"
                    )
                    if dumped < 3:
                        path = DUMP_DIR / f"{name}_{kind}_{abs_hit:x}.bin"
                        path.write_bytes(blob)
                        lines.append(f"    dumped {path.name}")
                        dumped += 1
                    for c in score_near_ments(blob, base, ments, bands, locks, meta["det"]):
                        c["anchor"] = abs_hit
                        c["kind"] = kind
                        c["anchor_rel"] = c["abs"] - abs_hit
                        scored.append(c)

            # consensus
            groups: dict[tuple, list] = defaultdict(list)
            for c in scored:
                groups[consensus_key(c)].append(c)
            ranked = []
            for key, group in groups.items():
                anchors = {c["anchor"] for c in group}
                rep = min(group, key=lambda c: abs(c["ment_rel"]))
                rep = dict(rep)
                rep["n_hits"] = len(group)
                rep["n_anchors"] = len(anchors)
                ranked.append(rep)
            ranked.sort(key=lambda c: (-c["n_anchors"], -c["n_hits"], abs(c["ment_rel"])))
            all_scored[name] = ranked
            lines.append(f"  HA_prox_cands={len(ranked)} (raw={len(scored)})")
            for c in ranked[:12]:
                lines.append(
                    f"    nA={c['n_anchors']} n={c['n_hits']} {c['order']} "
                    f"ment_rel={c['ment_rel']} mode={c['ment_mode']} "
                    f"kind={c['kind']} {c['values']}"
                )

        # lock: prefer players with n_anchors>=2; then shared ment_rel across players
        lines.append("\n=== lock attempt ===")
        locked_players = {}
        for name, ranked in all_scored.items():
            if not ranked:
                lines.append(f"{name}: NO proximity candidates")
                continue
            # require multi-anchor OR |ment_rel|<=32 with sharp lock
            pick = None
            for c in ranked:
                if c["n_anchors"] >= 2:
                    pick = c
                    break
                if abs(c["ment_rel"]) <= 32 and c["n_hits"] >= 2:
                    pick = c
                    break
                if abs(c["ment_rel"]) <= 16:
                    pick = c
                    break
            if pick:
                locked_players[name] = {
                    "order": pick["order"],
                    "values": pick["values"],
                    "ment_rel": pick["ment_rel"],
                    "ment_mode": pick["ment_mode"],
                    "n_anchors": pick["n_anchors"],
                    "n_hits": pick["n_hits"],
                    "abs": pick["abs"],
                    "anchor": pick["anchor"],
                    "kind": pick["kind"],
                    "confidence": (
                        "high" if pick["n_anchors"] >= 2
                        else "medium" if abs(pick["ment_rel"]) <= 32
                        else "low"
                    ),
                }
                lines.append(f"LOCK {name} [{locked_players[name]['confidence']}]: {locked_players[name]}")
            else:
                lines.append(f"{name}: candidates but none passed lock bar")
                if ranked:
                    lines.append(f"  best-rejected: {ranked[0]}")

        payload = {
            "mode": "proximity_consensus",
            "prox": PROX,
            "players": locked_players,
            "note": "Only packs within PROX of Det/Lea; use high/medium for save search",
        }
        LOCKS_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        lines.append(f"wrote {LOCKS_OUT}")
    finally:
        CloseHandle(h)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in (
            "uid=", "HA_prox", "LOCK ", "NO prox", "trio=", "mental_pairs=",
            "wrote ", "dumped ", "lock attempt", "best-rejected", "candidates but",
        )):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
