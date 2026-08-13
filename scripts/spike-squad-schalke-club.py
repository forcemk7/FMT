"""Harvest UniqueIDs from Schalke club object; classify First Team if possible."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-schalke-club-uids.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
CLUB = 1986866253
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000
TID = 193616


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


def resolve_names(uids: list[int]) -> dict[int, str]:
    resolved = dict(NAME_BY)
    remaining = [u for u in uids if u not in resolved]
    pats = {u: b"\x00\x02" + struct.pack("<I", u) for u in remaining}
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
                for uid in list(remaining):
                    j = data.find(pats[uid])
                    if j < 0:
                        continue
                    for off in range(j + 6, min(len(data) - 8, j + 140)):
                        ln = struct.unpack_from("<I", data, off)[0]
                        if 5 <= ln <= 48 and off + 4 + ln <= len(data):
                            raw = data[off + 4 : off + 4 + ln]
                            if raw.isascii() and all(32 <= b < 127 for b in raw):
                                name = raw.decode("ascii")
                                if name[0].isupper() and any(c.isalpha() for c in name):
                                    cur = resolved.get(uid, "")
                                    if uid not in resolved or (
                                        " " in name and " " not in cur
                                    ):
                                        resolved[uid] = name
                                    if " " in name and uid in remaining:
                                        remaining.remove(uid)
                                    break
                abs_base += len(block)
                carry = data[-160:]
                if not remaining:
                    break
        finally:
            reader.close()
    return resolved


def main() -> None:
    lines: list[str] = []
    # Club name + trailing object body
    win = extract(CLUB, 100_000, before=2_000)
    base = CLUB - 2_000
    lines.append(f"club window base={base} len={len(win)}")

    j = win.find(b"FC Schalke 04")
    lines.append(f"FC Schalke 04 @{base+j}")

    # Collect UniqueIDs with local context tag (6 bytes before)
    hits = []
    for i in range(0, len(win) - 3):
        v = struct.unpack_from("<I", win, i)[0]
        if UID_LO <= v <= UID_HI:
            pre = win[max(0, i - 8) : i]
            hits.append((base + i, v, pre.hex()))

    # Dedupe preserving first-seen order
    seen = set()
    ordered = []
    for a, v, pre in hits:
        if v in seen:
            continue
        seen.add(v)
        ordered.append((a, v, pre))

    lines.append(f"unique UIDs in club±100KB: {len(ordered)}")
    print(f"unique UIDs: {len(ordered)} — resolving…", flush=True)

    # Focus UIDs that appear with relation-like prefixes (03 .. 02 pattern in pre)
    rel_like = [
        (a, v, pre)
        for a, v, pre in ordered
        if "030102" in pre or "030202" in pre or "0b02" in pre or pre.endswith("0202")
        or "4f" in pre  # Od/O* relation types
    ]
    lines.append(f"relation-like prefixed: {len(rel_like)}")

    # Also: UIDs where TID is within ±64 of the UID
    tid_near = []
    for a, v, pre in ordered:
        rel = a - base
        lo = max(0, rel - 64)
        hi = min(len(win), rel + 64)
        if struct.pack("<I", TID) in win[lo:hi]:
            tid_near.append((a, v))
    lines.append(f"UIDs with TID within ±64: {len(tid_near)}")

    # Primary roster try: unique UIDs between club name and +8KB that look like relation targets
    club_rel = j if j >= 0 else 2000
    region_uids = []
    for a, v, pre in ordered:
        rel = a - base
        if club_rel <= rel <= club_rel + 12000:
            region_uids.append(v)
    region_uids = list(dict.fromkeys(region_uids))
    lines.append(f"UIDs in club name .. +12KB: {len(region_uids)}")

    names = resolve_names(region_uids)
    fix = [NAME_BY[u] for u in region_uids if u in NAME_BY]
    lines.append(f"fixtures in that slice: {fix}")
    lines.append("\n## club name .. +12KB UIDs")
    for i, uid in enumerate(region_uids):
        lines.append(
            f"  [{i:02d}] {uid}  {names.get(uid,'?')}"
            f"{' <<FIX' if uid in NAME_BY else ''}"
        )

    # Broader: first 40KB after club name
    region2 = []
    for a, v, pre in ordered:
        rel = a - base
        if club_rel <= rel <= club_rel + 40000:
            region2.append(v)
    region2 = list(dict.fromkeys(region2))
    lines.append(f"\nUIDs in club name .. +40KB: {len(region2)}")
    names2 = resolve_names(region2)
    fix2 = [NAME_BY[u] for u in region2 if u in NAME_BY]
    lines.append(f"fixtures: {fix2}")
    lines.append("\n## club name .. +40KB UIDs")
    for i, uid in enumerate(region2):
        lines.append(
            f"  [{i:03d}] {uid}  {names2.get(uid,'?')}"
            f"{' <<FIX' if uid in NAME_BY else ''}"
        )

    # Parse typed relations after club short name more carefully
    # Pattern from earlier: 03 4f XX 03 YY 02 <u32>
    lines.append("\n======== typed 03 4f relations after club ========")
    after = win[club_rel : club_rel + 8000]
    after_base = base + club_rel
    i = 0
    rels = []
    while i + 12 <= len(after):
        if after[i] == 0x03 and after[i + 1] == 0x4F:
            code = after[i + 2]
            if after[i + 3] == 0x03 and after[i + 5] == 0x02:
                val = struct.unpack_from("<I", after, i + 6)[0]
                rels.append((after_base + i, code, after[i + 4], val))
                i += 9
                continue
        i += 1
    lines.append(f"relations: {len(rels)}")
    by_code: dict[int, list] = {}
    for a, code, sub, val in rels:
        by_code.setdefault(code, []).append((a, sub, val))
    for code, items in sorted(by_code.items()):
        ch = chr(code) if 32 <= code < 127 else "?"
        lines.append(f"  code=0x{code:02X}('{ch}') n={len(items)}")
        # If values look like UIDs, list them
        uid_vals = [v for _, _, v in items if UID_LO <= v <= UID_HI]
        if uid_vals:
            names = resolve_names(uid_vals)
            for a, sub, v in items:
                if UID_LO <= v <= UID_HI:
                    lines.append(
                        f"    @{a} sub={sub} {v}  {names.get(v,'?')}"
                        f"{' <<FIX' if v in NAME_BY else ''}"
                    )
                else:
                    lines.append(f"    @{a} sub={sub} val={v}")
        else:
            for a, sub, v in items[:8]:
                lines.append(f"    @{a} sub={sub} val={v}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii")[:30000])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
