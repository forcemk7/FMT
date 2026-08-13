#!/usr/bin/env python3
"""
Live FM HA hunt (UID-first, fast):
1) Find UniqueID hits
2) In ±8KB window look for Det*5 + Lea*5 mental pair
3) Score personality HA packs in that window
4) Emit locked values JSON for save-file pattern search
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
OUT = ROOT / "tmp" / "fm-spike" / "ha-live-attr-objs.txt"
LOCKS_OUT = ROOT / "tmp" / "fm-spike" / "ha-live-locked.json"

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


def read_mem(handle, addr: int, size: int) -> bytes | None:
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


def collect_uid_hits(handle, uid: int, limit=40) -> list[int]:
    pat = struct.pack("<I", uid)
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


def ok_ha(raw, keys, bands, locks):
    for i, key in enumerate(keys):
        v = raw[i]
        if key not in bands:
            if not (1 <= v <= 20):
                return False
            continue
        if not (1 <= v <= 20) or not in_band(v, bands[key]):
            return False
        if key in locks and v != locks[key]:
            return False
    return True


def find_mental_in_window(blob: bytes, det: int, lea: int) -> list[int]:
    """Offsets in blob where Det*5 and Lea*5 sit 2 apart (standard mental layout: det, flair, lea)."""
    det_b, lea_b = det * 5, lea * 5
    hits = []
    # exact classic gap: det at i, lea at i+2
    for i in range(0, len(blob) - 2):
        if blob[i] == det_b and blob[i + 2] == lea_b:
            hits.append(i)
    # also allow within ±8 unordered
    if not hits:
        for i in range(len(blob)):
            if blob[i] != det_b:
                continue
            for j in range(max(0, i - 8), min(len(blob), i + 9)):
                if j != i and blob[j] == lea_b:
                    hits.append(i)
                    break
    return hits


def score_window(blob, abs_base, bands, locks):
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
                    "values": dict(zip(keys, list(raw))),
                    "raw": list(raw),
                })
    return out


def main() -> int:
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 13220
    cal = {p["uid"]: p for p in json.loads(CAL.read_text(encoding="utf-8"))["players"]}
    lines = [f"pid={pid}"]
    OUT.parent.mkdir(parents=True, exist_ok=True)

    h = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print(f"OpenProcess failed {ctypes.get_last_error()}")
        return 1

    all_scored = {}
    try:
        for name, meta in PLAYERS.items():
            bands = cal[meta["uid"]]["bands"]
            locks = cal[meta["uid"]].get("locks") or {}
            print(f"UID scan {name}…", flush=True)
            hits = collect_uid_hits(h, meta["uid"], limit=35)
            lines.append(f"\n=== {name} uidHits={len(hits)} ===")

            scored = []
            ment_hits = 0
            for uid_abs in hits:
                # window around UID
                blob = read_mem(h, uid_abs - 2048, 8192)
                if not blob:
                    continue
                base = uid_abs - 2048
                ments = find_mental_in_window(blob, meta["det"], meta["lea"])
                if not ments:
                    continue
                ment_hits += 1
                for ment_off in ments[:3]:
                    # also check jobId nearby
                    job_pat = struct.pack("<I", meta["job"])
                    has_job = job_pat in blob
                    cands = score_window(blob, base, bands, locks)
                    for c in cands:
                        c["uid_abs"] = uid_abs
                        c["ment_abs"] = base + ment_off
                        c["uid_rel"] = c["abs"] - uid_abs
                        c["ment_rel"] = c["abs"] - (base + ment_off)
                        c["has_job"] = has_job
                        scored.append(c)
            lines.append(f"  uid-windows with Det/Lea={ment_hits} HA_cands={len(scored)}")

            # unique by abs+order
            uniq = {}
            for c in scored:
                uniq[(c["abs"], c["order"])] = c
            ranked = list(uniq.values())
            # prefer has_job, then cm_from_loy/classic, then closer to ment
            ranked.sort(key=lambda c: (
                0 if c["has_job"] else 1,
                0 if c["order"] in ("cm_from_loy", "classic_pers") else 1,
                abs(c["ment_rel"]),
                abs(c["uid_rel"]),
            ))
            all_scored[name] = ranked
            for c in ranked[:20]:
                lines.append(
                    f"  {c['order']} uid_rel={c['uid_rel']} ment_rel={c['ment_rel']} "
                    f"job={c['has_job']} {c['values']}"
                )

        # Shared uid_rel across players
        lines.append("\n=== shared uid_rel (same order) ===")
        locked = None
        for ord_name in ORDERS:
            maps = {}
            for name, ranked in all_scored.items():
                m = {}
                for c in ranked:
                    if c["order"] == ord_name:
                        m[c["uid_rel"]] = c
                maps[name] = m
            shared = set(maps["kizza"]) & set(maps["paco"]) & set(maps["tassinari"])
            if "seimen" in maps and maps["seimen"]:
                shared5 = shared & set(maps["seimen"]) & set(maps["yoan"])
            else:
                shared5 = set()
            lines.append(f"order={ord_name} trio_shared={len(shared)} all5_shared={len(shared5)}")
            for rel in sorted(shared5 or shared, key=abs)[:15]:
                lines.append(f"  rel={rel}")
                names = ["kizza", "paco", "tassinari"] + (["seimen", "yoan"] if rel in shared5 else [])
                snap = {}
                for name in names:
                    if rel in maps[name]:
                        c = maps[name][rel]
                        lines.append(f"    {name}: {c['values']}")
                        snap[name] = c["values"]
                if len(snap) == 5 and locked is None:
                    locked = {"rel_to_uid": rel, "order": ord_name, "players": snap}
                    lines.append("  *** LOCKED all5 ***")

        # Shared ment_rel
        lines.append("\n=== shared ment_rel (same order) ===")
        for ord_name in ORDERS:
            maps = {}
            for name, ranked in all_scored.items():
                m = {}
                for c in ranked:
                    if c["order"] == ord_name:
                        m[c["ment_rel"]] = c
                maps[name] = m
            shared = set(maps["kizza"]) & set(maps["paco"]) & set(maps["tassinari"])
            shared5 = shared & set(maps.get("seimen", {})) & set(maps.get("yoan", {})) if shared else set()
            lines.append(f"order={ord_name} trio_shared={len(shared)} all5_shared={len(shared5)}")
            for rel in sorted(shared5 or shared, key=abs)[:10]:
                lines.append(f"  mrel={rel}")
                names = ["kizza", "paco", "tassinari"] + (["seimen", "yoan"] if rel in shared5 else [])
                snap = {}
                for name in names:
                    if rel in maps[name]:
                        lines.append(f"    {name}: {maps[name][rel]['values']}")
                        snap[name] = maps[name][rel]["values"]
                if len(snap) == 5 and locked is None:
                    locked = {"rel_to_mental": rel, "order": ord_name, "players": snap}
                    lines.append("  *** LOCKED all5 ***")

        # Emit best available
        if locked:
            LOCKS_OUT.write_text(json.dumps({"mode": "shared_layout", **locked}, indent=2), encoding="utf-8")
            lines.append(f"\nwrote shared lock -> {LOCKS_OUT}")
        else:
            best = {}
            for name, ranked in all_scored.items():
                if ranked:
                    best[name] = {
                        "order": ranked[0]["order"],
                        "values": ranked[0]["values"],
                        "uid_rel": ranked[0]["uid_rel"],
                        "ment_rel": ranked[0]["ment_rel"],
                        "abs": ranked[0]["abs"],
                        "uid_abs": ranked[0]["uid_abs"],
                    }
                    lines.append(f"BEST {name}: {best[name]}")
            payload = {"mode": "per_player_best", "players": best}
            LOCKS_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            lines.append(f"\nwrote per-player best -> {LOCKS_OUT}")

    finally:
        CloseHandle(h)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in (
            "uidHits=", "Det/Lea=", "shared=", "LOCKED", "BEST ", "wrote ",
            "trio_shared=", "all5_shared=", "rel=", "mrel=",
        )):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
