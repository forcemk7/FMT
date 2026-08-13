"""Dig 'First Team Squad' objects near 1007250046 and Schalke team units."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-first-team-obj.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
UID_LO, UID_HI = 1_000_000_000, 3_000_000_000


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


def dump(b: bytes, base: int, n: int = 512) -> list[str]:
    lines = []
    b = b[:n]
    for i in range(0, len(b), 32):
        chunk = b[i : i + 32]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"  {base+i:10d}  {hexs:<96}  {asc}")
    return lines


def find_lp32(buf: bytes, base: int) -> list[tuple[int, str]]:
    out = []
    i = 0
    while i + 8 <= len(buf):
        ln = struct.unpack_from("<I", buf, i)[0]
        if 3 <= ln <= 80 and i + 4 + ln <= len(buf):
            raw = buf[i + 4 : i + 4 + ln]
            if raw.isascii() and all(32 <= b < 127 for b in raw):
                s = raw.decode("ascii")
                if any(c.isalpha() for c in s):
                    out.append((base + i, s))
                    i += 4 + ln
                    continue
        i += 1
    return out


def known_uids_in(buf: bytes, base: int):
    out = []
    for name, uid in UIDS.items():
        pat = struct.pack("<I", uid)
        start = 0
        while True:
            j = buf.find(pat, start)
            if j < 0:
                break
            out.append((base + j, name, uid))
            start = j + 1
    out.sort()
    return out


def count_prefixed_uid_lists(buf: bytes, base: int, min_n=12, max_n=60):
    found = []
    i = 0
    while i + 8 <= len(buf):
        count = struct.unpack_from("<I", buf, i)[0]
        if min_n <= count <= max_n:
            vals = []
            ok = True
            for k in range(count):
                off = i + 4 + 4 * k
                if off + 4 > len(buf):
                    ok = False
                    break
                v = struct.unpack_from("<I", buf, off)[0]
                if not (UID_LO <= v <= UID_HI):
                    ok = False
                    break
                vals.append(v)
            if ok and len(set(vals)) >= count * 0.85:
                known = [NAME_BY[v] for v in vals if v in NAME_BY]
                found.append(
                    {
                        "abs": base + i,
                        "count": count,
                        "known": known,
                        "uids": vals,
                        "pre24": buf[max(0, i - 24) : i].hex(),
                    }
                )
                i += 4 + 4 * count
                continue
        i += 1
    return found


def stride9_lists(buf: bytes, base: int):
    found = []
    i = 0
    while i + 9 * 10 <= len(buf):
        uid = struct.unpack_from("<I", buf, i)[0]
        if not (UID_LO <= uid <= UID_HI):
            i += 1
            continue
        mid = struct.unpack_from("<I", buf, i + 4)[0]
        if mid not in (0x00, 0x08, 0x10, 0x20, 0x40, 0x80):
            i += 1
            continue
        rows = []
        j = i
        while j + 9 <= len(buf) and len(rows) < 70:
            u = struct.unpack_from("<I", buf, j)[0]
            m = struct.unpack_from("<I", buf, j + 4)[0]
            if not (UID_LO <= u <= UID_HI) or m != mid:
                break
            rows.append(u)
            j += 9
        if len(rows) >= 10:
            known = [NAME_BY[u] for u in rows if u in NAME_BY]
            found.append(
                {
                    "abs": base + i,
                    "n": len(rows),
                    "mid": mid,
                    "known": known,
                    "uids": rows,
                }
            )
            i = j
        else:
            i += 1
    return found


def main() -> None:
    lines: list[str] = []

    # Focus region covering all3 cluster + First Team Squad strings
    # all3 @1007145540, First Team Squad @1007250046
    center = 1007250046
    buf = extract(center, 200000, before=150000)
    base = center - 150000
    lines.append(f"======== window base={base} len={len(buf)} ========")

    strings = find_lp32(buf, base)
    lines.append(f"lp32 strings: {len(strings)}")
    for a, s in strings:
        if any(
            k in s
            for k in (
                "First",
                "Reserve",
                "U19",
                "U18",
                "Schalke",
                "Squad",
                "XI",
                "Youth",
                "Senior",
                "Amateure",
            )
        ):
            lines.append(f"  @{a} {s!r}")

    known = known_uids_in(buf, base)
    lines.append(f"\nfixture UID hits in window: {len(known)}")
    for a, n, u in known:
        lines.append(f"  @{a} {n}")

    lines.append("\n--- dumps at each First Team Squad ---")
    for a, s in strings:
        if s != "First Team Squad":
            continue
        rel = a - base
        lines.append(f"\n### First Team Squad @{a}")
        lines.extend(dump(buf[max(0, rel - 64) : rel + 256], a - min(64, rel), 320))
        # look for UID lists in ±8KB of this string
        lo = max(0, rel - 8000)
        hi = min(len(buf), rel + 8000)
        sub = buf[lo:hi]
        sub_base = base + lo
        clists = count_prefixed_uid_lists(sub, sub_base)
        lines.append(f"  count-prefixed UID lists ±8KB: {len(clists)}")
        for L in clists[:10]:
            lines.append(
                f"    @{L['abs']} count={L['count']} known={L['known']} pre24={L['pre24']}"
            )
            if L["known"]:
                lines.append(f"      uids={L['uids']}")
        s9 = stride9_lists(sub, sub_base)
        lines.append(f"  stride9 lists ±8KB: {len(s9)}")
        for L in s9[:8]:
            lines.append(
                f"    @{L['abs']} n={L['n']} mid=0x{L['mid']:X} known={L['known']}"
            )
            if L["known"]:
                lines.append(f"      uids={L['uids']}")

    # Whole window lists with known fixtures
    lines.append("\n======== ALL count-prefixed lists with known in window ========")
    for L in count_prefixed_uid_lists(buf, base):
        if not L["known"]:
            continue
        lines.append(
            f"  @{L['abs']} count={L['count']} known={L['known']} pre24={L['pre24']}"
        )
        if len(set(L["known"])) >= 2:
            lines.append(f"    ALL={L['uids']}")

    lines.append("\n======== stride9 with known in window ========")
    for L in stride9_lists(buf, base):
        if not L["known"]:
            continue
        lines.append(
            f"  @{L['abs']} n={L['n']} mid=0x{L['mid']:X} known={L['known']}"
        )
        if len(set(L["known"])) >= 2:
            lines.append(f"    ALL={L['uids']}")

    # Schalke team units near club object (1986866253)
    lines.append("\n======== Schalke club area team names ========")
    club = 1986866253
    buf2 = extract(club, 500000, before=50000)
    base2 = club - 50000
    strings2 = find_lp32(buf2, base2)
    for a, s in strings2:
        if any(
            k in s
            for k in (
                "Schalke",
                "First",
                "Reserve",
                "U19",
                "U18",
                "U21",
                "Amateure",
                "Youth",
                "Senior",
                "II",
            )
        ):
            lines.append(f"  @{a} {s!r}")

    known2 = known_uids_in(buf2, base2)
    lines.append(f"\nfixture UIDs near club big window: {len(known2)}")
    for a, n, u in known2[:40]:
        lines.append(f"  @{a} {n}")

    # Find team objects matching Reserve pattern: lp32 name + ... + 01 00 6c 07
    lines.append("\n======== team-like objects (name near 01 00 6c 07) ========")
    marker = b"\x01\x00\x6c\x07"
    start = 0
    n = 0
    while n < 40:
        j = buf2.find(marker, start)
        if j < 0:
            break
        # look backward for lp32 string within 80 bytes
        region = buf2[max(0, j - 80) : j]
        names_near = []
        for off in range(len(region) - 8):
            ln = struct.unpack_from("<I", region, off)[0]
            if 3 <= ln <= 60 and off + 4 + ln <= len(region):
                raw = region[off + 4 : off + 4 + ln]
                if raw.isascii() and all(32 <= b < 127 for b in raw):
                    names_near.append(raw.decode("ascii"))
        if names_near:
            lines.append(f"  @{base2+j} names_before={names_near[-3:]}")
            # dump a bit after marker for player refs
            after = buf2[j : j + 128]
            lines.append(f"    after={after[:64].hex()}")
        start = j + 1
        n += 1

    # Search specifically for "Schalke" team records using Reserves template near club
    lines.append("\n======== Schalke string contexts (team?) ========")
    start = 0
    shown = 0
    while shown < 25:
        j = buf2.find(b"Schalke", start)
        if j < 0:
            break
        ctx = buf2[max(0, j - 40) : j + 80]
        s = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
        # skip pure club name record we already know around 1986866253
        lines.append(f"  @{base2+j} {s!r}")
        start = j + 1
        shown += 1

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii")[:25000])
    print(f"\n... wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
