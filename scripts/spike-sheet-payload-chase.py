"""poolId is sheet-local only. Chase nested payload IDs (+40/+44/+56) and
cross-check sheet fields against double-UID blobs."""

from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/sheet-payload-chase.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}

# Known sheet rows (start at type tag, 77 bytes)
ROWS = {
    "Patrick Bandeira": 206618,
    "Robert Müller": 209313,
    "Dennis Seimen": 252202,
}
DOUBLE = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}
STRIDE = 77


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


def stream_blocks():
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            reader.close()


def find_u32_near_uid(val: int, uid: int, window: int = 256, limit: int = 8) -> list:
    pat = struct.pack("<I", val & 0xFFFFFFFF)
    uid_b = struct.pack("<I", uid & 0xFFFFFFFF)
    hits = []
    abs_base = 0
    carry = b""
    for block in stream_blocks():
        data = carry + block
        start = 0
        while len(hits) < limit:
            i = data.find(uid_b, start)
            if i < 0:
                break
            win = data[max(0, i - window) : i + window]
            j = win.find(pat)
            if j >= 0:
                abs_off = abs_base - len(carry) + i
                hits.append(
                    {
                        "uid_abs": abs_off,
                        "val_rel": j - (i - max(0, i - window)),
                        "ctx": win[
                            max(0, j - 8) : j + 16
                        ].hex(" "),
                    }
                )
            start = i + 1
        abs_base += len(block)
        carry = data[-window - 8 :]
        if len(hits) >= limit:
            break
    return hits


def taxonomy_u32(val: int, limit: int = 20) -> dict:
    """Count hit neighborhoods for a u32 value."""
    pat = struct.pack("<I", val & 0xFFFFFFFF)
    kinds = Counter()
    samples = defaultdict(list)
    abs_base = 0
    carry = b""
    total = 0
    for block in stream_blocks():
        data = carry + block
        start = 0
        while total < 5000:  # safety
            i = data.find(pat, start)
            if i < 0:
                break
            total += 1
            win = data[max(0, i - 32) : i + 64]
            base = i - max(0, i - 32)
            if bytes.fromhex("01006c07") in win:
                kind = "near_6c07"
            elif bytes.fromhex("058c0c") in win:
                kind = "near_058c0c"
            elif win[base : base + 4] == win[base + 4 : base + 8]:
                kind = "dup_pair"
            else:
                kind = "other"
            kinds[kind] += 1
            if len(samples[kind]) < 3:
                abs_off = abs_base - len(carry) + i
                samples[kind].append((abs_off, win[base : base + 40].hex(" ")))
            start = i + 1
        abs_base += len(block)
        carry = data[-96:]
    return {"total": total, "kinds": dict(kinds), "samples": dict(samples)}


def main() -> None:
    lines = []
    lines.append(
        "POOLID IS SHEET-LOCAL (only appears as the dup pair in the 77B row).\n"
        "Chasing nested payload fields instead.\n"
    )

    rows = {}
    for name, abs_r in ROWS.items():
        row = extract(abs_r, STRIDE)
        rows[name] = row
        lines.append(f"## {name} row@{abs_r}")
        # Field map
        typ = struct.unpack_from("<I", row, 0)[0]
        idx = struct.unpack_from("<I", row, 4)[0]
        pool = struct.unpack_from("<I", row, 8)[0]
        f16 = struct.unpack_from("<I", row, 16)[0]
        # flags region
        lines.append(f"  type=0x{typ:08X} idx={idx} pool=0x{pool:08X}")
        lines.append(f"  +16..+23: {row[16:24].hex(' ')}")
        lines.append(f"  +24..+35: {row[24:36].hex(' ')}")
        lines.append(f"  +36..+51: {row[36:52].hex(' ')}  (nested type?)")
        lines.append(f"  +52..+76: {row[52:77].hex(' ')}")
        nest_type = struct.unpack_from("<I", row, 36)[0]
        nest_a = struct.unpack_from("<I", row, 40)[0]
        nest_b = struct.unpack_from("<I", row, 44)[0]
        nest_c = struct.unpack_from("<I", row, 48)[0]
        lines.append(
            f"  nested: type=0x{nest_type:08X} a={nest_a} b={nest_b} c=0x{nest_c:08X}"
        )
        lines.append("")

    # Cross-check: shared constants Band/Mull (young outfielders)
    rb, rm, rs = rows["Patrick Bandeira"], rows["Robert Müller"], rows["Dennis Seimen"]
    lines.append("======== Band↔Mull shared payload constants ========")
    for off in range(16, 77):
        if rb[off] == rm[off]:
            lines.append(f"  +{off}: {rb[off]} (Seim={rs[off]})")

    # Extract candidate FK fields
    candidates = {}
    for name, row in rows.items():
        candidates[name] = {
            "nest_a_+40": struct.unpack_from("<I", row, 40)[0],
            "nest_b_+44": struct.unpack_from("<I", row, 44)[0],
            "u32_+52": struct.unpack_from("<I", row, 52)[0],
            "u32_+56": struct.unpack_from("<I", row, 56)[0],
            "u16_+23": struct.unpack_from("<H", row, 23)[0],  # 0x8c for Band/Mull
            "byte_+32": row[32],
            "byte_+34": row[34],
            "byte_+35": row[35],
        }
        lines.append(f"{name} candidates: {candidates[name]}")

    # Chase nest_b (+44) — small distinctive ints 189/162/78
    lines.append("\n======== chase nest_b (+44) near UniqueID ========")
    for name, c in candidates.items():
        uid = PLAYERS[name]["uid"]
        val = c["nest_b_+44"]
        hits = find_u32_near_uid(val, uid, window=512, limit=6)
        lines.append(f"{name} +44={val}: near-uid hits={len(hits)}")
        for h in hits[:4]:
            lines.append(f"  uid@{h['uid_abs']} val_rel={h['val_rel']} {h['ctx']}")

    # Chase +56
    lines.append("\n======== chase u32_+56 near UniqueID ========")
    for name, c in candidates.items():
        uid = PLAYERS[name]["uid"]
        val = c["u32_+56"]
        hits = find_u32_near_uid(val, uid, window=512, limit=6)
        lines.append(f"{name} +56={val} (0x{val:08X}): near-uid hits={len(hits)}")
        for h in hits[:4]:
            lines.append(f"  uid@{h['uid_abs']} val_rel={h['val_rel']} {h['ctx']}")

    # Taxonomy of nest_b globally
    lines.append("\n======== nest_b (+44) global taxonomy ========")
    for name, c in candidates.items():
        val = c["nest_b_+44"]
        tax = taxonomy_u32(val, limit=20)
        lines.append(f"{name} +44={val}: total≈{tax['total']} kinds={tax['kinds']}")
        for kind, samples in tax["samples"].items():
            lines.append(f"  {kind}:")
            for abs_off, hx in samples:
                lines.append(f"    abs={abs_off} {hx}")

    # Does sheet share any u32 payload with double-UID blob?
    lines.append("\n======== shared u32s between sheet row and double-UID blob ========")
    for name in ROWS:
        row = rows[name]
        dbl = extract(DOUBLE[name], 512)
        sheet_u32s = set()
        for off in range(0, STRIDE - 3):
            sheet_u32s.add(struct.unpack_from("<I", row, off)[0])
        shared = []
        for off in range(0, len(dbl) - 3):
            v = struct.unpack_from("<I", dbl, off)[0]
            if v in sheet_u32s and v not in (0, 1, 0xFFFFFFFF, 0x7FFF, 0x076C0001):
                # also skip personIndex
                if v == struct.unpack_from("<I", row, 4)[0]:
                    shared.append((off, v, "personIndex"))
                elif v == struct.unpack_from("<I", row, 8)[0]:
                    shared.append((off, v, "poolId"))
                else:
                    shared.append((off, v, "other"))
        # unique by value
        seen = set()
        lines.append(f"{name}:")
        for off, v, lab in shared:
            if v in seen:
                continue
            seen.add(v)
            lines.append(f"  double+{off}: 0x{v:08X} ({v}) [{lab}]")

    # Compare nest_a across many neighbors — is it an enum?
    lines.append("\n======== nest_a (+40) distribution over 500 sheet rows ========")
    base = ROWS["Patrick Bandeira"] - 100 * STRIDE
    sample = extract(base, 500 * STRIDE)
    nest_a_counts = Counter()
    nest_b_vals = []
    for i in range(500):
        row = sample[i * STRIDE : (i + 1) * STRIDE]
        if len(row) < 48:
            break
        if row[36:40] != bytes.fromhex("01006c07"):
            continue  # skip alternate types for this dist
        nest_a_counts[struct.unpack_from("<I", row, 40)[0]] += 1
        nest_b_vals.append(struct.unpack_from("<I", row, 44)[0])
    lines.append(f"nest_a top: {nest_a_counts.most_common(15)}")
    lines.append(
        f"nest_b: n={len(nest_b_vals)} unique={len(set(nest_b_vals))} "
        f"min={min(nest_b_vals) if nest_b_vals else None} "
        f"max={max(nest_b_vals) if nest_b_vals else None}"
    )

    # Annotated field map hypothesis
    lines.append("\n======== FIELD MAP HYPOTHESIS ========")
    lines.append(
        """
+0..+3   object type (often 01 00 6c 07 = Person-ish; Müller  b6 00 e1 07)
+4..+7   personIndex (matches double-UID +31)
+8..+15  poolId ×2 (sheet-local identity; NOT referenced elsewhere in save)
+16..+19 00 00 00 01
+20..+22 01 ff 7f     (flag/sentinel 0x7FFF)
+23..+26 Band/Mull: 8c 00 00 00 (=140); Seimen: 28 22 ff 7f (different shape)
+27..+35 variable small fields then…
+36..+39 nested type 01 00 6c 07
+40..+43 nest_a small enum-like (1..5 common)
+44..+47 nest_b mid-size id (78..189 for our three) — CHASE CANDIDATE
+48..+51 ffffffff
+52..    trailing ints (uncertain)
"""
    )

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii")[:11000])
    print(f"\n... wrote {OUT}")


if __name__ == "__main__":
    main()
