#!/usr/bin/env python3
"""
Pointer-chase from live person directory objects (UID+name) to attr-rich heaps.

Goal: definite HA bytes for save pattern search.
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
OUT = ROOT / "tmp" / "fm-spike" / "ha-live-ptrchase.txt"
LOCKS_OUT = ROOT / "tmp" / "fm-spike" / "ha-live-locked.json"
DUMP_DIR = ROOT / "tmp" / "fm-spike" / "live-ptrchase"

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PLAYERS = {
    "kizza": {"uid": 2002185604, "job": 285346, "name": b"Kizza", "det": 16, "lea": 15},
    "paco": {"uid": 2000136577, "job": 106935, "name": b"Paco", "det": 19, "lea": 14},
    "tassinari": {"uid": 2002083070, "job": 182812, "name": b"Tassinari", "det": 15, "lea": 13},
    "seimen": {"uid": 2000175080, "job": 113517, "name": b"Seimen", "det": 18, "lea": 16},
    "yoan": {"uid": 2002089146, "job": 188888, "name": b"Yoan", "det": 15, "lea": 17},
}

HA_ORDERS = {
    "classic_pers": [
        "ambition", "loyalty", "pressure", "professionalism",
        "sportsmanship", "temperament", "controversy", "importantMatches",
    ],
    "user": [
        "professionalism", "pressure", "ambition", "importantMatches",
        "sportsmanship", "temperament", "loyalty", "controversy",
    ],
    "cm_staff": [
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
    if addr <= 0:
        return None
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


def find_person_objs(handle, uid: int, name: bytes, max_hits=6):
    pat = struct.pack("<I", uid)
    found = []
    for base, size in regions(handle):
        off = 0
        chunk = 4 << 20
        while off < size and len(found) < max_hits:
            n = min(chunk, size - off)
            data = read_mem(handle, base + off, n)
            if not data:
                off += n
                continue
            start = 0
            while True:
                j = data.find(pat, start)
                if j < 0:
                    break
                abs_addr = base + off + j
                window = data[j : j + 128]
                if len(window) < 64:
                    window = read_mem(handle, abs_addr, 128) or b""
                if name in window and len(window) >= 8 and window[4:8] == pat:
                    found.append(abs_addr)
                    if len(found) >= max_hits:
                        return found
                start = j + 1
            off += n
    return found


def is_ptr(v: int) -> bool:
    return 0x10000 < v < 0x7FFFFFFFFFFF and (v >> 48) == 0


def extract_ptrs(blob: bytes, base_abs: int):
    out = []
    for i in range(0, len(blob) - 7, 8):
        v = struct.unpack_from("<Q", blob, i)[0]
        if is_ptr(v):
            out.append((base_abs + i, v))
    # also unaligned 8-byte at 4
    for i in range(4, len(blob) - 7, 8):
        v = struct.unpack_from("<Q", blob, i)[0]
        if is_ptr(v):
            out.append((base_abs + i, v))
    # dedupe by target
    uniq = {}
    for src, tgt in out:
        uniq.setdefault(tgt, src)
    return [(src, tgt) for tgt, src in uniq.items()]


def has_det_lea(blob: bytes, det: int, lea: int) -> list[tuple[int, str]]:
    hits = []
    # raw contiguous & gap1/2
    for i in range(len(blob) - 1):
        if blob[i] == det and blob[i + 1] == lea:
            hits.append((i, "raw_adj"))
        if i + 2 < len(blob) and blob[i] == det and blob[i + 2] == lea:
            hits.append((i, "raw_gap2"))
    db, lb = det * 5, lea * 5
    for i in range(len(blob) - 1):
        if blob[i] == db and blob[i + 1] == lb:
            hits.append((i, "x5_adj"))
        if i + 2 < len(blob) and blob[i] == db and blob[i + 2] == lb:
            # reject common false positive: .. 5a 77 .. tags around 90/80
            if blob[i + 1] == 0x77:
                continue
            hits.append((i, "x5_gap2"))
    # int32
    dp = struct.pack("<I", det)
    lp = struct.pack("<I", lea)
    s = 0
    while True:
        j = blob.find(dp, s)
        if j < 0:
            break
        w = blob[j : j + 48]
        k = w.find(lp)
        if 0 < k <= 40:
            hits.append((j, f"i32_gap{k}"))
        s = j + 1
    return hits


def score_ha(blob, bands, locks, det):
    cands = []
    for oname, keys in HA_ORDERS.items():
        n = len(keys)
        for i in range(0, len(blob) - n + 1):
            raw = blob[i : i + n]
            if max(Counter(raw).values()) >= n - 1:
                continue
            ok = True
            vals = {}
            for j, k in enumerate(keys):
                v = raw[j]
                if not (1 <= v <= 20):
                    ok = False
                    break
                if k == "determination" and v != det:
                    ok = False
                    break
                if k == "adaptability":
                    vals[k] = v
                    continue
                if k in bands and not (bands[k][0] <= v <= bands[k][1]):
                    ok = False
                    break
                if k in locks and v != locks[k]:
                    ok = False
                    break
                if k in bands or k in locks:
                    vals[k] = v
            if not ok:
                continue
            sharp = any(
                (k in locks and raw[j] == locks[k])
                or (k in bands and bands[k][1] - bands[k][0] <= 4)
                for j, k in enumerate(keys)
            )
            if not sharp:
                continue
            cands.append({"order": oname, "off": i, "values": vals, "raw": list(raw)})
    return cands


def scan_i32_attrs(blob, bands, locks):
    """Search int32 LE arrays of personality attrs (1-20)."""
    # look for Pro=20 / Tem lock as i32
    cands = []
    keys_try = [
        ["professionalism", "pressure", "ambition", "importantMatches",
         "sportsmanship", "temperament", "loyalty", "controversy"],
        ["ambition", "loyalty", "pressure", "professionalism",
         "sportsmanship", "temperament", "controversy", "importantMatches"],
        ["loyalty", "pressure", "professionalism", "sportsmanship", "temperament"],
    ]
    for keys in keys_try:
        n = len(keys)
        for i in range(0, len(blob) - 4 * n + 1, 4):
            vals = []
            ok = True
            for j in range(n):
                v = struct.unpack_from("<I", blob, i + 4 * j)[0]
                if not (1 <= v <= 20):
                    ok = False
                    break
                vals.append(v)
            if not ok:
                continue
            mapped = dict(zip(keys, vals))
            good = True
            for k, v in mapped.items():
                if k in bands and not (bands[k][0] <= v <= bands[k][1]):
                    good = False
                    break
                if k in locks and v != locks[k]:
                    good = False
                    break
            if not good:
                continue
            sharp = any(
                (k in locks and mapped[k] == locks[k])
                or (k in bands and bands[k][1] - bands[k][0] <= 4)
                for k in keys if k in mapped
            )
            if sharp:
                cands.append({"order": "i32_" + keys[0], "off": i, "values": mapped, "raw": vals})
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
            locks = cal[meta["uid"]].get("locks") or {}
            print(f"chase {name}…", flush=True)
            lines.append(f"\n=== {name} locks={locks} ===")
            objs = find_person_objs(h, meta["uid"], meta["name"], max_hits=4)
            lines.append(f"  person_objs={len(objs)} {[hex(x) for x in objs]}")

            dest_scores = defaultdict(list)
            dumped = 0

            for obj in objs:
                # dump object neighborhood for pointers
                local = read_mem(h, obj - 64, 512)
                if not local:
                    continue
                ptrs = extract_ptrs(local, obj - 64)
                lines.append(f"  obj@{obj:#x} ptrs={len(ptrs)}")
                # also include nearby floating pointers that might be object fields
                # chase top ptrs + any containing jobId nearby in object
                job_pat = struct.pack("<I", meta["job"])
                if job_pat in local:
                    lines.append(f"    jobId in person obj at rel={local.find(job_pat)-64}")

                for src, tgt in ptrs[:40]:
                    # read pointed object
                    target = read_mem(h, tgt - 64, 2048)
                    if not target:
                        continue
                    ments = has_det_lea(target, meta["det"], meta["lea"])
                    has_lock = False
                    if "temperament" in locks and locks["temperament"] in target[64:64+512]:
                        has_lock = True
                    if "professionalism" in locks and locks["professionalism"] in target[64:64+512]:
                        has_lock = True

                    ha = score_ha(target, bands, locks, meta["det"])
                    ha32 = scan_i32_attrs(target, bands, locks)

                    if not ments and not ha and not ha32:
                        continue

                    score = len(ments) * 2 + len(ha) + len(ha32) * 3 + (5 if has_lock else 0)
                    # prefer destinations that also contain uid or job
                    uid_pat = struct.pack("<I", meta["uid"])
                    if uid_pat in target:
                        score += 10
                    if job_pat in target:
                        score += 8

                    dest_scores[tgt].append({
                        "score": score,
                        "src": src,
                        "obj": obj,
                        "ments": ments[:6],
                        "ha": ha[:4],
                        "ha32": ha32[:4],
                        "has_uid": uid_pat in target,
                        "has_job": job_pat in target,
                    })

                    if dumped < 6 and score >= 3:
                        path = DUMP_DIR / f"{name}_{tgt:x}.bin"
                        path.write_bytes(target)
                        lines.append(
                            f"    DEST@{tgt:#x} from={src:#x} score={score} "
                            f"ments={ments[:3]} ha={len(ha)} ha32={len(ha32)} "
                            f"uid={uid_pat in target} job={job_pat in target}"
                        )
                        for c in (ha[:2] + ha32[:2]):
                            lines.append(f"      {c['order']} @{c['off']} {c['values']}")
                        dumped += 1

            # pick best destination
            ranked = []
            for tgt, hits in dest_scores.items():
                best = max(hits, key=lambda x: x["score"])
                ranked.append((best["score"], tgt, best))
            ranked.sort(reverse=True)
            lines.append(f"  ranked_dests={len(ranked)}")
            for score, tgt, best in ranked[:8]:
                lines.append(
                    f"    score={score} dest={tgt:#x} ments={best['ments'][:2]} "
                    f"ha_n={len(best['ha'])} ha32_n={len(best['ha32'])} "
                    f"uid={best['has_uid']} job={best['has_job']}"
                )
                vals = None
                if best["ha32"]:
                    vals = best["ha32"][0]["values"]
                    enc = "i32"
                elif best["ha"]:
                    vals = best["ha"][0]["values"]
                    enc = best["ha"][0]["order"]
                if vals and score >= 5:
                    locked[name] = {
                        "confidence": "high" if best["has_uid"] or best["has_job"] else "medium",
                        "dest": tgt,
                        "encoding": enc,
                        "values": vals,
                        "score": score,
                        "ments": best["ments"][:3],
                    }
                    lines.append(f"  LOCK {locked[name]}")
                    break

            if name not in locked:
                lines.append("  NO lock from pointer chase")

        payload = {
            "mode": "ptrchase",
            "players": locked,
            "note": "HA values chased from person UID+name objects via heap pointers",
        }
        LOCKS_OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        lines.append(f"\nwrote {LOCKS_OUT}")
    finally:
        CloseHandle(h)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in (
            "===", "person_objs", "DEST@", "LOCK ", "NO lock", "ranked",
            "score=", "wrote ", "jobId in",
        )):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
