#!/usr/bin/env python3
"""
Tem=15 cohort hunt across save (+ optional live RAM).

Fixture: data/fixtures/ha-tem15-cohort.json (6 players, Tem locked 15).

Checks:
1) Double-UID loci — shared rel where byte==15 (raw) or ==75 (x5)
2) All single-UID hits — same shared-rel vote
3) Contiguous / interleaved packs with Tem=15 at shared layout
4) Optional: live RAM if fm.exe PID given
"""

from __future__ import annotations

import ctypes
import json
import mmap
import os
import struct
import sys
import tempfile
from collections import Counter, defaultdict
from ctypes import wintypes
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
COHORT = ROOT / "data" / "fixtures" / "ha-tem15-cohort.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-tem15-cohort.txt"
ZSTD_OFF = 26
TEM = 15
TEM_X5 = 75
WIN = 512  # bytes after UID / double

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-tem15-", suffix=".bin")
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


def find_all(mm, pat: bytes, limit=80) -> list[int]:
    hits = []
    j = mm.find(pat)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(pat, j + 1)
    return hits


def shared_tem_rels(windows: dict[str, bytes], value: int) -> list[tuple[int, int]]:
    """Return (rel, n_players) where every player's window has value at rel."""
    if not windows:
        return []
    # vote which rels have TEM for each player
    sets = []
    for blob in windows.values():
        rels = {i for i, b in enumerate(blob) if b == value}
        sets.append(rels)
    inter = set.intersection(*sets) if sets else set()
    # also majority (≥ n-1)
    counts: Counter[int] = Counter()
    for s in sets:
        for r in s:
            counts[r] += 1
    n = len(windows)
    out = []
    for rel, c in sorted(counts.items(), key=lambda t: (-t[1], t[0])):
        if c >= n - 1 and 0 <= rel < WIN:
            out.append((rel, c))
    # mark full intersection first
    full = [(r, n) for r in sorted(inter) if 0 <= r < WIN]
    # dedupe preferring full
    seen = set()
    ranked = []
    for r, c in full + out:
        if r in seen:
            continue
        seen.add(r)
        ranked.append((r, c))
    return ranked


def dump_hex(blob: bytes, mark_rels: set[int]) -> list[str]:
    lines = []
    for i in range(0, min(len(blob), 256), 16):
        chunk = blob[i : i + 16]
        parts = []
        for j, b in enumerate(chunk):
            rel = i + j
            s = f"{b:02x}"
            if rel in mark_rels:
                s = f"[{s}]"
            parts.append(s)
        lines.append(f"  +{i:03d}: {' '.join(parts)}")
    return lines


def scan_save(lines: list[str], players: list[dict]) -> dict:
    print("decompressing save…", flush=True)
    tmp = decompress(SAVE)
    result = {"double": {}, "single": {}, "shared_double_raw": [], "shared_double_x5": [],
              "shared_single_raw": [], "shared_single_x5": []}
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                lines.append(f"save_bytes={mm.size()}")
                double_windows = {}
                single_windows = {}  # best single hit per player (first / prefer double-like)

                for p in players:
                    uid = p["uid"]
                    name = p["name"]
                    dpat = struct.pack("<II", uid, uid)
                    spat = struct.pack("<I", uid)
                    doubles = find_all(mm, dpat, limit=20)
                    singles = find_all(mm, spat, limit=40)
                    lines.append(
                        f"\n=== {name} uid={uid} doubles={len(doubles)} singles={len(singles)} ==="
                    )
                    result["double"][name] = doubles
                    result["single"][name] = singles

                    if doubles:
                        dab = doubles[0]
                        blob = bytes(mm[dab : dab + WIN])
                        double_windows[name] = blob
                        tem_raw = [i for i, b in enumerate(blob) if b == TEM]
                        tem_x5 = [i for i, b in enumerate(blob) if b == TEM_X5]
                        lines.append(f"  double0@{dab} tem15_rels={tem_raw[:24]}")
                        lines.append(f"  double0@{dab} tem75_rels={tem_x5[:24]}")
                        lines.extend(dump_hex(blob, set(tem_raw[:16])))
                    else:
                        lines.append("  NO double-UID")

                    # pick single: prefer one that is also a double start, else first
                    pick = None
                    for s in singles:
                        if s in doubles or (s + 4) in doubles or any(abs(s - d) < 4 for d in doubles):
                            pick = s
                            break
                    if pick is None and singles:
                        pick = singles[0]
                    if pick is not None:
                        blob = bytes(mm[pick : pick + WIN])
                        single_windows[name] = blob
                        lines.append(
                            f"  single_pick@{pick} tem15={[i for i,b in enumerate(blob) if b==TEM][:16]}"
                        )

                # shared across double windows
                lines.append("\n=== SHARED tem at double-UID windows ===")
                if len(double_windows) >= 2:
                    for label, val, key in (
                        ("raw15", TEM, "shared_double_raw"),
                        ("x5_75", TEM_X5, "shared_double_x5"),
                    ):
                        ranked = shared_tem_rels(double_windows, val)
                        result[key] = ranked[:40]
                        full = [r for r, c in ranked if c == len(double_windows)]
                        lines.append(
                            f"{label}: players_with_double={len(double_windows)} "
                            f"full_shared={len(full)} top={ranked[:20]}"
                        )
                        for rel in full[:12]:
                            vals = {n: double_windows[n][rel] for n in double_windows}
                            # neighbors
                            neigh = {
                                n: list(double_windows[n][max(0, rel - 4) : rel + 5])
                                for n in double_windows
                            }
                            lines.append(f"  FULL rel=+{rel} bytes={vals}")
                            # show if neighborhood identical shape
                            shapes = {n: bytes(neigh[n]) for n in neigh}
                            uniq = len(set(shapes.values()))
                            lines.append(f"    neigh±4 unique_shapes={uniq}")
                            if uniq <= 3:
                                for n, b in list(shapes.items())[:3]:
                                    lines.append(f"    {n}: {b.hex(' ')}")
                else:
                    lines.append("too few double windows")

                lines.append("\n=== SHARED tem at single-UID windows ===")
                if len(single_windows) >= 4:
                    for label, val, key in (
                        ("raw15", TEM, "shared_single_raw"),
                        ("x5_75", TEM_X5, "shared_single_x5"),
                    ):
                        ranked = shared_tem_rels(single_windows, val)
                        result[key] = ranked[:40]
                        full = [r for r, c in ranked if c == len(single_windows)]
                        lines.append(
                            f"{label}: players={len(single_windows)} full_shared={len(full)} "
                            f"top={ranked[:16]}"
                        )
                        for rel in full[:15]:
                            lines.append(
                                f"  FULL rel=+{rel} "
                                f"{ {n: single_windows[n][rel] for n in single_windows} }"
                            )

                # Contiguous classic packs containing Tem=15 at same index across doubles
                lines.append("\n=== pack scan (Tem@index, shared across doubles) ===")
                orders = {
                    "classic": [
                        "ambition", "loyalty", "pressure", "professionalism",
                        "sportsmanship", "temperament", "controversy", "importantMatches",
                    ],
                    "user": [
                        "professionalism", "pressure", "ambition", "importantMatches",
                        "sportsmanship", "temperament", "loyalty", "controversy",
                    ],
                }
                if len(double_windows) >= 4:
                    for oname, keys in orders.items():
                        tem_i = keys.index("temperament")
                        n = len(keys)
                        # candidate start offs where every player has Tem=15 at start+tem_i
                        votes = Counter()
                        for name, blob in double_windows.items():
                            for start in range(0, len(blob) - n + 1):
                                if blob[start + tem_i] == TEM:
                                    raw = blob[start : start + n]
                                    if all(1 <= b <= 20 for b in raw) and len(set(raw)) >= 3:
                                        votes[start] += 1
                        ranked = votes.most_common(12)
                        lines.append(f"{oname}: top starts={ranked}")
                        for start, c in ranked:
                            if c < len(double_windows) - 1:
                                continue
                            lines.append(f"  start=+{start} hits={c}/{len(double_windows)}")
                            for name, blob in double_windows.items():
                                pack = list(blob[start : start + n])
                                lines.append(f"    {name}: {dict(zip(keys, pack))}")

                # Interleaved V 01 with value 15 shared
                lines.append("\n=== interleaved V|01 including Tem=15 ===")
                if double_windows:
                    for name, blob in double_windows.items():
                        found = []
                        for start in range(8, min(200, len(blob) - 2)):
                            seq = []
                            j = start
                            while j + 1 < len(blob) and blob[j + 1] == 0x01 and 1 <= blob[j] <= 20:
                                seq.append(blob[j])
                                j += 2
                                if len(seq) >= 10:
                                    break
                            if TEM in seq and len(seq) >= 4:
                                found.append((start, seq))
                        lines.append(f"{name}: interleaved_with_15={found[:6]}")

            finally:
                mm.close()
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
    return result


# --- optional RAM ---
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


def scan_ram(lines: list[str], players: list[dict], pid: int) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
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

    def collect_hits(handle, value, limit=25):
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

    h = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        lines.append(f"RAM OpenProcess failed err={ctypes.get_last_error()}")
        return
    lines.append(f"\n=== LIVE RAM pid={pid} ===")
    try:
        windows = {}
        for p in players:
            hits = collect_hits(h, p["uid"], limit=20)
            lines.append(f"{p['name']}: uid_hits={len(hits)}")
            # take first hit with Tem=15 in +WIN
            for abs_h in hits[:8]:
                blob = read_mem(h, abs_h, WIN)
                if not blob:
                    continue
                if TEM in blob or TEM_X5 in blob:
                    windows[p["name"]] = blob
                    lines.append(
                        f"  pick@{abs_h:#x} tem15={[i for i,b in enumerate(blob) if b==TEM][:12]}"
                    )
                    break
        lines.append("\n=== RAM SHARED tem ===")
        if len(windows) >= 4:
            for label, val in (("raw15", TEM), ("x5_75", TEM_X5)):
                ranked = shared_tem_rels(windows, val)
                full = [r for r, c in ranked if c == len(windows)]
                lines.append(f"{label}: n={len(windows)} full={len(full)} top={ranked[:16]}")
                for rel in full[:10]:
                    lines.append(f"  FULL +{rel}")
        else:
            lines.append(f"insufficient windows ({len(windows)})")
    finally:
        CloseHandle(h)


def main() -> int:
    players = json.loads(COHORT.read_text(encoding="utf-8"))["players"]
    lines = [f"cohort={len(players)} temperament_lock={TEM}"]
    OUT.parent.mkdir(parents=True, exist_ok=True)

    print("scanning save…", flush=True)
    result = scan_save(lines, players)

    pid = None
    if len(sys.argv) > 1:
        pid = int(sys.argv[1])
    else:
        # try find fm.exe
        try:
            import subprocess
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-Process fm -ErrorAction SilentlyContinue).Id"],
                text=True,
            ).strip()
            if out:
                pid = int(out.split()[0])
        except Exception:
            pid = None

    if pid:
        print(f"scanning RAM pid={pid}…", flush=True)
        scan_ram(lines, players, pid)
    else:
        lines.append("\n=== LIVE RAM skipped (no pid / fm not running) ===")

    # verdict
    lines.append("\n=== VERDICT ===")
    cold = True
    for key in ("shared_double_raw", "shared_double_x5", "shared_single_raw", "shared_single_x5"):
        full = [r for r, c in result.get(key, []) if c >= len(players) - 1]
        # for double may have fewer players if some lack doubles
        lines.append(f"{key}: candidates≥n-1 -> {full[:20]}")
        if full:
            cold = False
    if cold:
        lines.append(
            "COLD: no robust shared Tem=15 locus across the cohort at UID windows. "
            "Ready for Genie HA dump → exact-byte save/RAM search."
        )
    else:
        lines.append("WARM: shared Tem offsets found — inspect FULL rel dumps above.")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    # print summary
    for line in lines:
        if any(x in line for x in (
            "===", "doubles=", "NO double", "full_shared", "FULL rel",
            "VERDICT", "COLD", "WARM", "LIVE RAM", "top starts",
            "interleaved_with_15", "insufficient", "skipped",
        )):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
