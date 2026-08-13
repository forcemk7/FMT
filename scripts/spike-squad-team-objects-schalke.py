"""Parse Schalke team subunit objects (First / II / U19) near known II name."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-team-objects-schalke.txt")
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

# From string hunt
II_NAME_ABS = 10087063


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


def lp32(buf: bytes, base: int) -> list[tuple[int, str]]:
    out = []
    i = 0
    while i + 8 <= len(buf):
        ln = struct.unpack_from("<I", buf, i)[0]
        if 2 <= ln <= 80 and i + 4 + ln <= len(buf):
            raw = buf[i + 4 : i + 4 + ln]
            if raw.isascii() and all(32 <= b < 127 for b in raw):
                s = raw.decode("ascii")
                if any(c.isalpha() for c in s):
                    out.append((base + i, s))
                    i += 4 + ln
                    continue
        i += 1
    return out


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
                    best = None
                    for off in range(j + 6, min(len(data) - 8, j + 140)):
                        ln = struct.unpack_from("<I", data, off)[0]
                        if 5 <= ln <= 48 and off + 4 + ln <= len(data):
                            raw = data[off + 4 : off + 4 + ln]
                            if raw.isascii() and all(32 <= b < 127 for b in raw):
                                name = raw.decode("ascii")
                                if name[0].isupper() and any(c.isalpha() for c in name):
                                    if best is None or (" " in name and " " not in best):
                                        best = name
                    if best:
                        resolved[uid] = best
                        if " " in best:
                            remaining.remove(uid)
                abs_base += len(block)
                carry = data[-160:]
                if not remaining:
                    break
        finally:
            reader.close()
    return resolved


def find_uid_lists(buf: bytes, base: int) -> list[dict]:
    found = []
    # count-prefixed
    i = 0
    while i + 8 <= len(buf):
        count = struct.unpack_from("<I", buf, i)[0]
        if 8 <= count <= 50:
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
            if ok and len(set(vals)) >= max(8, int(count * 0.85)):
                known = [NAME_BY[v] for v in vals if v in NAME_BY]
                found.append(
                    {
                        "kind": "count4",
                        "abs": base + i,
                        "count": count,
                        "uids": vals,
                        "known": known,
                        "pre24": buf[max(0, i - 24) : i].hex(),
                    }
                )
                i += 4 + 4 * count
                continue
        i += 1
    return found


def scan_team_window(label: str, name_abs: int, lines: list[str]) -> None:
    lines.append(f"\n######## {label} name@{name_abs} ########")
    # Large local neighbourhood: teams often packed close
    buf = extract(name_abs, 200000, before=150000)
    base = name_abs - 150000
    strings = lp32(buf, base)
    # Show Schalke / U19 / II related names
    for a, s in strings:
        if any(
            k in s
            for k in (
                "Schalke",
                "Under",
                "U19",
                "Junior",
                "II",
                "Amateure",
                "First",
                "Youth",
            )
        ):
            lines.append(f"  str @{a} {s!r}")

    # Dump around the target name
    rel = name_abs - base
    lines.append("dump around name:")
    lines.extend(dump(buf[max(0, rel - 64) : rel + 192], name_abs - min(64, rel), 256))

    # Marker 01 00 6c 07 near names (team object from Reserve template)
    marker = b"\x01\x00\x6c\x07"
    starts = []
    start = 0
    while True:
        j = buf.find(marker, start)
        if j < 0:
            break
        # associate with nearest prior lp32 string
        nearest = None
        for a, s in strings:
            if a < base + j and (nearest is None or a > nearest[0]):
                if base + j - a < 200:
                    nearest = (a, s)
        if nearest and any(
            k in nearest[1]
            for k in ("Schalke", "Under", "U19", "Junior", "II", "Amateure")
        ):
            starts.append((base + j, nearest[1], nearest[0]))
        start = j + 1
    lines.append(f"team-like 6c07 after Schalke/U19 names: {len(starts)}")
    for a, s, sa in starts[:20]:
        lines.append(f"  obj@{a} after_str@{sa} {s!r}")
        # list search in +4KB of object
        sub = buf[a - base : a - base + 4096]
        lists = find_uid_lists(sub, a)
        for L in lists:
            lines.append(
                f"    LIST @{L['abs']} n={L['count']} known={L['known']} pre={L['pre24']}"
            )
            if L["known"]:
                names = resolve_names(L["uids"])
                for idx, uid in enumerate(L["uids"]):
                    lines.append(
                        f"      [{idx:02d}] {uid}  {names.get(uid,'?')}"
                        f"{' <<' + NAME_BY[uid] if uid in NAME_BY else ''}"
                    )

    # Also search for known UIDs in the big window and note which team name is nearest
    lines.append("known UIDs in neighbourhood:")
    for name, uid in KNOWN.items():
        p = buf.find(struct.pack("<I", uid))
        if p < 0:
            lines.append(f"  {name}: not in ±150/200KB window")
            continue
        abs_i = base + p
        # nearest string before
        nearest = None
        for a, s in strings:
            if a <= abs_i and (nearest is None or a > nearest[0]):
                nearest = (a, s)
        lines.append(
            f"  {name} @{abs_i} nearest_str={nearest[1] if nearest else None!r} "
            f"Δ={abs_i - nearest[0] if nearest else None}"
        )


def main() -> None:
    lines: list[str] = []

    # 1) Around II object
    scan_team_window("Schalke 04 II", II_NAME_ABS, lines)

    # 2) Find Schalke U19 / First Team team names via targeted extract near II
    # Often sibling teams share a packed table — expand II window already covers
    # Also global find exact "FC Schalke 04" team objects that are NOT the club @1.98B
    print("finding sibling Schalke team names…", flush=True)
    abs_base = 0
    carry = b""
    schalke_names: list[tuple[int, str]] = []
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
                for needle in (
                    b"FC Schalke 04 II",
                    b"Schalke 04 II",
                    b"FC Schalke 04",
                    b"Schalke 04 U19",
                    b"Schalke 04 Under",
                    b"U19s",
                ):
                    start = 0
                    while True:
                        j = data.find(needle, start)
                        if j < 0:
                            break
                        abs_i = chunk_start + j
                        # skip the giant late club area
                        if abs_i < 500_000_000:
                            schalke_names.append(
                                (abs_i, needle.decode("latin-1", "replace"))
                            )
                        start = j + 1
                abs_base += len(block)
                carry = data[-80:]
        finally:
            reader.close()

    # Dedup / show early hits (team table, not late club)
    seen = set()
    lines.append("\n======== early Schalke* team-name hits (<500MB) ========")
    for a, s in sorted(schalke_names):
        key = (a // 64, s)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  @{a} {s!r}")

    # Dig each unique early FC Schalke 04 (non-II) as possible First Team object
    first_cands = [
        a
        for a, s in schalke_names
        if s == "FC Schalke 04" and a < 50_000_000 and abs(a - II_NAME_ABS) < 5_000_000
    ]
    lines.append(f"\nFirst Team candidate name abs near II: {first_cands[:10]}")
    for a in first_cands[:3]:
        scan_team_window(f"FC Schalke 04?@{a}", a, lines)

    # U19 name near II
    u19_cands = [
        a
        for a, s in schalke_names
        if ("U19" in s or "Under" in s) and abs(a - II_NAME_ABS) < 2_000_000
    ]
    lines.append(f"\nU19 candidates near II: {u19_cands[:10]}")
    for a in u19_cands[:3]:
        scan_team_window(f"U19?@{a}", a, lines)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii")[:35000])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
