#!/usr/bin/env python3
"""
Find live FM person objects (UID + name nearby) and probe for HA blocks.
"""

from __future__ import annotations

import ctypes
import struct
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "ha-live-person-objs.txt"

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PLAYERS = {
    "kizza": (2002185604, b"Kizza"),
    "paco": (2000136577, b"Paco"),  # common name may be Paco
    "tassinari": (2002083070, b"Tassinari"),
    "seimen": (2000175080, b"Seimen"),
    "yoan": (2002089146, b"Robert"),  # Yoan Robert - Robert is common; also try Yoan
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


def find_person_objs(handle, uid: int, name: bytes, max_hits=8):
    """UID hits where name ASCII appears within +256 bytes."""
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
                # peek ahead for name
                window = data[j : j + 256]
                if len(window) < 64:
                    more = read_mem(handle, abs_addr, 256) or b""
                    window = more
                if name in window:
                    # prefer double-UID
                    is_double = len(window) >= 8 and window[4:8] == pat
                    found.append((abs_addr, is_double, window))
                    if len(found) >= max_hits:
                        return found
                start = j + 1
            off += n
    return found


def scan_ha_candidates(blob: bytes, base_rel: int = 0):
    """Find interesting 1-20 runs and classic packs."""
    out = []
    # classic from_loy 5 bytes
    for i in range(len(blob) - 4):
        pack = blob[i : i + 5]
        if all(1 <= b <= 20 for b in pack):
            # score: contains distinctive values
            if 15 in pack or 20 in pack or any(3 <= b <= 6 for b in pack):
                out.append(("run5", base_rel + i, list(pack)))
    # 8-byte personality-ish
    for i in range(len(blob) - 7):
        pack = blob[i : i + 8]
        if all(1 <= b <= 20 for b in pack) and (20 in pack or 15 in pack):
            out.append(("run8", base_rel + i, list(pack)))
    return out[:40]


def main() -> int:
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 13220
    lines = [f"pid={pid}"]
    h = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print(f"OpenProcess failed {ctypes.get_last_error()}")
        return 1
    try:
        objs = {}
        for name, (uid, needle) in PLAYERS.items():
            print(f"find person objs {name}…", flush=True)
            # also try alt needles
            needles = [needle]
            if name == "yoan":
                needles = [b"Yoan", b"Robert"]
            if name == "paco":
                needles = [b"Paco", b"Su"]
            hits = []
            for nd in needles:
                hits.extend(find_person_objs(h, uid, nd, max_hits=6))
            # dedupe by addr
            uniq = {}
            for addr, is_d, window in hits:
                uniq[addr] = (is_d, window)
            objs[name] = uniq
            lines.append(f"{name}: personObjs={len(uniq)}")
            for addr, (is_d, window) in list(uniq.items())[:4]:
                lines.append(f"  @{addr:#x} double={is_d}")
                # show ascii preview
                ascii_bits = "".join(chr(b) if 32 <= b < 127 else "." for b in window[:120])
                lines.append(f"    ascii={ascii_bits}")
                lines.append(f"    hex={window[:96].hex(' ')}")

        # Deep dump around best Seimen-like objects (double + name)
        lines.append("\n=== deep dumps (double+name) ===")
        for name, uniq in objs.items():
            best = [(a, w) for a, (d, w) in uniq.items() if d]
            if not best:
                best = [(a, w) for a, (d, w) in uniq.items()]
            for addr, _w in best[:2]:
                blob = read_mem(h, addr - 64, 512)
                if not blob:
                    continue
                lines.append(f"\n{name} deep@{addr:#x}")
                for i in range(0, len(blob), 32):
                    chunk = blob[i : i + 32]
                    rel = i - 64
                    hx = chunk.hex(" ")
                    asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                    lines.append(f"  {rel:+04d}: {hx}  {asc}")
                cands = scan_ha_candidates(blob, -64)
                lines.append(f"  candidates={cands[:20]}")

        # Cross: for each player's best double+name object, scan same relative
        # offsets for Pro/Tem locks
        lines.append("\n=== cross Pro/Tem on double+name objects ===")
        anchors = {}
        for name, uniq in objs.items():
            doubles = [a for a, (d, _) in uniq.items() if d]
            anchors[name] = doubles[0] if doubles else (next(iter(uniq)) if uniq else None)
        lines.append(f"anchors={ {k: (hex(v) if v else None) for k,v in anchors.items()} }")

        if anchors.get("paco") and anchors.get("kizza"):
            pb = read_mem(h, anchors["paco"] - 64, 512) or b""
            kb = read_mem(h, anchors["kizza"] - 64, 512) or b""
            for i in range(len(pb)):
                if pb[i] == 20:
                    for gap in range(0, 12):
                        j = i + gap
                        if j < len(kb) and kb[j] == 15:
                            # check tassinari if present
                            extra = ""
                            if anchors.get("tassinari"):
                                tb = read_mem(h, anchors["tassinari"] - 64, 512) or b""
                                if j < len(tb):
                                    extra = f" tass@same={tb[j]}"
                            lines.append(
                                f"  paco[+{i-64}]=20 kizza[+{j-64}]=15 gap={gap}{extra}"
                            )
    finally:
        CloseHandle(h)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(
            x in line
            for x in (
                "personObjs=",
                "double=",
                "ascii=",
                "anchors=",
                "paco[",
                "candidates=",
                "deep@",
            )
        ):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
