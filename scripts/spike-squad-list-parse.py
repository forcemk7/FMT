"""Single-pass stride-9 squad list finder + name resolve for best candidates."""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-list-parse.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
KNOWN_SET = set(UIDS.values())
UID_LO, UID_HI = 1_000_000_000, 3_000_000_000


def is_uid(v: int) -> bool:
    return UID_LO <= v <= UID_HI


def parse_run(data: bytes, start: int, max_n: int = 60) -> list[tuple[int, int, int]]:
    """Return list of (uid, mid, tail) for stride-9 run starting at start."""
    rows = []
    for k in range(max_n):
        off = start + k * 9
        if off + 9 > len(data):
            break
        uid = struct.unpack_from("<I", data, off)[0]
        mid = struct.unpack_from("<I", data, off + 4)[0]
        tail = data[off + 8]
        if not is_uid(uid):
            break
        rows.append((uid, mid, tail))
    return rows


def main() -> None:
    lines: list[str] = []
    lines.append("=== stride-9 squad lists (single pass) ===")

    # Pass 1: stream; whenever a known UID appears, try stride-9 parse
    candidates: list[dict] = []
    seen_starts: set[int] = set()

    abs_base = 0
    carry = b""
    pats = {uid: struct.pack("<I", uid) for uid in KNOWN_SET}

    print("pass1: stream stride-9…", flush=True)
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

                # find known UID offsets in this window
                hit_rels: list[tuple[int, int]] = []
                for uid, pat in pats.items():
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        # only process hits that have 9*40 bytes ahead in `data`
                        if j + 9 * 8 <= len(data) and j >= 9 * 5:
                            hit_rels.append((j, uid))
                        start = j + 1

                for rel, uid0 in hit_rels:
                    mid0 = struct.unpack_from("<I", data, rel + 4)[0]
                    # typical flag we've seen is 0x10; accept small flags
                    if mid0 not in (0x00, 0x08, 0x10, 0x20, 0x40, 0x80):
                        continue
                    # walk back
                    start = rel
                    while start - 9 >= 0:
                        uid = struct.unpack_from("<I", data, start - 9)[0]
                        mid = struct.unpack_from("<I", data, start - 9 + 4)[0]
                        if not is_uid(uid):
                            break
                        if mid != mid0:
                            break
                        start -= 9
                    abs_start = chunk_start + start
                    if abs_start in seen_starts:
                        continue
                    rows = parse_run(data, start, 60)
                    if len(rows) < 8:
                        continue
                    # require stable mid for majority
                    same = sum(1 for u, m, t in rows if m == mid0)
                    if same < max(8, len(rows) * 0.75):
                        continue
                    known = sorted({NAME_BY[u] for u, _, _ in rows if u in NAME_BY})
                    if len(known) < 2:
                        continue
                    seen_starts.add(abs_start)
                    candidates.append(
                        {
                            "abs": abs_start,
                            "n": len(rows),
                            "mid": mid0,
                            "tail": rows[0][2],
                            "known": known,
                            "uids": [u for u, _, _ in rows],
                            "pre16": data[max(0, start - 16) : start].hex(),
                        }
                    )

                abs_base += len(block)
                # keep enough for back-walk + ahead
                carry = data[-(9 * 50) :]
        finally:
            reader.close()

    candidates.sort(key=lambda c: (-len(c["known"]), -c["n"], c["abs"]))
    lines.append(f"candidates with ≥2 fixtures: {len(candidates)}")
    for c in candidates[:30]:
        lines.append(
            f"  @{c['abs']} n={c['n']} mid=0x{c['mid']:X} known={c['known']} pre16={c['pre16']}"
        )

    all3 = [c for c in candidates if len(c["known"]) >= 3]
    lines.append(f"\nwith all 3 fixtures: {len(all3)}")
    for c in all3[:15]:
        lines.append(f"  @{c['abs']} n={c['n']} uids={c['uids']}")

    # Collect unique UIDs from top lists for name resolution
    top = candidates[:12]
    if all3:
        top = all3[:8] + [c for c in candidates if c not in all3][:4]
    need_uids = []
    for c in top:
        need_uids.extend(c["uids"])
    need_uids = list(dict.fromkeys(need_uids))  # preserve order unique
    lines.append(f"\nresolving names for {len(need_uids)} uids from top lists…")

    # Pass 2: single stream build uid -> name via lp32 after "00 02 UID" near-name pattern
    # Heuristic from prior RE: ... 00 02 UniqueID  lp32(full name)
    print(f"pass2: resolve {len(need_uids)} names…", flush=True)
    need_set = set(need_uids) - set(NAME_BY)
    resolved: dict[int, str] = dict(NAME_BY)
    # also store several candidate names
    name_cands: dict[int, list[str]] = defaultdict(list)

    pats2 = {uid: b"\x00\x02" + struct.pack("<I", uid) for uid in need_set}
    # fallback: raw uid
    pats_raw = {uid: struct.pack("<I", uid) for uid in need_set}

    abs_base = 0
    carry = b""
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

                for uid, pat in pats2.items():
                    if uid in resolved and len(name_cands[uid]) >= 2:
                        continue
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        # lp32 name often within next 8..48 bytes
                        for off in range(j + 6, min(len(data) - 8, j + 80)):
                            ln = struct.unpack_from("<I", data, off)[0]
                            if 3 <= ln <= 48 and off + 4 + ln <= len(data):
                                raw = data[off + 4 : off + 4 + ln]
                                if raw.isascii() and all(32 <= b < 127 for b in raw):
                                    name = raw.decode("ascii")
                                    if name[0].isupper() and any(c.isalpha() for c in name):
                                        name_cands[uid].append(name)
                                        if uid not in resolved:
                                            resolved[uid] = name
                                        break
                        start = j + 1

                abs_base += len(block)
                carry = data[-128:]
        finally:
            reader.close()

    # Fill unresolved via raw uid near lp32 (weaker)
    still = [u for u in need_uids if u not in resolved]
    if still:
        print(f"pass2b: weak resolve {len(still)}…", flush=True)
        abs_base = 0
        carry = b""
        still_set = set(still)
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
                    for uid in list(still_set):
                        pat = pats_raw[uid]
                        j = data.find(pat)
                        if j < 0:
                            continue
                        for off in range(j, min(len(data) - 8, j + 120)):
                            ln = struct.unpack_from("<I", data, off)[0]
                            if 5 <= ln <= 40 and off + 4 + ln <= len(data):
                                raw = data[off + 4 : off + 4 + ln]
                                if raw.isascii() and b" " in raw and raw[0:1].isalpha():
                                    name = raw.decode("ascii")
                                    if name[0].isupper():
                                        resolved[uid] = name
                                        still_set.discard(uid)
                                        break
                    abs_base += len(block)
                    carry = data[-160:]
            finally:
                reader.close()

    lines.append(f"resolved {len(resolved)} / need~{len(need_uids)}")

    # Print top lists with names
    lines.append("\n======== TOP LISTS WITH NAMES ========")
    show = all3[:5] if all3 else top[:5]
    if not show:
        show = candidates[:5]
    for c in show:
        lines.append(
            f"\nLIST @{c['abs']} n={c['n']} mid=0x{c['mid']:X} known_fixtures={c['known']}"
        )
        lines.append(f"  pre16={c['pre16']}")
        for i, uid in enumerate(c["uids"]):
            nm = resolved.get(uid, "?")
            fix = " <<FIX" if uid in NAME_BY else ""
            lines.append(f"  [{i:02d}] {uid}  {nm}{fix}")

    # Stride-174 strip
    lines.append("\n======== stride-174 @813373363 ========")
    # one small targeted decompress via streaming until offset — reuse pass by searching
    # Extract using a single stream seek-style
    target = 813373363
    abs_base = 0
    carry = b""
    buf = None
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
                if chunk_start <= target + 174 * 8 and abs_base + len(block) >= target:
                    # capture
                    lo = max(0, target - chunk_start)
                    hi = min(len(data), target + 174 * 8 - chunk_start)
                    if hi > lo:
                        piece = data[lo:hi]
                        if buf is None:
                            # may start mid-piece
                            if chunk_start + lo == target:
                                buf = bytearray(piece)
                            elif chunk_start < target < abs_base + len(block):
                                buf = bytearray(piece)
                        else:
                            buf.extend(piece)
                abs_base += len(block)
                carry = data[-8:]
                if buf is not None and len(buf) >= 174 * 8:
                    break
        finally:
            reader.close()

    if buf:
        rows174 = []
        for k in range(8):
            off = k * 174
            if off + 4 > len(buf):
                break
            uid = struct.unpack_from("<I", buf, off)[0]
            if not is_uid(uid):
                break
            rows174.append(uid)
        for i, uid in enumerate(rows174):
            lines.append(f"  [{i}] {uid}  {resolved.get(uid, NAME_BY.get(uid, '?'))}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
