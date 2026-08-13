"""Differentiate First Team / II / U19 via known UIDs.

First Team fixtures: Seimen, Bandeira, Müller
Reserve (II): 2002206353
U19: 2002423570
"""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-subunit-diff.txt")
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
UIDS = list(KNOWN.values())
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000
CLUB = 1986866253


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


def stream_hits() -> dict[int, list[int]]:
    pats = {u: struct.pack("<I", u) for u in UIDS}
    hits = {u: [] for u in UIDS}
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
                for uid, pat in pats.items():
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        hits[uid].append(chunk_start + j)
                        start = j + 1
                abs_base += len(block)
                carry = data[-8:]
        finally:
            reader.close()
    for u in hits:
        hits[u] = sorted(set(hits[u]))
    return hits


def main() -> None:
    lines: list[str] = []
    lines.append("=== subunit diff (FT fixtures vs Reserve vs U19) ===")
    for k, v in KNOWN.items():
        lines.append(f"  {k}={v}")

    print("pass1: UID hits…", flush=True)
    hits = stream_hits()
    for u, offs in hits.items():
        lines.append(f"{NAME_BY[u]}: {len(offs)} hits")

    # Club window relations
    print("pass2: club relations…", flush=True)
    win = extract(CLUB, 50000, before=256)
    base = CLUB - 256
    j = win.find(b"FC Schalke 04")
    after = win[j:]
    after_base = base + j

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

    lines.append("\n======== fixture/reserve/u19 relation codes on club ========")
    for name, uid in KNOWN.items():
        rows = [(a, k, c, s) for a, k, c, s, v in entries if v == uid]
        lines.append(f"{name}:")
        for a, k, c, s in rows:
            lines.append(f"  @{a} kind=0x{k:02X} code=0x{c:02X} sub={s}")

    # Group by (kind, code): which known players share a bucket
    by_bucket: dict[tuple[int, int], list[str]] = defaultdict(list)
    for a, k, c, s, v in entries:
        if v in NAME_BY:
            label = NAME_BY[v]
            if label not in by_bucket[(k, c)]:
                by_bucket[(k, c)].append(label)

    lines.append("\n======== club relation buckets containing ≥1 known ========")
    for (k, c), names in sorted(by_bucket.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"  kind=0x{k:02X} code=0x{c:02X} -> {names}")

    # Full UID lists for buckets that mix FT+Reserve or FT+U19 interestingly
    interesting = []
    for (k, c), names in by_bucket.items():
        has_ft = any(n in names for n in ("Dennis Seimen", "Patrick Bandeira", "Robert Müller"))
        has_r = "Reserve_II" in names
        has_u = "U19" in names
        if has_ft or has_r or has_u:
            interesting.append((k, c, names, has_ft, has_r, has_u))

    lines.append("\n======== full lists for interesting buckets ========")
    for k, c, names, has_ft, has_r, has_u in sorted(
        interesting, key=lambda t: (not t[3], not t[4], not t[5], t[1])
    ):
        uids = list(
            dict.fromkeys(v for a, kk, cc, s, v in entries if kk == k and cc == c)
        )
        lines.append(
            f"\n## kind=0x{k:02X} code=0x{c:02X} n={len(uids)} "
            f"known={names} ft={has_ft} res={has_r} u19={has_u}"
        )
        for i, uid in enumerate(uids):
            mark = f" <<{NAME_BY[uid]}" if uid in NAME_BY else ""
            lines.append(f"  [{i:02d}] {uid}{mark}")

    # Search strings: Schalke 04 II, Under 19, U19 near club / known UIDs
    print("pass3: squad name strings…", flush=True)
    lines.append("\n======== squad subunit name strings (global sample) ========")
    needles = [
        b"Schalke 04 II",
        b"FC Schalke 04 II",
        b"Under 19",
        b"U19",
        b"Junioren",
        b"Amateure",
        b"Squads",
    ]
    abs_base = 0
    carry = b""
    found_str: list[tuple[int, str, bytes]] = []
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
                for needle in needles:
                    start = 0
                    n = 0
                    while n < 20:
                        j = data.find(needle, start)
                        if j < 0:
                            break
                        abs_i = chunk_start + j
                        ctx = data[max(0, j - 40) : j + len(needle) + 60]
                        found_str.append(
                            (abs_i, needle.decode("latin-1", "replace"), ctx)
                        )
                        start = j + 1
                        n += 1
                abs_base += len(block)
                carry = data[-100:]
        finally:
            reader.close()

    # Dedup by abs
    seen = set()
    for abs_i, lab, ctx in sorted(found_str, key=lambda t: t[0]):
        if abs_i in seen:
            continue
        seen.add(abs_i)
        # Prefer near club or near our UIDs
        near_uid = any(abs(abs_i - h) < 50000 for offs in hits.values() for h in offs[:3])
        near_club = abs(abs_i - CLUB) < 200000
        if not (near_club or near_uid or "II" in lab or "Under" in lab or "Junior" in lab):
            continue
        s = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
        lines.append(f"  @{abs_i} {lab!r} near_club={near_club}")
        lines.append(f"    {s}")

    # Co-occurrence: find windows containing Reserve XOR U19 XOR (2+ FT)
    lines.append("\n======== tight co-occurrence clusters (2KB) ========")
    events = [(o, u) for u, offs in hits.items() for o in offs]
    events.sort()
    window = 2048
    clusters = []
    i = 0
    while i < len(events):
        j = i
        set_u = {events[i][1]}
        while j + 1 < len(events) and events[j + 1][0] - events[i][0] <= window:
            j += 1
            set_u.add(events[j][1])
        if len(set_u) >= 2:
            names = sorted(NAME_BY[u] for u in set_u)
            clusters.append(
                {
                    "start": events[i][0],
                    "end": events[j][0],
                    "names": names,
                    "n": len(set_u),
                }
            )
        i += 1
        while i < len(events) and events[i][0] == events[i - 1][0]:
            i += 1

    # Prefer clusters that separate subunits
    def score(c):
        n = set(c["names"])
        ft = sum(
            x in n for x in ("Dennis Seimen", "Patrick Bandeira", "Robert Müller")
        )
        return (ft, "Reserve_II" in n, "U19" in n, -c["end"] + c["start"])

    # Unique by start bucket
    seen_c = set()
    uniq_c = []
    for c in sorted(clusters, key=score, reverse=True):
        key = (c["start"] // 256, tuple(c["names"]))
        if key in seen_c:
            continue
        seen_c.add(key)
        uniq_c.append(c)

    for c in uniq_c[:40]:
        lines.append(
            f"  @{c['start']}..{c['end']} span={c['end']-c['start']} {c['names']}"
        )

    # Dig best mixed clusters for list structure
    print("pass4: dig best clusters…", flush=True)
    targets = []
    for c in uniq_c:
        n = set(c["names"])
        if "U19" in n and any(
            x in n for x in ("Dennis Seimen", "Patrick Bandeira", "Robert Müller", "Reserve_II")
        ):
            targets.append(c)
        if "Reserve_II" in n and any(
            x in n for x in ("Dennis Seimen", "Patrick Bandeira", "Robert Müller", "U19")
        ):
            targets.append(c)
        if sum(x in n for x in ("Dennis Seimen", "Patrick Bandeira", "Robert Müller")) >= 2 and (
            "Reserve_II" in n or "U19" in n
        ):
            targets.append(c)

    lines.append(f"\n======== dig mixed clusters n={len(targets)} ========")
    for c in targets[:8]:
        mid = (c["start"] + c["end"]) // 2
        buf = extract(mid, 4000, before=2000)
        bbase = mid - 2000
        lines.append(f"\n-- @{c['start']}..{c['end']} {c['names']} --")
        # strings
        for needle in (
            b"Schalke",
            b"First",
            b"Under",
            b"U19",
            b"II",
            b"Junior",
            b"Squad",
        ):
            p = buf.find(needle)
            if p >= 0:
                ctx = buf[max(0, p - 8) : p + 40]
                s = "".join(chr(x) if 32 <= x < 127 else "." for x in ctx)
                lines.append(f"  str {needle!r} @{bbase+p} {s!r}")
        # marked positions
        for name, uid in KNOWN.items():
            if name not in c["names"]:
                continue
            p = buf.find(struct.pack("<I", uid))
            if p >= 0:
                lines.append(
                    f"  {name} @{bbase+p} pre8={buf[max(0,p-8):p].hex()}"
                )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
