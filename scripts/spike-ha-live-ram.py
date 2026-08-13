#!/usr/bin/env python3
"""
Live FM process memory HA probe.

Opens fm.exe, finds UniqueID u32 hits, then scans neighborhoods for
classic/personality HA candidates (Pro=20, Tem=15, etc.).
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
OUT = ROOT / "tmp" / "fm-spike" / "ha-live-ram.txt"

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


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
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
ReadProcessMemory.restype = wintypes.BOOL

VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
VirtualQueryEx.restype = ctypes.c_size_t

CloseHandle = kernel32.CloseHandle

PLAYERS = {
    "kizza": 2002185604,
    "paco": 2000136577,
    "tassinari": 2002083070,
    "seimen": 2000175080,
    "yoan": 2002089146,
}


def find_pid() -> int:
    # Prefer PowerShell-style: enumerate via CreateToolhelp32Snapshot is heavy;
    # use tasklist via ctypes GetExitCode - simpler: parse from external already known.
    # We'll accept pid as argv or discover via EnumProcesses.
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    arr = (wintypes.DWORD * 4096)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(needed)):
        raise OSError("EnumProcesses failed")
    count = needed.value // ctypes.sizeof(wintypes.DWORD)
    for i in range(count):
        pid = arr[i]
        if not pid:
            continue
        h = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not h:
            continue
        try:
            buf = ctypes.create_unicode_buffer(260)
            # QueryFullProcessImageNameW
            size = wintypes.DWORD(260)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                path = buf.value.lower()
                if path.endswith("\\fm.exe") and "football manager" in path:
                    return pid
        finally:
            CloseHandle(h)
    raise RuntimeError("fm.exe not found")


def readable_regions(handle):
    address = 0
    mbi = MEMORY_BASIC_INFORMATION()
    # user-space up to 48-bit typically; stop at 0x7FFFFFFFFFFF
    max_addr = 0x7FFFFFFFFFFF
    while address < max_addr:
        got = VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi))
        if not got:
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if size == 0:
            break
        prot = mbi.Protect
        if (
            mbi.State == MEM_COMMIT
            and not (prot & PAGE_NOACCESS)
            and not (prot & PAGE_GUARD)
            and prot
            != 0
        ):
            # readable protections: PAGE_READONLY, READWRITE, EXECUTE_READ, EXECUTE_READWRITE
            if prot in (0x02, 0x04, 0x08, 0x20, 0x40, 0x80):
                yield base, size
        next_addr = base + size
        if next_addr <= address:
            break
        address = next_addr


def read_mem(handle, addr: int, size: int) -> bytes | None:
    buf = (ctypes.c_char * size)()
    read = ctypes.c_size_t(0)
    ok = ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(read))
    if not ok or read.value == 0:
        return None
    return bytes(buf[: read.value])


def scan_uid(handle, uid: int, max_hits: int = 30) -> list[int]:
    pat = struct.pack("<I", uid)
    hits = []
    for base, size in readable_regions(handle):
        # cap huge regions into chunks
        offset = 0
        chunk = 4 * 1024 * 1024
        while offset < size and len(hits) < max_hits:
            n = min(chunk, size - offset)
            data = read_mem(handle, base + offset, n)
            if data:
                start = 0
                while True:
                    j = data.find(pat, start)
                    if j < 0:
                        break
                    hits.append(base + offset + j)
                    if len(hits) >= max_hits:
                        return hits
                    start = j + 1
            offset += n
            # if region huge, also allow early exit after some hits found across regions
        if len(hits) >= max_hits:
            break
    return hits


def dump_around(handle, addr: int, before: int = 64, after: int = 192) -> bytes | None:
    return read_mem(handle, max(0, addr - before), before + after)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    try:
        pid = int(sys.argv[1]) if len(sys.argv) > 1 else find_pid()
    except Exception as e:
        lines.append(f"PID discover failed: {e}")
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return 1

    lines.append(f"pid={pid}")
    handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        err = ctypes.get_last_error()
        lines.append(f"OpenProcess failed last_error={err}")
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return 1

    try:
        # Region stats
        regions = list(readable_regions(handle))
        total = sum(s for _, s in regions)
        lines.append(f"readable_regions={len(regions)} bytes~={total}")

        hits = {}
        for name, uid in PLAYERS.items():
            print(f"scanning {name} uid={uid}…", flush=True)
            hs = scan_uid(handle, uid, max_hits=20)
            hits[name] = hs
            lines.append(f"{name}: hits={len(hs)} {hs[:8]}")

        any_hits = any(hits.values())
        if not any_hits:
            lines.append("No calibration UIDs found in FM26 memory.")
            lines.append("Likely a different save/career is loaded than the FM24 Schalke .fm.")
            # try UTF-16LE name fragments
            for label, needle in (
                ("Kizza", "Kizza".encode("utf-16le")),
                ("Seimen", "Seimen".encode("utf-16le")),
                ("Tassinari", "Tassinari".encode("utf-16le")),
            ):
                print(f"scanning name {label}…", flush=True)
                found = []
                for base, size in readable_regions(handle):
                    offset = 0
                    chunk = 2 * 1024 * 1024
                    while offset < size and len(found) < 5:
                        n = min(chunk, size - offset)
                        data = read_mem(handle, base + offset, n)
                        if data:
                            j = data.find(needle)
                            if j >= 0:
                                found.append(base + offset + j)
                        offset += n
                    if len(found) >= 5:
                        break
                lines.append(f"name[{label}] hits={found}")

        # For each hit, look for Pro=20 / Tem=15 near and classic 5-byte Loy..Tem
        lines.append("\n=== neighborhoods ===")
        for name, hs in hits.items():
            for h in hs[:6]:
                blob = dump_around(handle, h, 32, 128)
                if not blob:
                    continue
                lines.append(f"{name}@{h:#x}: {blob.hex(' ')}")
                # scan for value sequences
                for i in range(len(blob) - 4):
                    chunk = blob[i : i + 5]
                    if all(1 <= b <= 20 for b in chunk):
                        # interesting if contains 15 or 20
                        if 15 in chunk or 20 in chunk:
                            rel = i - 32
                            lines.append(f"  +{rel}: {list(chunk)}")

        # If paco and kizza both found, try shared relative Pro/Tem
        if hits.get("paco") and hits.get("kizza"):
            lines.append("\n=== shared rel Pro/Tem ===")
            for rel in range(-64, 128):
                for hp in hits["paco"][:8]:
                    bp = dump_around(handle, hp + rel, 0, 1)
                    if not bp or bp[0] != 20:
                        continue
                    for hk in hits["kizza"][:8]:
                        bk = dump_around(handle, hk + rel, 0, 1)
                        if not bk:
                            continue
                        # Tem often different offset — try same rel and rel+2
                        for gap in (0, 1, 2, 3, 4, 5):
                            bt = dump_around(handle, hk + rel + gap, 0, 1)
                            if bt and bt[0] == 15:
                                lines.append(
                                    f"  pacoPro@{hp:#x}+{rel}=20 kizzaTem@{hk:#x}+{rel}+{gap}=15"
                                )
    finally:
        CloseHandle(handle)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
