"""Hunt the 'spreadsheet' keyed by personIndex (1198 / 1233 / 1790).

Strong test: a fixed-stride table where row[index] contains that player's UniqueID.
Also: dump other occurrences of each personIndex u32 and classify neighborhoods.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/person-index-table.txt")

# personIndex from double-UID records
INDEX = {
    "Dennis Seimen": 1790,  # 0x06FE
    "Patrick Bandeira": 1198,  # 0x04AE
    "Robert Müller": 1233,  # 0x04D1
}
DOUBLE_ABS = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}


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
                if abs_base > end + 8 * 1024 * 1024:
                    break
        finally:
            reader.close()
    return bytes(buf)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("PERSON INDEX TABLE HUNT")
    lines.append(
        "Indices: "
        + ", ".join(f"{n}={INDEX[n]}" for n in INDEX)
        + "\n"
    )

    # --- 1) All personIndex u32 occurrences (context) ---
    lines.append("======== personIndex u32 occurrences (excl. known double-UID) ========")
    idx_hits: dict[str, list[dict]] = {n: [] for n in INDEX}
    abs_base = 0
    carry = b""
    for block in stream_blocks():
        data = carry + block
        for name, idx in INDEX.items():
            pat = struct.pack("<I", idx)
            uid = struct.pack("<I", next(p["uid"] for p in PLAYERS if p["name"] == name) & 0xFFFFFFFF)
            start = 0
            while len(idx_hits[name]) < 25:
                i = data.find(pat, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                # skip the known double-UID location (+31)
                known = DOUBLE_ABS[name]
                if known <= abs_off <= known + 40:
                    start = i + 1
                    continue
                win = data[max(0, i - 32) : i + 96]
                base = i - max(0, i - 32)
                uid_rel = win.find(uid)
                dbl = win.find(uid + uid)
                lines_hit = {
                    "abs": abs_off,
                    "uid_rel": (uid_rel - base) if uid_rel >= 0 else None,
                    "double_rel": (dbl - base) if dbl >= 0 else None,
                    "hex": win.hex(" "),
                    "u8": list(win[base : base + 48]),
                }
                # de-dupe same abs
                if not idx_hits[name] or idx_hits[name][-1]["abs"] != abs_off:
                    idx_hits[name].append(lines_hit)
                start = i + 1
        abs_base += len(block)
        carry = data[-128:]

    for name in INDEX:
        rows = idx_hits[name]
        with_uid = [r for r in rows if r["uid_rel"] is not None]
        lines.append(
            f"\n## {name} idx={INDEX[name]} hits={len(rows)} with_uid_nearby={len(with_uid)}"
        )
        for r in (with_uid or rows)[:10]:
            lines.append(
                f"  abs={r['abs']} uid_rel={r['uid_rel']} double_rel={r['double_rel']}"
            )
            lines.append(f"    {r['hex'][:200]}")

    # --- 2) Stride table: row[index] starts with UniqueID ---
    # Load one big contiguous slice that is likely to contain a person table.
    # Try several sample windows around career DB middles / near double-UID clusters.
    lines.append("\n\n======== stride table search (row[i] contains UniqueID) ========")
    # We need a window large enough for max_index * S.
    # Cap S so max_index * S fits in sample.
    max_idx = max(INDEX.values())  # 1790
    samples = [
        ("near_bandeira_double", DOUBLE_ABS["Patrick Bandeira"] - 2_000_000, 8_000_000),
        ("near_muller_double", DOUBLE_ABS["Robert Müller"] - 2_000_000, 8_000_000),
        ("near_seimen_double", DOUBLE_ABS["Dennis Seimen"] - 2_000_000, 8_000_000),
        ("mid_150m", 150_000_000, 8_000_000),
        ("mid_250m", 250_000_000, 8_000_000),
        ("early_50m", 50_000_000, 8_000_000),
    ]

    # Precompute player uid bytes
    pmeta = []
    for p in PLAYERS:
        pmeta.append(
            {
                "name": p["name"],
                "idx": INDEX[p["name"]],
                "uid": struct.pack("<I", p["uid"] & 0xFFFFFFFF),
            }
        )

    found_any = []
    for label, start, length in samples:
        lines.append(f"\n-- sample {label} @{start} len={length} --")
        # extract may be slow
        sample = extract(start, length)
        if len(sample) < length // 2:
            lines.append(f"  short read {len(sample)}")
            continue
        lines.append(f"  got {len(sample)} bytes")

        hits_for_sample = []
        # stride sizes: small to medium (attr rows are often 32–512)
        for S in list(range(8, 65, 4)) + list(range(68, 257, 4)) + [320, 384, 512, 768, 1024]:
            need = max_idx * S + S
            if need > len(sample):
                continue
            # try every base alignment 0..min(S,64)-1 for speed
            bases = range(min(S, 64))
            for base in bases:
                if base + need > len(sample):
                    continue
                # For each player, check if UID appears in row window [0:S]
                ok = True
                locs = {}
                for pm in pmeta:
                    row_off = base + pm["idx"] * S
                    row = sample[row_off : row_off + S]
                    pos = row.find(pm["uid"])
                    if pos < 0:
                        ok = False
                        break
                    locs[pm["name"]] = pos
                if ok:
                    hits_for_sample.append((S, base, locs))
                    found_any.append((label, start, S, base, locs))
            if len(hits_for_sample) >= 5:
                break  # enough for this sample

        if hits_for_sample:
            lines.append(f"  MATCHES: {len(hits_for_sample)}")
            for S, base, locs in hits_for_sample[:8]:
                lines.append(f"    S={S} base={base} uid_in_row_at={locs}")
                # dump first 64 bytes of each row
                for pm in pmeta:
                    row_off = base + pm["idx"] * S
                    row = sample[row_off : row_off + min(64, S)]
                    abs_row = start + row_off
                    lines.append(
                        f"      {pm['name']} abs~={abs_row} hex={row.hex(' ')}"
                    )
        else:
            lines.append("  no stride where all 3 rows contain their UniqueID")

    # --- 3) Weaker: stride where row contains personIndex at fixed offset ---
    lines.append("\n\n======== stride where row[i] has personIndex at offset 0 ========")
    # Already partially covered; try: at base+idx*S the first u32 IS the index
    # (array of records starting with index, looking up by position)
    # Search one promising sample near Bandeira if no UID match.
    sample = extract(DOUBLE_ABS["Patrick Bandeira"] - 1_000_000, 6_000_000)
    start = DOUBLE_ABS["Patrick Bandeira"] - 1_000_000
    idx_hits2 = []
    for S in list(range(16, 257, 4)) + [512, 1024]:
        need = max_idx * S + 4
        if need > len(sample):
            continue
        for base in range(min(S, 32)):
            if base + need > len(sample):
                continue
            ok = True
            for pm in pmeta:
                off = base + pm["idx"] * S
                val = struct.unpack_from("<I", sample, off)[0]
                if val != pm["idx"]:
                    ok = False
                    break
            if ok:
                idx_hits2.append((S, base))
    lines.append(f"rows starting with own index: {idx_hits2[:10]}")

    # --- 4) Diff band/mull double-UID distance vs index diff ---
    lines.append("\n\n======== geometry of known double-UID blobs ========")
    b = DOUBLE_ABS["Patrick Bandeira"]
    m = DOUBLE_ABS["Robert Müller"]
    s = DOUBLE_ABS["Dennis Seimen"]
    lines.append(f"Bandeira abs={b} idx={INDEX['Patrick Bandeira']}")
    lines.append(f"Müller   abs={m} idx={INDEX['Robert Müller']}")
    lines.append(f"Seimen   abs={s} idx={INDEX['Dennis Seimen']}")
    lines.append(f"Mull-Band abs delta={m - b}  idx delta={INDEX['Robert Müller'] - INDEX['Patrick Bandeira']}")
    if INDEX["Robert Müller"] != INDEX["Patrick Bandeira"]:
        approx = (m - b) / (INDEX["Robert Müller"] - INDEX["Patrick Bandeira"])
        lines.append(f"  implied stride if same array: {approx:.2f} bytes/row")
    lines.append(
        "Seimen is far from the other two → likely different memory region "
        "or not stored as a dense idx array of double-UID blobs."
    )

    # --- 5) Look for pointer/offset tables: u32 array where [idx] is an abs offset ---
    lines.append("\n\n======== offset-table hypothesis ========")
    lines.append(
        "If personIndex indexes a pointer table of u32 offsets, then "
        "table[idx] might point near that player's double-UID."
    )
    # Search for a u32 array where sample[base+idx*4] ~= relative offset to double-UID
    # Too many false positives; instead: find u32 equal to (double_abs - X) near indices.
    for name in ("Patrick Bandeira", "Robert Müller"):
        target = DOUBLE_ABS[name]
        idx = INDEX[name]
        # search for the abs value itself as u32 (unlikely in 32-bit compressed space)
        # search for low 24 bits
        lo24 = target & 0xFFFFFF
        pat = struct.pack("<I", lo24)
        lines.append(f"\n{name}: abs={target} lo24=0x{lo24:06X} idx={idx}")
        # just note - full scan expensive; skip unless needed

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii")[:12000])
    print(f"\n... wrote {OUT} ({len(text)} chars)")
    if found_any:
        print(f"STRIDE MATCHES: {len(found_any)}")
        for row in found_any[:5]:
            print(" ", row)
    else:
        print("No stride UID matches in sampled windows.")


if __name__ == "__main__":
    main()
