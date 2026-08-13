"""Map everything attached to known UIDs: classify fields, follow refs.

Strategy (per user): stop guessing attrs; inventory what the UID-linked
records actually contain, then chase cross-table references.
"""

from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/uid-record-map.txt")

# Double-UID "player blob" records (from prior RE)
DOUBLE_ABS = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}
INTERNAL = {
    "Dennis Seimen": 0x0001BB6D,
    "Patrick Bandeira": 0x0005191C,
    "Robert Müller": 0x00059603,
}

# Classic FM 15-slot position order (working hypothesis)
POS15 = [
    "GK",
    "SW",
    "DR",
    "DL",
    "DC",
    "WBR",
    "WBL",
    "DM",
    "MR",
    "ML",
    "MC",
    "AMR",
    "AML",
    "AMC",
    "ST",
]


def extract(abs_target: int, length: int = 768, before: int = 0) -> bytes:
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
                if abs_base > end + 8 * 1024 * 1024:
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


def classify_uid_hits(uid: bytes, name: str, limit_per_class: int = 6) -> dict:
    """Scan save for UID; bucket by neighbourhood signatures."""
    name_b = name.encode("utf-8")
    name_lp = struct.pack("<I", len(name_b)) + name_b
    buckets: dict[str, list[dict]] = defaultdict(list)
    counts: Counter = Counter()
    abs_base = 0
    carry = b""
    overlap = 400
    for block in stream_blocks():
        data = carry + block
        start = 0
        while True:
            i = data.find(uid, start)
            if i < 0:
                break
            abs_off = abs_base - len(carry) + i
            counts["total"] += 1
            win = data[max(0, i - 64) : i + 256]
            base = i - max(0, i - 64)
            # signatures
            is_double = win[base : base + 8] == uid + uid
            name_rel = win.find(name_lp)
            marker = win.find(bytes.fromhex("058c0c"))
            tag_6c07 = win.find(bytes.fromhex("016c07"))  # often 01 00 6c 07
            if tag_6c07 < 0:
                tag_6c07 = win.find(bytes.fromhex("006c07"))

            if is_double:
                kind = "double_uid"
            elif name_rel >= 0:
                kind = "near_name"
            elif marker >= 0 and marker - base < 96:
                kind = "near_058c0c"
            elif 0 <= (marker - base) < 200:
                kind = "marker_in_window"
            else:
                kind = "other"

            counts[kind] += 1
            if len(buckets[kind]) < limit_per_class:
                buckets[kind].append(
                    {
                        "abs": abs_off,
                        "double": is_double,
                        "name_rel": (name_rel - base) if name_rel >= 0 else None,
                        "marker_rel": (marker - base) if marker >= 0 else None,
                        "hex": win[base : base + 96].hex(" "),
                        "u8": list(win[base : base + 64]),
                    }
                )
            start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]
    return {"counts": dict(counts), "buckets": dict(buckets)}


def annotate_double(blob: bytes, p: dict, lines: list[str]) -> list[int]:
    """Annotate a double-UID blob; return list of u32 candidates that look like refs."""
    uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
    assert blob[:8] == uid + uid
    lines.append(f"\n### double-UID blob ({len(blob)} bytes)")
    lines.append(f"hex[0:160]:\n  {blob[:160].hex(' ')}")

    # Fixed known layout from alignment across 3 players
    lines.append("\nfield map (hypothesis):")
    lines.append("  +0..+7   UniqueID x2")
    # bytes 8..26 vary then ffff
    ff = blob.find(b"\xff\xff\xff\xff")
    lines.append(f"  first 0xFFFFFFFF @ +{ff}")

    # person index: after ff run
    i = ff
    while i < len(blob) and blob[i] == 0xFF:
        i += 1
    idx = struct.unpack_from("<I", blob, i)[0]
    lines.append(f"  +{i}..+{i+3} personIndex u32le = {idx} (0x{idx:X})")
    zeros = blob[i + 4 : i + 8]
    lines.append(f"  +{i+4}..+{i+7} pad? {zeros.hex(' ')}")

    role_at = i + 8
    roles = list(blob[role_at : role_at + 15])
    lines.append(f"  +{role_at}..+{role_at+14} ROLE/POS block (15 bytes): {roles}")
    ranked = sorted(enumerate(roles), key=lambda t: -t[1])
    lines.append("    ranked (idx, rating, POS15 hyp):")
    for idx_r, rating in ranked[:6]:
        label = POS15[idx_r] if idx_r < len(POS15) else "?"
        lines.append(f"      [{idx_r}] {rating:2d}  ~{label}")
    fixture_pos = p.get("pos")
    lines.append(f"    fixture pos string: {fixture_pos!r}")

    body_at = role_at + 15
    lines.append(f"  +{body_at}..  BODY (unknown — not raw/x5 attrs):")
    lines.append(f"    u8[0:80]: {list(blob[body_at : body_at + 80])}")

    # Recurring 6c 07 tag
    tag = bytes.fromhex("006c07")
    tag_hits = []
    pos = 0
    while True:
        j = blob.find(tag, pos)
        if j < 0:
            break
        tag_hits.append(j)
        pos = j + 1
    lines.append(f"  tag .. 00 6c 07 hits @ {tag_hits[:20]} (0x076c=1900 type?)")

    # Collect interesting u32s for ref chase
    refs = []
    for off in range(8, min(120, len(blob) - 3)):
        v = struct.unpack_from("<I", blob, off)[0]
        # skip obvious junk
        if v in (0, 0xFFFFFFFF, 0xFFFFFFFE):
            continue
        if v == (p["uid"] & 0xFFFFFFFF):
            continue
        # FM unique IDs often 1e9..2.1e9 (0x7738xxxx style for newgens)
        if 1_000_000_000 <= v <= 2_200_000_000:
            refs.append((off, v, "uid_range"))
        elif 1000 <= v <= 50_000:
            refs.append((off, v, "small_id"))
        elif v == 0x076C or (v & 0xFFFF) == 0x076C:
            refs.append((off, v, "tag_6c07"))
    lines.append("  ref candidates:")
    for off, v, kind in refs[:40]:
        lines.append(f"    +{off}: {v} (0x{v:08X}) [{kind}]")

    # u16 sweep in header (8..40) — label only, not assumed CA/PA
    lines.append("  u16le header sweep (+8..+40) [NOT assumed CA/PA]:")
    for off in range(8, 40, 2):
        v = struct.unpack_from("<H", blob, off)[0]
        lines.append(f"    +{off}: {v}")

    return [v for _, v, k in refs if k == "uid_range"]


def resolve_uid_ref(ref_uid: int, lines: list[str], budget: int = 3) -> None:
    """If ref looks like another person UniqueID, find nearby UTF-8 name."""
    uid_b = struct.pack("<I", ref_uid & 0xFFFFFFFF)
    hits = 0
    abs_base = 0
    carry = b""
    for block in stream_blocks():
        data = carry + block
        start = 0
        while hits < budget:
            i = data.find(uid_b, start)
            if i < 0:
                break
            # look for lp32 string within +4..+80
            win = data[i : i + 160]
            for j in range(4, 96):
                if j + 4 > len(win):
                    break
                ln = struct.unpack_from("<I", win, j)[0]
                if 3 <= ln <= 40 and j + 4 + ln <= len(win):
                    raw = win[j + 4 : j + 4 + ln]
                    try:
                        s = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    if s.isprintable() and " " in s or (s[:1].isalpha() and len(s) >= 4):
                        abs_off = abs_base - len(carry) + i
                        lines.append(
                            f"    ref 0x{ref_uid:08X} @{abs_off}+{j}: name? {s!r}"
                        )
                        hits += 1
                        break
            start = i + 1
        abs_base += len(block)
        carry = data[-200:]
        if hits >= budget:
            break
    if hits == 0:
        lines.append(f"    ref 0x{ref_uid:08X}: no nearby lp32 name found (sample)")


def compare_aligned(blobs: dict[str, bytes], lines: list[str]) -> None:
    lines.append("\n\n======== ALIGNED FIELD COMPARISON ========")
    names = list(blobs.keys())
    n = min(len(blobs[names[0]]), 200)
    # Classify each offset
    lines.append("offset | equal-all | equal-BM | Band | Mull | Seim | note")
    # Find role block start (same structure)
    role_starts = {}
    for name, blob in blobs.items():
        ff = blob.find(b"\xff\xff\xff\xff")
        i = ff
        while i < len(blob) and blob[i] == 0xFF:
            i += 1
        role_starts[name] = i + 8  # after index+pad

    # Use Bandeira as reference layout
    b = blobs["Patrick Bandeira"]
    m = blobs["Robert Müller"]
    s = blobs["Dennis Seimen"]
    for off in range(n):
        bv, mv, sv = b[off], m[off], s[off]
        eq_all = bv == mv == sv
        eq_bm = bv == mv
        note = ""
        if off < 8:
            note = "UID"
        elif 8 <= off < 27:
            note = "header"
        elif b[off] == 0xFF and off < 40:
            note = "ff"
        rs = role_starts["Patrick Bandeira"]
        if rs <= off < rs + 15:
            note = f"ROLE[{off - rs}]~{POS15[off - rs]}"
        if not eq_bm or note:
            if eq_all:
                mark = "ALL"
            elif eq_bm:
                mark = "BM"
            else:
                mark = "diff"
            if mark == "diff" or note.startswith("ROLE") or off < 45:
                lines.append(
                    f"  +{off:3d} | {mark:4s} | B={bv:3d} M={mv:3d} S={sv:3d} | {note}"
                )


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"SAVE {SAVE.name}")
    lines.append(
        "Goal: inventory UID-linked records and chase refs — "
        "do NOT assume body bytes are CA/PA or visible attrs.\n"
    )

    blobs: dict[str, bytes] = {}
    all_refs: list[int] = []

    for p in PLAYERS:
        name = p["name"]
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        lines.append("\n" + "=" * 72)
        lines.append(
            f"{name} uid={p['uid']} iid=0x{INTERNAL[name]:08X} "
            f"pos={p.get('pos')} age={p.get('age')}"
        )

        # 1) UID occurrence taxonomy
        lines.append("\n## UID occurrence taxonomy")
        tax = classify_uid_hits(uid, name)
        lines.append(f"  counts: {tax['counts']}")
        for kind, rows in tax["buckets"].items():
            lines.append(f"\n  -- {kind} (showing {len(rows)}) --")
            for r in rows:
                lines.append(
                    f"  abs={r['abs']} name_rel={r['name_rel']} "
                    f"marker_rel={r['marker_rel']}"
                )
                lines.append(f"    {r['hex']}")

        # 2) Double-UID deep annotate
        abs_d = DOUBLE_ABS[name]
        blob = extract(abs_d, 512)
        blobs[name] = blob
        refs = annotate_double(blob, p, lines)
        all_refs.extend(refs)

        # 3) Name-colocated person record (identity)
        lines.append("\n## name-colocated person window (if found)")
        name_b = name.encode("utf-8")
        needle = struct.pack("<I", len(name_b)) + name_b
        found = False
        abs_base = 0
        carry = b""
        for block in stream_blocks():
            data = carry + block
            start = 0
            while not found:
                i = data.find(needle, start)
                if i < 0:
                    break
                behind = data[max(0, i - 80) : i]
                if uid in behind:
                    ws = max(0, i - 48)
                    we = min(len(data), i + len(needle) + 128)
                    win = data[ws:we]
                    abs_off = abs_base - len(carry) + i
                    lines.append(f"  name@abs={abs_off}")
                    lines.append(f"  hex: {win.hex(' ')}")
                    # dump trail after name as u8
                    trail = data[i + len(needle) : i + len(needle) + 64]
                    lines.append(f"  after-name u8: {list(trail)}")
                    found = True
                    break
                start = i + 1
            abs_base += len(block)
            carry = data[-200:]
            if found:
                break
        if not found:
            lines.append("  (not found in scan)")

    compare_aligned(blobs, lines)

    # Chase a few unique refs
    lines.append("\n\n======== REF CHASE (uid-range u32s from double-UID bodies) ========")
    uniq_refs = []
    seen = set()
    for v in all_refs:
        if v not in seen:
            seen.add(v)
            uniq_refs.append(v)
    for v in uniq_refs[:12]:
        lines.append(f"\nref {v} (0x{v:08X}):")
        resolve_uid_ref(v, lines, budget=2)

    # Sanity on POS15 hypothesis
    lines.append("\n\n======== POS15 HYPOTHESIS CHECK ========")
    lines.append(
        "If ROLE[0]=GK: Seimen must be ~20; Bandeira/Müller low.\n"
        "Bandeira fixture D(L)/DM → want high DL/DC/DM.\n"
        "Müller fixture AM(C) → want high AMC/MC/DM."
    )
    for name, blob in blobs.items():
        ff = blob.find(b"\xff\xff\xff\xff")
        i = ff
        while blob[i] == 0xFF:
            i += 1
        roles = list(blob[i + 8 : i + 23])
        lines.append(f"\n{name}: {list(zip(POS15, roles))}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii")[:14000])
    print(f"\n... wrote {OUT} ({len(text)} chars)")


if __name__ == "__main__":
    main()
