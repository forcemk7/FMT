"""Dump 77-byte personIndex spreadsheet rows (type tag may vary)."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/person-index-sheet.txt")

IDX = {
    "Patrick Bandeira": (1198, 206622),
    "Robert Müller": (1233, 209317),
    "Dennis Seimen": (1790, 252206),
}
STRIDE = 77
FIELD_OFF = 4  # row starts 4 bytes before personIndex


def extract(abs_target: int, length: int) -> bytes:
    end = abs_target + length
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        buf = bytearray()
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                chunk_start = abs_base - len(carry)
                if chunk_start < end and abs_base + len(block) > abs_target:
                    lo = max(0, abs_target - chunk_start)
                    hi = min(len(data), end - chunk_target if False else end - chunk_start)
                    already = len(buf)
                    want_from = abs_target + already
                    lo2 = max(lo, want_from - chunk_start)
                    if lo2 < hi:
                        buf.extend(data[lo2:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= length:
                    break
        finally:
            reader.close()
    return bytes(buf)


def main() -> None:
    # fix extract - I introduced a typo; rewrite cleanly
    pass


if __name__ == "__main__":
    # inline clean extract to avoid typo leftovers
    def extract2(abs_target: int, length: int) -> bytes:
        end = abs_target + length
        with SAVE.open("rb") as f:
            f.seek(26)
            reader = zstd.ZstdDecompressor().stream_reader(f)
            abs_base = 0
            carry = b""
            buf = bytearray()
            try:
                while True:
                    try:
                        block = reader.read(8 * 1024 * 1024)
                    except zstd.ZstdError:
                        break
                    if not block:
                        break
                    data = carry + block
                    chunk_start = abs_base - len(carry)
                    if chunk_start < end and abs_base + len(block) > abs_target:
                        lo = max(0, abs_target - chunk_start)
                        hi = min(len(data), end - chunk_start)
                        already = len(buf)
                        want_from = abs_target + already
                        lo2 = max(lo, want_from - chunk_start)
                        if lo2 < hi:
                            buf.extend(data[lo2:hi])
                    abs_base += len(block)
                    carry = data[-64:]
                    if len(buf) >= length:
                        break
            finally:
                reader.close()
        return bytes(buf)

    lines = []
    b_idx, b_abs = IDX["Patrick Bandeira"]
    table_base = b_abs - FIELD_OFF - b_idx * STRIDE
    lines.append(f"STRIDE={STRIDE} FIELD_OFF={FIELD_OFF} table_base={table_base}")
    lines.append(
        "Row: [4-byte type][personIndex u32][poolId u32][poolId u32][payload…]\n"
        "Note: type is often 01 00 6c 07 but Müller uses b6 00 e1 07 — same grid.\n"
    )

    players = {
        p["name"]: p
        for p in json.loads(
            Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
        )
    }

    rows: dict[str, tuple[int, bytes]] = {}
    for name, (idx, abs_idx) in IDX.items():
        row_abs = abs_idx - FIELD_OFF
        row = extract2(row_abs, STRIDE)
        assert struct.unpack_from("<I", row, 4)[0] == idx, name
        rows[name] = (row_abs, row)
        type_u32 = struct.unpack_from("<I", row, 0)[0]
        pool = struct.unpack_from("<I", row, 8)[0]
        pool2 = struct.unpack_from("<I", row, 12)[0]
        lines.append(f"## {name} idx={idx} row@{row_abs}")
        lines.append(
            f"  type=0x{type_u32:08X} ({row[:4].hex(' ')}) "
            f"poolId={pool} (0x{pool:08X}) dup={pool == pool2}"
        )
        lines.append(f"  hex: {row.hex(' ')}")
        lines.append(f"  u8:  {list(row)}")
        for off in range(16, 74, 4):
            lines.append(f"  u32+{off:02d}={struct.unpack_from('<I', row, off)[0]}")
        lines.append("")

    rb, rm, rs = rows["Patrick Bandeira"][1], rows["Robert Müller"][1], rows["Dennis Seimen"][1]
    lines.append("diffs Band vs Mull:")
    for i in range(STRIDE):
        if rb[i] != rm[i]:
            lines.append(f"  +{i:02d}: B={rb[i]:3d} M={rm[i]:3d} S={rs[i]:3d}")
    shared = [i for i in range(STRIDE) if rb[i] == rm[i] == rs[i]]
    lines.append(f"shared-equal: {len(shared)} offs {shared}")

    lines.append("\n======== neighbors Bandeira idx±2 ========")
    for di in range(-2, 3):
        idx = b_idx + di
        row_abs = table_base + idx * STRIDE
        row = extract2(row_abs, STRIDE)
        got = struct.unpack_from("<I", row, 4)[0]
        pool = struct.unpack_from("<I", row, 8)[0]
        lines.append(
            f"  idx={idx} got={got} ok={got==idx} type={row[:4].hex(' ')} "
            f"pool=0x{pool:08X} row@{row_abs}"
        )

    # Chase poolIds
    lines.append("\n======== poolId → UniqueID proximity ========")
    for name, (_row_abs, row) in rows.items():
        pool = struct.unpack_from("<I", row, 8)[0]
        uid = struct.pack("<I", players[name]["uid"] & 0xFFFFFFFF)
        pool_b = struct.pack("<I", pool)
        hits = []
        abs_base = 0
        carry = b""
        with SAVE.open("rb") as f:
            f.seek(26)
            reader = zstd.ZstdDecompressor().stream_reader(f)
            try:
                while len(hits) < 6:
                    try:
                        block = reader.read(8 * 1024 * 1024)
                    except zstd.ZstdError:
                        break
                    if not block:
                        break
                    data = carry + block
                    start = 0
                    while len(hits) < 6:
                        i = data.find(pool_b, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        win = data[max(0, i - 48) : i + 80]
                        base = i - max(0, i - 48)
                        urel = win.find(uid)
                        if urel >= 0:
                            hits.append((abs_off, urel - base))
                        start = i + 1
                    abs_base += len(block)
                    carry = data[-120:]
            finally:
                reader.close()
        lines.append(f"{name} pool=0x{pool:08X}: uid-near hits={hits}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines).encode("ascii", "replace").decode("ascii")[:8000])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
