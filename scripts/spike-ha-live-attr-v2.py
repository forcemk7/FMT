#!/usr/bin/env python3
"""
Live HA probe v2:
- Try Det/Lea as raw display bytes AND as *5 (save-style)
- Larger ±32KB windows around UID and jobId
- Dump promising windows; score HA packs more permissively
"""

from __future__ import annotations

import ctypes
import json
import struct
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-live-attr-v2.txt"
LOCKS_OUT = ROOT / "tmp" / "fm-spike" / "ha-live-locked.json"
DUMP_DIR = ROOT / "tmp" / "fm-spike" / "live-windows"

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PLAYERS = {
    "kizza": {"uid": 2002185604, "job": 285346, "det": 16, "lea": 15},
    "paco": {"uid": 2000136577, "job": 106935, "det": 19, "lea": 14},
    "tassinari": {"uid": 2002083070, "job": 182812, "det": 15, "lea": 13},
    "seimen": {"uid": 2000175080, "job": 113517, "det": 18, "lea": 16},
    "yoan": {"uid": 2002089146, "job": 188888, "det": 15, "lea": 17},
}

ORDERS = {
    "user": [
        "professionalism", "pressure", "ambition", "importantMatches",
        "sportsmanship", "temperament", "loyalty", "controversy",
    ],
    "classic_pers": [
        "ambition", "loyalty", "pressure", "professionalism",
        "sportsmanship", "temperament", "controversy", "importantMatches",
    ],
    "cm_from_loy": ["loyalty", "pressure", "professionalism", "sportsmanship", "temperament"],
    "pro_tem": [
        "professionalism", "temperament", "pressure", "ambition",
        "loyalty", "sportsmanship", "controversy", "importantMatches",
    ],
    "cm_full": [
        "adaptability", "ambition", "determination", "loyalty",
        "pressure", "professionalism", "sportsmanship", "temperament",
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


def collect_hits(handle, value: int, limit=40):
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


def ok_ha(raw, keys, bands, locks, require_det=False):
    for i, key in enumerate(keys):
        v = raw[i]
        if key == "adaptability":
            if not (1 <= v <= 20):
                return False
            continue
        if key == "determination":
            # when present in pack, must match known det if require
            if not (1 <= v <= 20):
                return False
            continue
        if key not in bands:
            if not (1 <= v <= 20):
                return False
            continue
        if not (1 <= v <= 20) or not in_band(v, bands[key]):
            return False
        if key in locks and v != locks[key]:
            return False
    return True


def find_mental_pairs(blob, det, lea):
    """Return list of (offset, mode) where mode in raw_gap2, x5_gap2, i32_pair."""
    hits = []
    # raw display gap2
    for i in range(len(blob) - 2):
        if blob[i] == det and blob[i + 2] == lea:
            hits.append((i, "raw_gap2"))
    # *5 gap2
    db, lb = det * 5, lea * 5
    for i in range(len(blob) - 2):
        if blob[i] == db and blob[i + 2] == lb:
            hits.append((i, "x5_gap2"))
    # int32 LE pair within 32 bytes
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


def score(blob, abs_base, bands, locks):
    out = []
    for ord_name, keys in ORDERS.items():
        n = len(keys)
        for i in range(0, len(blob) - n + 1):
            raw = blob[i : i + n]
            if ok_ha(raw, keys, bands, locks):
                out.append({
                    "order": ord_name,
                    "abs": abs_base + i,
                    "off": i,
                    "values": {k: raw[j] for j, k in enumerate(keys) if k in bands or k in ("adaptability", "determination")},
                    "raw": list(raw),
                    "full": dict(zip(keys, list(raw))),
                })
    return out


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

    all_scored = {}
    try:
        for name, meta in PLAYERS.items():
            bands = cal[meta["uid"]]["bands"]
            locks = cal[meta["uid"]].get("locks") or {}
            print(f"scan {name}…", flush=True)
            uid_hits = collect_hits(h, meta["uid"], limit=25)
            job_hits = collect_hits(h, meta["job"], limit=15)
            lines.append(f"\n=== {name} uid={len(uid_hits)} job={len(job_hits)} ===")

            scored = []
            dumped = 0
            for kind, hits in (("uid", uid_hits), ("job", job_hits)):
                for abs_hit in hits:
                    blob = read_mem(h, abs_hit - 8192, 65536)
                    if not blob:
                        continue
                    base = abs_hit - 8192
                    ments = find_mental_pairs(blob, meta["det"], meta["lea"])
                    if not ments:
                        continue
                    lines.append(f"  {kind}@{abs_hit:#x} mental_pairs={len(ments)} modes={sorted({m for _, m in ments})}")
                    # dump first promising window
                    if dumped < 2:
                        path = DUMP_DIR / f"{name}_{kind}_{abs_hit:x}.bin"
                        path.write_bytes(blob)
                        lines.append(f"    dumped {path.name} mentsample={ments[:5]}")
                        dumped += 1
                    cands = score(blob, base, bands, locks)
                    for c in cands:
                        c["anchor"] = abs_hit
                        c["kind"] = kind
                        c["uid_rel"] = c["abs"] - abs_hit if kind == "uid" else None
                        c["job_rel"] = c["abs"] - abs_hit if kind == "job" else None
                        # nearest mental
                        nearest = min(ments, key=lambda t: abs((base + t[0]) - c["abs"]))
                        c["ment_rel"] = c["abs"] - (base + nearest[0])
                        c["ment_mode"] = nearest[1]
                        scored.append(c)

            uniq = {(c["abs"], c["order"]): c for c in scored}
            ranked = list(uniq.values())
            ranked.sort(key=lambda c: (
                0 if c["order"] in ("cm_from_loy", "classic_pers", "cm_full") else 1,
                abs(c["ment_rel"]),
            ))
            all_scored[name] = ranked
            lines.append(f"  HA_cands={len(ranked)}")
            for c in ranked[:15]:
                lines.append(
                    f"    {c['order']} ment_rel={c['ment_rel']} mode={c['ment_mode']} "
                    f"kind={c['kind']} {c['full']}"
                )

        # shared layout
        lines.append("\n=== shared uid_rel ===")
        locked = None
        for ord_name in ORDERS:
            maps = {}
            for name, ranked in all_scored.items():
                m = {}
                for c in ranked:
                    if c["order"] == ord_name and c["kind"] == "uid" and c["uid_rel"] is not None:
                        m[c["uid_rel"]] = c
                maps[name] = m
            shared = set.intersection(*(set(maps[n]) for n in PLAYERS if maps[n])) if all(maps[n] for n in PLAYERS) else set()
            # trio at least
            trio = set(maps["kizza"]) & set(maps["paco"]) & set(maps["tassinari"])
            lines.append(f"{ord_name}: trio={len(trio)} all5={len(shared)}")
            target = shared or trio
            for rel in sorted(target, key=abs)[:12]:
                lines.append(f"  rel={rel}")
                snap = {}
                for name in PLAYERS:
                    if rel in maps[name]:
                        lines.append(f"    {name}: {maps[name][rel]['full']}")
                        snap[name] = maps[name][rel]["full"]
                if len(snap) == 5 and locked is None:
                    locked = {"rel_to_uid": rel, "order": ord_name, "players": {
                        n: {k: v for k, v in vals.items() if k in bands_for(n, cal, PLAYERS)}
                        for n, vals in snap.items()
                    }}
                    # simpler store full
                    locked = {"mode": "shared_uid_rel", "rel_to_uid": rel, "order": ord_name,
                              "players": {n: maps[n][rel]["full"] for n in snap}}
                    lines.append("  *** LOCKED ***")

        if locked:
            LOCKS_OUT.write_text(json.dumps(locked, indent=2), encoding="utf-8")
            lines.append(f"wrote {LOCKS_OUT}")
        else:
            best = {}
            for name, ranked in all_scored.items():
                if ranked:
                    c = ranked[0]
                    best[name] = {
                        "order": c["order"],
                        "values": c["full"],
                        "ment_rel": c["ment_rel"],
                        "ment_mode": c["ment_mode"],
                        "abs": c["abs"],
                        "anchor": c["anchor"],
                        "kind": c["kind"],
                    }
                    lines.append(f"BEST {name}: {best[name]}")
            LOCKS_OUT.write_text(json.dumps({"mode": "per_player_best", "players": best}, indent=2), encoding="utf-8")
            lines.append(f"wrote {LOCKS_OUT}")
    finally:
        CloseHandle(h)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in (
            "uid=", "HA_cands=", "trio=", "LOCKED", "BEST ", "mental_pairs=", "wrote ",
            "rel=", "dumped ",
        )):
            print(line.encode("ascii", "replace").decode())
    return 0


def bands_for(name, cal, players):
    return cal[players[name]["uid"]]["bands"]


if __name__ == "__main__":
    raise SystemExit(main())
