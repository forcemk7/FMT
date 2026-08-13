"""Chase spreadsheet poolId → find what table/record it points at."""

from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/poolid-chase.txt")
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

# From person-index sheet
POOL = {
    "Patrick Bandeira": 0x0086CF7F,
    "Robert Müller": 0x0087617C,
    "Dennis Seimen": 0x01604912,
}
DOUBLE = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}
INTERNAL = {
    "Dennis Seimen": 0x0001BB6D,
    "Patrick Bandeira": 0x0005191C,
    "Robert Müller": 0x00059603,
}
INDEX = {
    "Dennis Seimen": 1790,
    "Patrick Bandeira": 1198,
    "Robert Müller": 1233,
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
                    lo = max(0, abs_target - before - chunk_start)
                    # careful
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


def classify_window(win: bytes, base: int, name: str) -> str:
    uid = struct.pack("<I", next(p["uid"] for p in PLAYERS if p["name"] == name) & 0xFFFFFFFF)
    iid = struct.pack("<I", INTERNAL[name])
    idx = struct.pack("<I", INDEX[name])
    if win[base : base + 8] == uid + uid:
        return "double_uid"
    if uid in win:
        return "near_uid"
    if iid in win:
        return "near_iid"
    if idx in win and win.find(idx) != base:  # personIndex elsewhere in window
        # could be the sheet row itself
        pass
    if bytes.fromhex("058c0c") in win:
        return "near_058c0c"
    name_b = name.encode("utf-8")
    if name_b in win or name.split()[-1].encode("utf-8") in win:
        return "near_name"
    # type tags
    if win[max(0, base - 4) : base] in (
        bytes.fromhex("01006c07"),
        bytes.fromhex("b600e107"),
    ) or win[base : base + 4] in (
        bytes.fromhex("01006c07"),
        bytes.fromhex("b600e107"),
    ):
        return "type_tagged"
    # pool duplicated (sheet row pattern)
    if base + 8 <= len(win) and win[base : base + 4] == win[base + 4 : base + 8]:
        return "pool_dup_pair"
    return "other"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("POOLID CHASE\n")

    # 0) Is poolId inside known double-UID blobs?
    lines.append("======== poolId inside double-UID blob? ========")
    for name, abs_d in DOUBLE.items():
        blob = extract(abs_d, 512)
        pool = POOL[name]
        pat = struct.pack("<I", pool)
        pos = blob.find(pat)
        lines.append(f"{name}: pool=0x{pool:08X} in double-UID @ {pos}")

    # 1) Full taxonomy of every poolId hit
    lines.append("\n======== poolId occurrence taxonomy ========")
    all_hits: dict[str, list[dict]] = {}
    abs_base = 0
    carry = b""
    for block in stream_blocks():
        data = carry + block
        for name, pool in POOL.items():
            if name not in all_hits:
                all_hits[name] = []
            pat = struct.pack("<I", pool)
            start = 0
            while True:
                i = data.find(pat, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                # skip duplicate from carry overlap
                if all_hits[name] and all_hits[name][-1]["abs"] == abs_off:
                    start = i + 1
                    continue
                ws = max(0, i - 64)
                we = min(len(data), i + 128)
                win = data[ws:we]
                base = i - ws
                kind = classify_window(win, base, name)
                rec = {
                    "abs": abs_off,
                    "kind": kind,
                    "hex": win[base : base + 64].hex(" "),
                    "before": win[max(0, base - 24) : base].hex(" "),
                    "u8": list(win[base : base + 48]),
                }
                all_hits[name].append(rec)
                start = i + 1
        abs_base += len(block)
        carry = data[-200:]

    for name, rows in all_hits.items():
        counts = Counter(r["kind"] for r in rows)
        lines.append(f"\n## {name} pool=0x{POOL[name]:08X} total={len(rows)} kinds={dict(counts)}")
        # show samples per kind
        by_kind: dict[str, list] = defaultdict(list)
        for r in rows:
            by_kind[r["kind"]].append(r)
        for kind, samples in by_kind.items():
            lines.append(f"  -- {kind} (n={len(samples)}) --")
            for r in samples[:4]:
                lines.append(f"  abs={r['abs']}")
                lines.append(f"    before: {r['before']}")
                lines.append(f"    after:  {r['hex']}")

    # 2) Stride table keyed by poolId?
    # Test: row[poolId] contains UniqueID — poolIds are huge (~8e6), need huge table
    # More likely: poolId is dense id in 0..N with stride S
    # Check span of poolIds in neighborhood of sheet
    lines.append("\n\n======== poolId density / possible stride ========")
    pools = list(POOL.values())
    lines.append(f"pool values: { {n: hex(v) for n,v in POOL.items()} }")
    lines.append(f"Band-Mull delta: {POOL['Robert Müller'] - POOL['Patrick Bandeira']}")
    # Extract ~2000 consecutive sheet rows and collect their poolIds
    # Bandeira sheet row starts at 206618
    sheet_start = 206618 - 50 * 77  # 50 rows before
    sample = extract(sheet_start, 200 * 77)
    sheet_pools = []
    for i in range(200):
        row = sample[i * 77 : (i + 1) * 77]
        if len(row) < 16:
            break
        idx = struct.unpack_from("<I", row, 4)[0]
        pool = struct.unpack_from("<I", row, 8)[0]
        sheet_pools.append((idx, pool))
    lines.append(f"sampled {len(sheet_pools)} sheet rows around Bandeira")
    # check if poolIds are mostly unique / monotonic
    pool_vals = [p for _, p in sheet_pools]
    lines.append(f"  unique pools: {len(set(pool_vals))}/{len(pool_vals)}")
    deltas = [pool_vals[i + 1] - pool_vals[i] for i in range(len(pool_vals) - 1)]
    delta_counts = Counter(deltas)
    lines.append(f"  top pool deltas: {delta_counts.most_common(8)}")

    # 3) Hunt: records that START with poolId (like objects keyed by poolId)
    lines.append("\n======== records starting with poolId (wide dump) ========")
    for name, pool in POOL.items():
        # take first 'other' or best non-sheet hit
        rows = [r for r in all_hits[name] if r["kind"] not in ("pool_dup_pair",)]
        # Prefer hits that look like object headers: preceded by few zeros or type
        interesting = []
        for r in all_hits[name]:
            # skip the sheet row itself (has dup pool immediately after)
            if r["kind"] == "pool_dup_pair":
                continue
            interesting.append(r)
        lines.append(f"\n## {name} interesting hits={len(interesting)}")
        for r in interesting[:8]:
            # wider dump
            wide = extract(r["abs"], 256, before=32)
            lines.append(f"  abs={r['abs']} kind={r['kind']}")
            lines.append(f"    wide: {wide.hex(' ')}")
            # search for UID / iid / det-lea in wide
            uid = struct.pack(
                "<I", next(p["uid"] for p in PLAYERS if p["name"] == name) & 0xFFFFFFFF
            )
            iid = struct.pack("<I", INTERNAL[name])
            lines.append(
                f"    uid_at={wide.find(uid)} iid_at={wide.find(iid)} "
                f"idx_at={wide.find(struct.pack('<I', INDEX[name]))}"
            )

    # 4) Cross-link: does double-UID personIndex row's poolId appear as a field
    #    in the name-colocated person record?
    lines.append("\n======== poolId near name records ========")
    for name, pool in POOL.items():
        name_b = name.encode("utf-8")
        needle = struct.pack("<I", len(name_b)) + name_b
        pool_b = struct.pack("<I", pool)
        found = 0
        abs_base = 0
        carry = b""
        for block in stream_blocks():
            data = carry + block
            start = 0
            while found < 4:
                i = data.find(needle, start)
                if i < 0:
                    break
                win = data[max(0, i - 128) : i + len(needle) + 160]
                if pool_b in win:
                    abs_off = abs_base - len(carry) + i
                    pr = win.find(pool_b)
                    lines.append(
                        f"  {name}: name@abs≈{abs_off} pool_rel_in_win={pr} "
                        f"ctx={win[max(0,pr-8):pr+16].hex(' ')}"
                    )
                    found += 1
                start = i + 1
            abs_base += len(block)
            carry = data[-300:]
            if found >= 4:
                break
        if found == 0:
            lines.append(f"  {name}: poolId NOT in ±128 of name lp32")

    # 5) Try poolId as stride key in early memory (pool values ~8e6 — too big
    #    unless table is offset). Try LOW 24 bits as index into dense table.
    lines.append("\n======== low24(poolId) as possible dense index ========")
    for name, pool in POOL.items():
        lo = pool & 0xFFFFFF
        lines.append(f"  {name}: pool=0x{pool:08X} lo24={lo} (0x{lo:06X})")
    # Check if Band and Mull lo24 differ by amount commensurate with sheet samples
    lo_b = POOL["Patrick Bandeira"] & 0xFFFFFF
    lo_m = POOL["Robert Müller"] & 0xFFFFFF
    lines.append(f"  lo24 delta Mull-Band: {lo_m - lo_b}")

    # Search for lo24 as u32 (zero-extended) near UniqueID with wider window
    lines.append("\n======== lo24 u32 near UniqueID (±256) ========")
    for name, pool in POOL.items():
        lo = pool & 0xFFFFFF
        # also try full pool with wider window — already done; try as u24 packed?
        pat = struct.pack("<I", lo)
        uid = struct.pack(
            "<I", next(p["uid"] for p in PLAYERS if p["name"] == name) & 0xFFFFFFFF
        )
        hits = []
        abs_base = 0
        carry = b""
        for block in stream_blocks():
            data = carry + block
            start = 0
            while len(hits) < 5:
                i = data.find(uid, start)
                if i < 0:
                    break
                win = data[max(0, i - 256) : i + 256]
                j = win.find(pat)
                if j >= 0:
                    abs_off = abs_base - len(carry) + i
                    hits.append((abs_off, j - (i - max(0, i - 256))))
                start = i + 1
            abs_base += len(block)
            carry = data[-300:]
            if len(hits) >= 5:
                break
        lines.append(f"  {name}: lo24 near uid hits={hits}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii")[:12000])
    print(f"\n... wrote {OUT} ({len(text)} chars)")


if __name__ == "__main__":
    main()
