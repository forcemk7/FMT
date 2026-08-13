"""Decode PlayerSL_FirstTeam_* shortlists and the 1007145540 UID cluster."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-shortlist-cluster.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
UID_LO, UID_HI = 1_000_000_000, 3_000_000_000
PINDEX = {"Dennis Seimen": 1790, "Patrick Bandeira": 1198, "Robert Müller": 1233}


def extract(abs_target: int, length: int, before: int = 0) -> bytes:
    start = abs_target - before
    end = abs_target + length
    abs_base = 0
    carry = b""
    buf = bytearray()
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
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
                    already = len(buf)
                    want = start + already
                    lo = max(0, start - chunk_start, want - chunk_start)
                    hi = min(len(data), end - chunk_start)
                    if lo < hi:
                        buf.extend(data[lo:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= before + length:
                    break
        finally:
            reader.close()
    return bytes(buf)


def dump(b: bytes, base: int) -> list[str]:
    lines = []
    for i in range(0, len(b), 32):
        chunk = b[i : i + 32]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"  {base+i:10d}  {hexs:<96}  {asc}")
    return lines


def main() -> None:
    lines: list[str] = []

    # ---- shortlist named objects ----
    for label, abs_s in [
        ("PlayerSL_FirstTeam_Squad", 1007175835),
        ("PlayerSL_FirstTeam_XI", 1007174678),
        ("PlayerSL_FirstTeam_Mentors", 1007170517),
        ("PlayerSL_Development_Squad", 1007171568),
    ]:
        buf = extract(abs_s, 2048, before=128)
        base = abs_s - 128
        lines.append(f"\n======== {label} @{abs_s} ========")
        # find exact string
        needle = label.encode("ascii")
        j = buf.find(needle)
        lines.append(f"  string_rel={j}")
        if j >= 0:
            lines.extend(dump(buf[max(0, j - 64) : j + 400], base + max(0, j - 64)))

    # ---- UID cluster at 1007145540 ----
    center = 1007145540
    buf = extract(center, 12000, before=2000)
    base = center - 2000
    lines.append(f"\n======== UID cluster around {center} ========")
    for name, uid in UIDS.items():
        pat = struct.pack("<I", uid)
        offs = []
        start = 0
        while True:
            j = buf.find(pat, start)
            if j < 0:
                break
            offs.append(base + j)
            start = j + 1
        lines.append(f"  {name}: {offs}")

    # dump from first known to last+200
    first = min(
        buf.find(struct.pack("<I", UIDS["Dennis Seimen"])),
        buf.find(struct.pack("<I", UIDS["Patrick Bandeira"])),
        buf.find(struct.pack("<I", UIDS["Robert Müller"])),
    )
    last = max(
        buf.find(struct.pack("<I", UIDS["Dennis Seimen"])),
        buf.find(struct.pack("<I", UIDS["Patrick Bandeira"])),
        buf.find(struct.pack("<I", UIDS["Robert Müller"])),
    )
    lines.append(f"\nhex from first-64 to last+256:")
    lo = max(0, first - 64)
    hi = min(len(buf), last + 256)
    lines.extend(dump(buf[lo:hi], base + lo))

    # Analyze spacing between consecutive UniqueID-looking values in this span
    lines.append("\nUID-like sequence analysis in cluster±2KB:")
    span = buf[max(0, first - 512) : min(len(buf), last + 512)]
    span_base = base + max(0, first - 512)
    hits = []
    for i in range(0, len(span) - 3):
        v = struct.unpack_from("<I", span, i)[0]
        if UID_LO <= v <= UID_HI:
            hits.append((span_base + i, v, NAME_BY.get(v)))
    lines.append(f"  uid-like count={len(hits)}")
    # show gaps between successive
    for i, (a, v, n) in enumerate(hits[:60]):
        gap = "" if i == 0 else f" Δ={a - hits[i-1][0]}"
        mark = f" **{n}" if n else ""
        lines.append(f"  @{a} {v}{mark}{gap}")

    # Try personIndex list in same area
    lines.append("\npersonIndex occurrences in cluster window:")
    for name, idx in PINDEX.items():
        pat = struct.pack("<I", idx)
        start = 0
        n = 0
        while n < 8:
            j = buf.find(pat, start)
            if j < 0:
                break
            ctx = buf[max(0, j - 8) : j + 16]
            lines.append(f"  {name} idx@{base+j} ctx={ctx.hex()}")
            start = j + 1
            n += 1

    # ---- Follow team-id candidates from First Team Squad filter ----
    # From earlier: 50 f4 02 00 = 193616; 04 4d = 19716; e8 54 = 21736
    team_ids = [193616, 19716, 21736, 0x4D04, 0x54E8, 0x2F450]
    lines.append("\n======== hunt team-id refs near fixture doubles ========")
    # Check whether any team id appears in double-UID headers
    for name, dbl in [
        ("Seimen", 157471994),
        ("Bandeira", 264934792),
        ("Müller", 279879830),
    ]:
        hdr = extract(dbl, 128, before=0)
        lines.append(f"{name} double head: {hdr[:80].hex()}")
        for tid in team_ids:
            pat = struct.pack("<I", tid)
            j = hdr.find(pat)
            lines.append(f"  tid {tid} in double[0:128]: {j}")

    # Search club object for team ids and for staffed-player lists using personIndex
    club = 1986866253
    buf = extract(club, 30000, before=5000)
    base = club - 5000
    lines.append(f"\n======== club object @ {club} expanded ========")
    lines.extend(dump(buf[5000 - 64 : 5000 + 512], club - 64))

    # Parse relation list more carefully after short name
    # After 'Schalke 04' we saw 1d 23 03 03 ... then relation entries
    j = buf.find(b"Schalke 04")
    lines.append(f"Schalke 04 at {base+j}")
    # Dump 2KB after club name as u8/u32 mix looking for UID packed with tags
    after = buf[j : j + 4000]
    lines.append("\nScan after club name for UID + tag patterns:")
    uid_hits = []
    for i in range(0, len(after) - 3):
        v = struct.unpack_from("<I", after, i)[0]
        if UID_LO <= v <= UID_HI:
            uid_hits.append((base + j + i, v, NAME_BY.get(v), after[max(0, i - 6) : i + 4].hex()))
    lines.append(f"  UID-like after club name (4KB): {len(uid_hits)}")
    for a, v, n, ctx in uid_hits[:40]:
        mark = f" **{n}" if n else ""
        lines.append(f"  @{a} {v}{mark} pre={ctx}")

    # Try to find a dense UniqueID list after club (stride 4 OR with tags)
    # Also look for personIndex dense lists (values 0..5000)
    lines.append("\nDense small-int (personIndex-like) runs after club:")
    # values in 1..5000 consecutive stride 4
    i = 0
    while i + 40 <= len(after):
        vals = []
        k = i
        while k + 4 <= len(after):
            v = struct.unpack_from("<I", after, k)[0]
            if not (1 <= v <= 8000):
                break
            vals.append(v)
            k += 4
            if len(vals) >= 80:
                break
        if len(vals) >= 15 and len(set(vals)) >= 12:
            known = []
            for name, idx in PINDEX.items():
                if idx in vals:
                    known.append((name, vals.index(idx)))
            lines.append(
                f"  @{base+j+i} n={len(vals)} unique={len(set(vals))} known_idx={known}"
            )
            lines.append(f"    head={vals[:20]}")
            if known:
                lines.append(f"    ALL={vals}")
            i = k
        else:
            i += 1

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = OUT.read_text(encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii")[:30000])
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
