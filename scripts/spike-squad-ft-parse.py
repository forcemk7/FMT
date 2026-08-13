#!/usr/bin/env python3
"""Parse teamId 193616 roster window + Schalke First Team team-object @3431104."""

from __future__ import annotations

import json
import struct
from collections import Counter
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-ft-parse.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

KNOWN = {
    "Reserve_II": 2002206353,
    "U19": 2002423570,
}
for p in FIXTURE:
    KNOWN[p["name"]] = int(p["uid"])
NAME_BY = {v: k for k, v in KNOWN.items()}
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000
TID = 193616
TID_PAT = struct.pack("<I", TID)
FT_NAME_ABS = 3_431_104
ROSTER_TID_ABS = 1_042_346_592


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


def dump(b: bytes, base: int, n: int | None = None) -> list[str]:
    if n is not None:
        b = b[:n]
    lines = []
    for i in range(0, len(b), 32):
        chunk = b[i : i + 32]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"  {base+i:10d}  {hexs:<96}  {asc}")
    return lines


def resolve_names(uids: list[int]) -> dict[int, str]:
    resolved = dict(NAME_BY)
    remaining = [u for u in uids if u not in resolved]
    if not remaining:
        return resolved
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
                                    if " " in name or " " not in cur:
                                        resolved[uid] = name
                                    if " " in name and uid in remaining:
                                        remaining.remove(uid)
                                    break
                carry = data[-160:]
                abs_base += len(block)
                if not remaining:
                    break
        finally:
            reader.close()
    return resolved


def scan_tag_uid(blob: bytes, base: int, tag: bytes) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start = 0
    while True:
        j = blob.find(tag, start)
        if j < 0:
            break
        if j + len(tag) + 4 <= len(blob):
            uid = struct.unpack_from("<I", blob, j + len(tag))[0]
            if UID_LO <= uid <= UID_HI:
                out.append((base + j, uid))
        start = j + 1
    return out


def main() -> None:
    lines: list[str] = []

    def log(s: str = "") -> None:
        # avoid Windows console codec crashes
        try:
            print(s)
        except UnicodeEncodeError:
            print(s.encode("ascii", "replace").decode("ascii"))
        lines.append(s)

    # ---- 1) First Team name/object ----
    log("######## First Team team-object around name @3431104 ########")
    win = extract(FT_NAME_ABS, 4096, before=256)
    base = FT_NAME_ABS - 256
    for row in dump(win, base, 512):
        log(row)

    # Is TID nearby?
    tid_pos = win.find(TID_PAT)
    log(f"TID 193616 in window: {('yes @'+str(base+tid_pos)) if tid_pos>=0 else 'no'}")

    # Collect ids after short name
    # short name ends at: name@3431104 len13, then lp10 Schalke 04, then payload
    name_off = 256
    assert win[name_off : name_off + 13] == b"FC Schalke 04"
    post = name_off + 13 + 4 + 10  # after Schalke 04
    log(f"payload starts @ {base+post}")
    payload = win[post : post + 400]
    log("u32 values in first 200 bytes of payload:")
    for i in range(0, min(200, len(payload) - 3), 4):
        v = struct.unpack_from("<I", payload, i)[0]
        mark = ""
        if v == TID:
            mark = " <<TID"
        elif UID_LO <= v <= UID_HI:
            mark = f" <<UID? {NAME_BY.get(v,'')}"
        if v != 0 and v != 0xFFFFFFFF:
            log(f"  +{i:03d} {v} (0x{v:08X}){mark}")

    # ---- 2) Roster TID window ----
    log("\n######## Roster window @1042346592 ########")
    rwin = extract(ROSTER_TID_ABS, 65536, before=64)
    rbase = ROSTER_TID_ABS - 64
    for row in dump(rwin, rbase, 256):
        log(row)

    # Find ALL tags then u32 uiids
    tags_to_try = [
        b"\x0b\x02",
        b"\x7f\x02",
        b"\x02\x00\x00\x00",  # weak
        b"\x09\x0b\x02",
        b"\x03\x02",
    ]
    for tag in tags_to_try:
        hits = scan_tag_uid(rwin, rbase, tag)
        # unique preserve order
        seen = set()
        uids = []
        for a, u in hits:
            if u not in seen:
                seen.add(u)
                uids.append(u)
        names = resolve_names(uids[:80])
        flags = [NAME_BY[u] for u in uids if u in NAME_BY]
        log(f"\ntag {tag.hex()} unique UIDs: {len(uids)} known={flags}")
        if flags or (12 <= len(uids) <= 60):
            for i, u in enumerate(uids[:50]):
                n = names.get(u, "")
                mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
                log(f"  [{i:02d}] {u}  {n}{mark}")

    # Brute: all unique player-range u32s in first 8KB after TID
    tid_rel = 64
    region = rwin[tid_rel : tid_rel + 8192]
    uids_all = []
    seen = set()
    for i in range(0, len(region) - 3):
        v = struct.unpack_from("<I", region, i)[0]
        if UID_LO <= v <= UID_HI and v not in seen:
            # require previous byte looks like a tag often 0x02 or known patterns
            prev = region[i - 1] if i > 0 else 0
            if prev in (0x02, 0x0B, 0x7F, 0x00, 0x01, 0x03, 0x04, 0x09):
                seen.add(v)
                uids_all.append((i, v, prev))
    names = resolve_names([u for _, u, _ in uids_all])
    flags = [NAME_BY[u] for _, u, _ in uids_all if u in NAME_BY]
    log(f"\nbrute u32+prev-tag in +8KB: {len(uids_all)} known={flags}")
    for i, (off, u, prev) in enumerate(uids_all[:60]):
        n = names.get(u, "")
        mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
        log(f"  [{i:02d}] +{off} prev=0x{prev:02X} {u} {n}{mark}")

    # Also scan double UniqueIDs in window
    dbls = []
    seen = set()
    for i in range(0, len(region) - 7):
        v = struct.unpack_from("<Q", region, i)[0]
        if UID_LO <= v <= UID_HI and v not in seen:
            seen.add(v)
            dbls.append((i, v))
    flags = [NAME_BY[u] for _, u in dbls if u in NAME_BY]
    log(f"\ndouble UIDs in +8KB: {len(dbls)} known={flags}")
    names = resolve_names([u for _, u in dbls])
    for i, (off, u) in enumerate(dbls[:40]):
        mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
        log(f"  [{i:02d}] +{off} {u} {names.get(u,'')}{mark}")

    # ---- 3) club relation codes for Reserve/U19 ----
    log("\n######## Club relation codes near club name ########")
    CLUB = 1_986_866_253
    cwin = extract(CLUB, 80000, before=256)
    cbase = CLUB - 256
    j = cwin.find(b"FC Schalke 04")
    after = cwin[j:]
    after_base = cbase + j
    entries = []
    i = 0
    while i + 12 <= len(after):
        if after[i] == 0x03 and after[i + 3] == 0x03 and after[i + 5] == 0x02:
            kind = after[i + 1]
            code = after[i + 2]
            sub = after[i + 4]
            val = struct.unpack_from("<I", after, i + 6)[0]
            if UID_LO <= val <= UID_HI:
                entries.append((after_base + i, kind, code, sub, val))
            i += 6
        else:
            i += 1
    for name, uid in KNOWN.items():
        rows = [(a, k, c, s) for a, k, c, s, v in entries if v == uid]
        log(f"{name}: {len(rows)} relations")
        for a, k, c, s in rows:
            log(f"  @{a} kind=0x{k:02X} code=0x{c:02X} sub={s}")

    # buckets that contain reserve or u19
    by_bucket: dict[tuple[int, int], list[int]] = {}
    for a, k, c, s, v in entries:
        by_bucket.setdefault((k, c), [])
        if v not in by_bucket[(k, c)]:
            by_bucket[(k, c)].append(v)

    for (k, c), uids in sorted(by_bucket.items(), key=lambda kv: -len(kv[1])):
        known_here = [NAME_BY[u] for u in uids if u in NAME_BY]
        if not known_here:
            continue
        if len(uids) < 3 and not any(
            x in known_here for x in ("Reserve_II", "U19")
        ):
            continue
        log(f"\nbucket kind=0x{k:02X} code=0x{c:02X} n={len(uids)} known={known_here}")
        names = resolve_names(uids)
        for i, u in enumerate(uids):
            mark = f" <<{NAME_BY[u]}" if u in NAME_BY else ""
            log(f"  [{i:02d}] {u} {names.get(u,'')}{mark}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
