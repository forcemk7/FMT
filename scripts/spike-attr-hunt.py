"""Hunt attribute encodings (esp. Det/Lead) near known Unique IDs."""

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
OUT = Path("tmp/fm-spike")
OUT.mkdir(parents=True, exist_ok=True)

# Window around each UID occurrence
RADIUS = 512


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


def iter_uid_windows(uid: int):
    pat = struct.pack("<I", uid & 0xFFFFFFFF)
    abs_base = 0
    carry = b""
    overlap = RADIUS * 2 + 8
    for block in stream_blocks():
        data = carry + block
        start = 0
        while True:
            i = data.find(pat, start)
            if i < 0:
                break
            abs_off = abs_base - len(carry) + i
            ws = max(0, i - RADIUS)
            we = min(len(data), i + 4 + RADIUS)
            yield abs_off, data[ws:we], i - ws
            start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]


def find_pair_offsets(window: bytes, uid_rel: int, a: int, b: int, max_gap: int = 8):
    """Rel offsets (from uid) where byte==a and byte(+1..max_gap)==b."""
    hits = []
    for i in range(len(window)):
        if window[i] != a:
            continue
        for g in range(1, max_gap + 1):
            j = i + g
            if j < len(window) and window[j] == b:
                hits.append((i - uid_rel, g, j - uid_rel))
    return hits


def find_u32_pair(window: bytes, uid_rel: int, a: int, b: int, max_gap_bytes: int = 16):
    pa = struct.pack("<I", a)
    pb = struct.pack("<I", b)
    hits = []
    start = 0
    while True:
        i = window.find(pa, start)
        if i < 0:
            break
        for g in range(4, max_gap_bytes + 1, 4):
            j = i + g
            if window[j : j + 4] == pb:
                hits.append((i - uid_rel, g, j - uid_rel))
        start = i + 1
    return hits


def score_attr_run(window: bytes, start: int, length: int = 20) -> list[int] | None:
    """Return values if stretch looks like 1..20 attribute bytes."""
    if start < 0 or start + length > len(window):
        return None
    vals = list(window[start : start + length])
    if all(1 <= v <= 20 for v in vals):
        return vals
    return None


def main() -> None:
    lines: list[str] = []
    # Cross-player consensus for det/lea pair geometry
    pair_geom: dict[str, Counter] = defaultdict(Counter)

    for p in PLAYERS:
        det, lea = p["det"], p["lea"]
        lines.append(
            f"\n======== {p['name']} uid={p['uid']} det={det} lea={lea} ========"
        )
        n_win = 0
        u8_pair_counter: Counter = Counter()
        u32_pair_counter: Counter = Counter()
        # Also reverse order lea then det
        u8_rev_counter: Counter = Counter()
        good_examples: list[str] = []

        for abs_off, win, uid_rel in iter_uid_windows(p["uid"]):
            n_win += 1
            for rel_a, gap, rel_b in find_pair_offsets(win, uid_rel, det, lea, max_gap=8):
                key = f"u8 det@+{rel_a} gap={gap} lea@+{rel_b}"
                u8_pair_counter[key] += 1
                pair_geom[f"u8 gap={gap}" ][rel_a] += 1
                if len(good_examples) < 6:
                    at = uid_rel + rel_a
                    ctx = win[max(0, at - 16) : at + 48]
                    # try attribute run starting a bit before det
                    runs = []
                    for back in range(0, 40):
                        r = score_attr_run(win, at - back, 14)
                        if r:
                            runs.append((back, r))
                    good_examples.append(
                        f"  uid@abs={abs_off} {key}\n"
                        f"    ctx: {ctx.hex(' ')}\n"
                        f"    asc: {''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)}\n"
                        f"    1-20 runs ending/near det: {runs[:4]}"
                    )

            for rel_a, gap, rel_b in find_pair_offsets(win, uid_rel, lea, det, max_gap=8):
                u8_rev_counter[f"u8 lea@+{rel_a} gap={gap} det@+{rel_b}"] += 1

            for rel_a, gap, rel_b in find_u32_pair(win, uid_rel, det, lea):
                u32_pair_counter[f"u32 det@+{rel_a} gap={gap} lea@+{rel_b}"] += 1

        lines.append(f"windows={n_win}")
        lines.append("top u8 det→lea geometries:")
        for k, n in u8_pair_counter.most_common(15):
            lines.append(f"  n={n}  {k}")
        lines.append("top u8 lea→det geometries:")
        for k, n in u8_rev_counter.most_common(10):
            lines.append(f"  n={n}  {k}")
        lines.append("top u32 det→lea geometries:")
        for k, n in u32_pair_counter.most_common(10):
            lines.append(f"  n={n}  {k}")
        lines.append("examples:")
        lines.extend(good_examples or ["  (none)"])

        # Focused scan of the known person-record trail bytes after common name
        # (from earlier): after last name string, for Seimen started 00 0c 11 10...
        name_b = p["name"].encode("utf-8")
        needle = struct.pack("<I", len(name_b)) + name_b
        uid_b = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        found = 0
        abs_base = 0
        carry = b""
        lines.append("person-record name trails (uid+name colocated):")
        for block in stream_blocks():
            data = carry + block
            start = 0
            while found < 3:
                i = data.find(needle, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                if uid_b in data[max(0, i - 160) : i] and abs_off > 1_000_000_000:
                    # bytes immediately after: len + lastName + trail
                    # find end of full name string then optional last name
                    j = i + len(needle)
                    # optional second lp string (lastname)
                    if j + 4 <= len(data):
                        ln = struct.unpack_from("<I", data, j)[0]
                        if 0 < ln < 40 and j + 4 + ln <= len(data):
                            j = j + 4 + ln
                    trail = data[j : j + 96]
                    lines.append(f"  name@abs={abs_off}")
                    lines.append(f"    trail96: {trail.hex(' ')}")
                    lines.append(
                        f"    as u8: {list(trail[:48])}"
                    )
                    # mark det/lea positions in trail
                    for idx, v in enumerate(trail[:64]):
                        if v == det:
                            lines.append(f"    det={det} at trail[{idx}]")
                        if v == lea:
                            lines.append(f"    lea={lea} at trail[{idx}]")
                    found += 1
                start = i + 1
            abs_base += len(block)
            carry = data[-200:]
            if found >= 3:
                break

    lines.append("\n======== CROSS-PLAYER u8 gap consensus (rel of det) ========")
    for geom, ctr in sorted(pair_geom.items()):
        lines.append(f"{geom}: top det rel={ctr.most_common(10)}")

    text = "\n".join(lines)
    (OUT / "attr-hunt.txt").write_text(text, encoding="utf-8")
    print(text)
    print("\nwrote", OUT / "attr-hunt.txt")


if __name__ == "__main__":
    main()
