"""Dump the 77-byte personIndex spreadsheet rows (Band/Mull/Seimen aligned)."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/person-index-rows.txt")

# personIndex value abs from prior hunt (where u32le index sits)
IDX_ABS = {
    "Patrick Bandeira": (1198, 206622),
    "Robert Müller": (1233, 209317),
    "Dennis Seimen": (1790, 252206),
}
STRIDE = 77
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}


def extract(abs_target: int, length: int, before: int = 0) -> bytes:
    start = abs_target - before
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
                if chunk_start < end and abs_base + len(block) > start:
                    lo = max(0, start - chunk_start)
                    hi = min(len(data), end - chunk_start)
                    already = len(buf)
                    want_from = start + already
                    lo2 = max(lo, want_from - chunk_start)
                    if lo2 < hi:
                        buf.extend(data[lo2:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= before + length:
                    break
        finally:
            reader.close()
    return bytes(buf)


def main() -> None:
    lines = []
    # Verify stride geometry
    b_idx, b_abs = IDX_ABS["Patrick Bandeira"]
    m_idx, m_abs = IDX_ABS["Robert Müller"]
    s_idx, s_abs = IDX_ABS["Dennis Seimen"]
    lines.append(f"stride check Mull-Band: {(m_abs - b_abs) / (m_idx - b_idx)}")
    lines.append(f"stride check Seim-Band: {(s_abs - b_abs) / (s_idx - b_idx)}")
    assert (m_abs - b_abs) == (m_idx - b_idx) * STRIDE
    assert (s_abs - b_abs) == (s_idx - b_idx) * STRIDE
    lines.append("STRIDE 77 CONFIRMED across all three\n")

    # Dump windows: 96 bytes before index through 96 after, aligned on index
    blobs = {}
    for name, (idx, abs_off) in IDX_ABS.items():
        blob = extract(abs_off, 160, before=96)
        blobs[name] = blob
        lines.append(f"======== {name} idx={idx} index@abs={abs_off} ========")
        lines.append(f"hex[-96..+64]: {blob.hex(' ')}")
        lines.append(f"u8: {list(blob)}")
        # mark index at offset 96 in blob
        lines.append(f"u32@+0(index)={struct.unpack_from('<I', blob, 96)[0]}")
        uid = PLAYERS[name]["uid"] & 0xFFFFFFFF
        uid_b = struct.pack("<I", uid)
        lines.append(f"UID in window: {blob.find(uid_b)}")
        lines.append("")

    # Find best row start: offset in [-96,0] relative to index where
    # the previous byte pattern suggests boundary, OR try all field_offs 0..76
    # and pick the one maximizing cross-player structure equality outside known diffs
    lines.append("======== find row-start (field offset of personIndex within 77B row) ========")
    # For each candidate field_off 0..76, row bytes = blob[96-field_off : 96-field_off+77]
    best = []
    for field_off in range(74):  # need 4 bytes for u32
        rows = {}
        ok = True
        for name, (idx, _) in IDX_ABS.items():
            blob = blobs[name]
            start = 96 - field_off
            if start < 0 or start + 77 > len(blob):
                ok = False
                break
            row = blob[start : start + 77]
            # personIndex must sit at field_off
            if struct.unpack_from("<I", row, field_off)[0] != idx:
                ok = False
                break
            rows[name] = row
        if not ok:
            continue
        # score: how many offsets are equal across all three
        eq = sum(
            1
            for i in range(77)
            if rows["Patrick Bandeira"][i]
            == rows["Robert Müller"][i]
            == rows["Dennis Seimen"][i]
        )
        best.append((eq, field_off, rows))
    best.sort(reverse=True)
    lines.append(f"top field_off by shared-equal bytes: {[(e, f) for e, f, _ in best[:8]]}")

    if best:
        eq, field_off, rows = best[0]
        lines.append(f"\nBEST field_off={field_off} equal-all={eq}/77")
        for name, row in rows.items():
            lines.append(f"\n{name} row:")
            lines.append(f"  hex: {row.hex(' ')}")
            lines.append(f"  u8:  {list(row)}")
            # annotate u32s
            for off in range(0, 74, 4):
                v = struct.unpack_from("<I", row, off)[0]
                lines.append(f"  u32@{off:02d}={v} (0x{v:08X})")
            for off in range(0, 76, 2):
                v = struct.unpack_from("<H", row, off)[0]
                if 1 <= v <= 200 or v in (0x076C,):
                    lines.append(f"  u16@{off:02d}={v}")

        # Diff Band vs Mull
        rb = rows["Patrick Bandeira"]
        rm = rows["Robert Müller"]
        rs = rows["Dennis Seimen"]
        lines.append("\nBand vs Mull byte diffs:")
        for i in range(77):
            if rb[i] != rm[i]:
                lines.append(f"  +{i}: B={rb[i]} M={rm[i]} S={rs[i]}")

        # table base estimate
        # index_abs = table_base + idx * 77 + field_off
        # table_base = index_abs - idx*77 - field_off
        table_base = b_abs - b_idx * STRIDE - field_off
        lines.append(f"\ntable_base (row0 start) ≈ {table_base}")
        # verify Seimen
        pred_s = table_base + s_idx * STRIDE + field_off
        lines.append(f"predict Seimen index abs={pred_s} actual={s_abs} ok={pred_s == s_abs}")

        # Dump neighboring rows (idx-1, idx, idx+1) for Bandeira
        lines.append("\n======== neighboring rows around Bandeira ========")
        for di in (-2, -1, 0, 1, 2):
            idx = b_idx + di
            abs_row = table_base + idx * STRIDE
            row = extract(abs_row, 77)
            idx_val = struct.unpack_from("<I", row, field_off)[0]
            lines.append(
                f"  idx={idx} (expect {idx_val}) abs={abs_row} hex={row.hex(' ')}"
            )

        # Search for UniqueID of Bandeira in a wider range after table_base
        # Maybe this row points elsewhere via an embedded id
        lines.append("\n======== embedded ids in best rows ========")
        for name, row in rows.items():
            p = PLAYERS[name]
            lines.append(f"{name}:")
            # any byte sequence matching det/lea?
            for off in range(77):
                if row[off] == p["det"]:
                    lines.append(f"  det={p['det']} at +{off}")
                if row[off] == p["lea"]:
                    lines.append(f"  lea={p['lea']} at +{off}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii")[:10000])
    print(f"\n... wrote {OUT}")


if __name__ == "__main__":
    main()
