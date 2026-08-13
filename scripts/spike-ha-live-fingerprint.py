#!/usr/bin/env python3
"""
Global live-RAM fingerprint scan for definite HA anchors.

Start with Paco (Pro=20 lock + Det=19 + Lea=14) — most unique.
Then Kizza (Tem=15 + Det=16 + Lea=15), Seimen (Pro∈{18,19}+Det=18+Lea=16).
If a fingerprint resolves to a stable byte pack, lock HAs and write JSON for save search.
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
OUT = ROOT / "tmp" / "fm-spike" / "ha-live-fingerprint.txt"
LOCKS_OUT = ROOT / "tmp" / "fm-spike" / "ha-live-locked.json"
DUMP_DIR = ROOT / "tmp" / "fm-spike" / "live-fingerprint"

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PLAYERS = {
    "paco": {
        "uid": 2000136577, "job": 106935, "det": 19, "lea": 14,
        "locks": {"professionalism": 20},
    },
    "kizza": {
        "uid": 2002185604, "job": 285346, "det": 16, "lea": 15,
        "locks": {"temperament": 15},
    },
    "seimen": {
        "uid": 2000175080, "job": 113517, "det": 18, "lea": 16,
        "locks": {},
        "pro_band": (18, 19),
        "con_band": (1, 5),
    },
    "tassinari": {
        "uid": 2002083070, "job": 182812, "det": 15, "lea": 13,
        "locks": {},
        "tem_band": (3, 6),
        "con_band": (15, 20),
        "spo_band": (1, 7),
    },
    "yoan": {
        "uid": 2002089146, "job": 188888, "det": 15, "lea": 17,
        "locks": {},
        "pre_band": (17, 19),
    },
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


def scan_fingerprint(handle, check_fn, limit=80):
    """Walk all committed memory; check_fn(blob)->list of (off, meta)."""
    hits = []
    for base, size in regions(handle):
        off = 0
        chunk = 2 << 20
        while off < size and len(hits) < limit:
            n = min(chunk, size - off)
            data = read_mem(handle, base + off, n)
            if data:
                for local_off, meta in check_fn(data):
                    hits.append((base + off + local_off, meta, data[max(0, local_off - 32): local_off + 64]))
                    if len(hits) >= limit:
                        return hits
            off += n
    return hits


def paco_checks(blob: bytes):
    """
    Paco fingerprints (prefer unique int32 / x5 over raw bytes — less noise):
    B) int32 Pro=20 + Det=19 + Lea=14 within ±64
    C) x5 bytes Pro=100 + Det=95 + Lea=70 within ±48
    A) raw Pro=20 with Det/Lea as int32 nearby (hybrid)
    """
    out = []
    pro = struct.pack("<I", 20)
    det = struct.pack("<I", 19)
    lea = struct.pack("<I", 14)
    s = 0
    while True:
        j = blob.find(pro, s)
        if j < 0:
            break
        if j % 4 == 0:
            win = blob[max(0, j - 64): j + 64]
            if det in win and lea in win:
                dens = sum(
                    1 for k in range(0, len(win) - 3, 4)
                    if 1 <= struct.unpack_from("<I", win, k)[0] <= 20
                )
                if dens >= 5:
                    out.append((j, {
                        "enc": "i32",
                        "pro_off": j,
                        "dens": dens,
                        "det_rel": win.find(det) - (j - max(0, j - 64)),
                        "lea_rel": win.find(lea) - (j - max(0, j - 64)),
                    }))
        s = j + 4
    # x5 contiguous-ish
    for i in range(0, len(blob) - 1):
        if blob[i] != 100:
            continue
        lo = max(0, i - 48)
        hi = min(len(blob), i + 48)
        win = blob[lo:hi]
        if 95 in win and 70 in win:
            # require several multiples-of-5 in 5..100 (CA-style)
            m5 = sum(1 for b in win if 5 <= b <= 100 and b % 5 == 0)
            if m5 >= 6:
                out.append((i, {"enc": "x5", "pro_off": i, "m5": m5}))
    return out


def kizza_checks(blob: bytes):
    """Tem=15, Det=16, Lea=15 — carefully (15 appears twice)."""
    out = []
    # i32: temperament=15 AND determination=16 nearby, leadership=15
    tem = struct.pack("<I", 15)
    det = struct.pack("<I", 16)
    s = 0
    while True:
        j = blob.find(det, s)
        if j < 0:
            break
        win = blob[max(0, j - 64): j + 80]
        # need two 15s (lea+tem) or lea adj
        if win.count(tem) >= 1 and struct.pack("<I", 15) in win:
            # also require another attr-like int32 in 1..20 densely
            dens = 0
            base = max(0, j - 64)
            for k in range(0, len(win) - 3, 4):
                v = struct.unpack_from("<I", win, k)[0]
                if 1 <= v <= 20:
                    dens += 1
            if dens >= 6:
                out.append((j, {"enc": "i32_dense", "det_off": j, "dens": dens}))
        s = j + 4
    # raw: 16 and 15 gap2 (det/lea) near another 15 (tem)
    for i in range(len(blob) - 2):
        if blob[i] == 16 and blob[i + 2] == 15:
            lo = max(0, i - 32)
            hi = min(len(blob), i + 48)
            win = blob[lo:hi]
            if win.count(15) >= 2 and 20 >= max(win) if win else False:
                # at least some 1-20 diversity
                vals = [b for b in win if 1 <= b <= 20]
                if len(set(vals)) >= 5:
                    out.append((i, {"enc": "raw_gap2_dense", "dens": len(set(vals))}))
    return out


def seimen_checks(blob: bytes):
    out = []
    det = struct.pack("<I", 18)
    lea = struct.pack("<I", 16)
    for pro in (18, 19):
        pp = struct.pack("<I", pro)
        s = 0
        while True:
            j = blob.find(pp, s)
            if j < 0:
                break
            win = blob[max(0, j - 64): j + 80]
            if det in win and lea in win:
                dens = sum(
                    1 for k in range(0, len(win) - 3, 4)
                    if 1 <= struct.unpack_from("<I", win, k)[0] <= 20
                )
                if dens >= 6:
                    # controversy 1-5 present?
                    con = any(
                        1 <= struct.unpack_from("<I", win, k)[0] <= 5
                        for k in range(0, len(win) - 3, 4)
                    )
                    out.append((j, {"enc": "i32", "pro": pro, "dens": dens, "con_slot": con}))
            s = j + 4
    return out


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
}


def decode_near(blob, center, bands, locks, enc_hint):
    cands = []
    # raw packs
    for oname, keys in ORDERS.items():
        n = len(keys)
        lo = max(0, center - 64)
        hi = min(len(blob) - n + 1, center + 64)
        for i in range(lo, hi):
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
                if k in bands and not (bands[k][0] <= v <= bands[k][1]):
                    ok = False
                    break
                if k in locks and v != locks[k]:
                    ok = False
                    break
                vals[k] = v
            if ok:
                cands.append({"order": oname, "enc": "u8", "rel": i - center, "values": vals})
    # i32 packs
    for oname, keys in ORDERS.items():
        n = len(keys)
        lo = max(0, (center - 64) // 4 * 4)
        hi = min(len(blob) - 4 * n + 1, center + 64)
        for i in range(lo, hi, 4):
            vals_l = []
            ok = True
            for j in range(n):
                v = struct.unpack_from("<I", blob, i + 4 * j)[0]
                if not (1 <= v <= 20):
                    ok = False
                    break
                vals_l.append(v)
            if not ok:
                continue
            mapped = dict(zip(keys, vals_l))
            good = True
            for k, v in mapped.items():
                if k in bands and not (bands[k][0] <= v <= bands[k][1]):
                    good = False
                    break
                if k in locks and v != locks[k]:
                    good = False
                    break
            if good:
                cands.append({"order": oname, "enc": "i32", "rel": i - center, "values": mapped})
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

    checkers = {
        "paco": paco_checks,
        "kizza": kizza_checks,
        "seimen": seimen_checks,
    }
    locked = {}
    try:
        for name, checker in checkers.items():
            print(f"fingerprint {name}…", flush=True)
            meta = PLAYERS[name]
            bands = cal[meta["uid"]]["bands"]
            locks = cal[meta["uid"]].get("locks") or {}
            hits = scan_fingerprint(h, checker, limit=60)
            lines.append(f"\n=== {name} fingerprint_hits={len(hits)} ===")
            enc_counts = Counter(m["enc"] for _, m, _ in hits)
            lines.append(f"  by_enc: {dict(enc_counts)}")

            # Prefer hits that also contain uid or job nearby when we re-read
            rich = []
            dumped = 0
            for abs_off, meta_h, snippet in hits:
                blob = read_mem(h, abs_off - 128, 512)
                if not blob:
                    continue
                uid_pat = struct.pack("<I", meta["uid"])
                job_pat = struct.pack("<I", meta["job"])
                has_uid = uid_pat in blob
                has_job = job_pat in blob
                cands = decode_near(blob, 128, bands, locks, meta_h["enc"])
                score = len(cands) + (20 if has_uid else 0) + (10 if has_job else 0)
                if meta_h["enc"] == "i32":
                    score += 3
                if cands or has_uid or has_job:
                    rich.append((score, abs_off, meta_h, cands, has_uid, has_job, blob))
                if dumped < 3 and (cands or has_uid):
                    (DUMP_DIR / f"{name}_{abs_off:x}.bin").write_bytes(blob)
                    lines.append(
                        f"  @{abs_off:#x} enc={meta_h['enc']} score={score} "
                        f"uid={has_uid} job={has_job} ha_cands={len(cands)}"
                    )
                    for c in cands[:3]:
                        lines.append(f"    {c}")
                    dumped += 1

            rich.sort(reverse=True, key=lambda t: t[0])
            lines.append(f"  rich={len(rich)}")
            if rich and rich[0][0] >= 3 and rich[0][3]:
                score, abs_off, meta_h, cands, has_uid, has_job, blob = rich[0]
                best = cands[0]
                locked[name] = {
                    "confidence": "high" if has_uid or has_job else "medium",
                    "abs": abs_off,
                    "fingerprint": meta_h,
                    "values": best["values"],
                    "order": best["order"],
                    "enc": best["enc"],
                    "ha_rel": best["rel"],
                    "has_uid": has_uid,
                    "has_job": has_job,
                    "score": score,
                }
                lines.append(f"  LOCK {locked[name]}")
            elif rich:
                lines.append(f"  best_score={rich[0][0]} but no HA decode; meta={rich[0][2]}")
                # still dump context hex
                _, abs_off, meta_h, _, has_uid, has_job, blob = rich[0]
                lines.append(f"  ctx@{abs_off:#x}: {blob[96:160].hex(' ')}")
            else:
                lines.append("  no rich hits")

        payload = {
            "mode": "fingerprint",
            "players": locked,
            "note": "Global fingerprint (Pro/Det/Lea co-location) then HA pack decode",
        }
        LOCKS_OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        lines.append(f"\nwrote {LOCKS_OUT}")
    finally:
        CloseHandle(h)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in (
            "===", "by_enc", "LOCK ", "rich=", "no rich", "best_score",
            "wrote ", "  @",
        )):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
