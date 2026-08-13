"""Dig squad-list candidates: stride-174 region + Schalke club object."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-list-dig.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
UID_LO, UID_HI = 1_000_000_000, 3_000_000_000

TARGETS = {
    "stride174_region": 813373363,
    "schalke_club_obj": 1986866256,
    "tight_seimen_band": 1966014746,
    "tight_seimen_mull": 1974444727,
    "all3_alt": 1007145540,
}


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


def dump_hex(b: bytes, base: int, width: int = 32) -> list[str]:
    lines = []
    for i in range(0, len(b), width):
        chunk = b[i : i + width]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"  {base+i:10d}  {hexs:<{width*3}}  {asc}")
    return lines


def uids_in(buf: bytes, base: int) -> list[tuple[int, int, str | None]]:
    out = []
    for i in range(0, len(buf) - 3):
        v = struct.unpack_from("<I", buf, i)[0]
        if UID_LO <= v <= UID_HI:
            out.append((base + i, v, NAME_BY.get(v)))
    return out


def walk_stride(buf: bytes, base: int, start_rel: int, stride: int, n: int = 40):
    rows = []
    for k in range(n):
        off = start_rel + k * stride
        if off + 4 > len(buf):
            break
        uid = struct.unpack_from("<I", buf, off)[0]
        head = buf[off : off + min(64, stride)]
        rows.append(
            {
                "abs": base + off,
                "uid": uid,
                "name": NAME_BY.get(uid),
                "is_uid": UID_LO <= uid <= UID_HI,
                "head": head.hex(),
            }
        )
    return rows


def main() -> None:
    lines: list[str] = []

    # ---- 1) stride 174 around Seimen/Band/Mull ----
    center = TARGETS["stride174_region"]
    buf = extract(center, 8000, before=4000)
    base = center - 4000
    lines.append("======== REGION stride174 (~813373363) ========")
    # find Seimen offset in buf
    pat = struct.pack("<I", UIDS["Dennis Seimen"])
    rels = []
    start = 0
    while True:
        j = buf.find(pat, start)
        if j < 0:
            break
        rels.append(j)
        start = j + 1
    lines.append(f"Seimen rels in extract: {rels}")
    for rel in rels[:3]:
        for stride in (170, 172, 174, 176, 178, 180, 184, 188, 192, 196, 200):
            rows = walk_stride(buf, base, rel, stride, 35)
            known = [r for r in rows if r["name"]]
            uidish = sum(1 for r in rows if r["is_uid"])
            if len(known) >= 2 or uidish >= 15:
                lines.append(
                    f"  stride={stride} from Seimen@{base+rel}: "
                    f"uidish={uidish}/{len(rows)} known={[r['name'] for r in known]}"
                )
                for r in rows[:25]:
                    mark = f" **{r['name']}" if r["name"] else ""
                    lines.append(
                        f"    [{r['abs']}] uid={r['uid']} ok={r['is_uid']}{mark}"
                    )
                    lines.append(f"      head32={r['head'][:64]}")

    # Also check Band-relative
    patb = struct.pack("<I", UIDS["Patrick Bandeira"])
    jb = buf.find(patb)
    if jb >= 0:
        lines.append(f"\nBandeira@{base+jb}; delta from nearest Seimen:")
        if rels:
            lines.append(f"  Δ={jb-rels[0]}")
        # dump bytes between Seimen and Band
        if rels:
            lo, hi = sorted([rels[0], jb])
            lines.append("bytes between first Seimen and Band:")
            lines.extend(dump_hex(buf[lo:hi], base + lo))

    # ---- 2) Schalke club object ----
    center = TARGETS["schalke_club_obj"]
    buf = extract(center, 12000, before=4000)
    base = center - 4000
    lines.append("\n======== SCHALKE CLUB OBJECT ========")
    # show string area
    j = buf.find(b"FC Schalke 04")
    lines.append(f"FC Schalke 04 rel={j} abs={base+j if j>=0 else None}")
    if j >= 0:
        lines.extend(dump_hex(buf[max(0, j - 128) : j + 256], base + max(0, j - 128)))

    # find known UIDs relative to club string
    uhits = uids_in(buf, base)
    known_hits = [u for u in uhits if u[2]]
    lines.append(f"UID-like in window: {len(uhits)}; known hits: {len(known_hits)}")
    for a, v, n in known_hits[:30]:
        lines.append(f"  @{a} {n}={v} rel_club={(a-(base+j)) if j>=0 else '?'}")

    # Look for count-prefixed UID lists near club string
    # Pattern: u32 count (10..80), then count * u32 UIDs
    lines.append("\ncount-prefixed UID lists near club (±8KB):")
    for i in range(0, len(buf) - 8):
        count = struct.unpack_from("<I", buf, i)[0]
        if not (8 <= count <= 60):
            continue
        ok = True
        vals = []
        for k in range(count):
            off = i + 4 + k * 4
            if off + 4 > len(buf):
                ok = False
                break
            v = struct.unpack_from("<I", buf, off)[0]
            if not (UID_LO <= v <= UID_HI):
                ok = False
                break
            vals.append(v)
        if not ok:
            continue
        known = [NAME_BY[v] for v in vals if v in NAME_BY]
        if len(set(vals)) < count * 0.7:
            continue  # too many dupes — not a roster
        if known or (j >= 0 and abs(i - j) < 2000):
            lines.append(
                f"  @{base+i} count={count} unique={len(set(vals))} "
                f"known={known} rel_club={(i-j) if j>=0 else '?'}"
            )
            lines.append(f"    uids={vals[:25]}{'...' if count>25 else ''}")
            lines.append(f"    pre16={buf[max(0,i-16):i].hex()}")

    # Broader: personIndex lists? 1198, 1790, 1233 as u32 arrays
    lines.append("\npersonIndex packed lists (look for 1790/1198/1233):")
    idxs = {"Seimen": 1790, "Bandeira": 1198, "Müller": 1233}
    for name, idx in idxs.items():
        pat = struct.pack("<I", idx)
        # only report near club
        start = 0
        found = 0
        while found < 5:
            p = buf.find(pat, start)
            if p < 0:
                break
            lines.append(f"  {name} personIndex@{base+p} rel_club={(p-j) if j>=0 else '?'}")
            # check if surrounded by other small ints (index list)
            window = buf[max(0, p - 40) : p + 80]
            smalls = [struct.unpack_from("<I", window, k)[0] for k in range(0, len(window) - 3, 4)]
            lines.append(f"    nearby u32s={smalls}")
            start = p + 1
            found += 1

    # ---- 3) Tight Seimen-Band (Δ=18) ----
    center = TARGETS["tight_seimen_band"]
    buf = extract(center, 512, before=128)
    base = center - 128
    lines.append("\n======== TIGHT Seimen↔Bandeira Δ=18 ========")
    lines.extend(dump_hex(buf, base))
    lines.append(f"uids: {[(a,n or v) for a,v,n in uids_in(buf, base)]}")

    # ---- 4) Wider scan around Schalke for team subsection strings ----
    center = TARGETS["schalke_club_obj"]
    buf = extract(center, 200000, before=50000)
    base = center - 50000
    lines.append("\n======== STRINGS near Schalke club (±50KB/+200KB) ========")
    for needle in (
        b"First",
        b"Reserve",
        b"U19",
        b"U18",
        b"U21",
        b"Youth",
        b"Senior",
        b"Squad",
        b"Schalke",
        b"II",
        b"Amateure",
    ):
        start = 0
        n = 0
        while n < 8:
            j = buf.find(needle, start)
            if j < 0:
                break
            ctx = buf[max(0, j - 12) : j + len(needle) + 40]
            s = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
            lines.append(f"  @{base+j} {needle!r} {s!r}")
            start = j + 1
            n += 1

    # Count-prefixed UID lists in this bigger window with ≥2 known
    lines.append("\n======== count-prefixed UID lists with ≥1 known (big window) ========")
    found_lists = []
    i = 0
    while i + 8 <= len(buf):
        count = struct.unpack_from("<I", buf, i)[0]
        if 10 <= count <= 70:
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
            if ok:
                known = [NAME_BY[v] for v in vals if v in NAME_BY]
                if known and len(set(vals)) >= count * 0.8:
                    found_lists.append(
                        {
                            "abs": base + i,
                            "count": count,
                            "known": known,
                            "uids": vals,
                            "pre32": buf[max(0, i - 32) : i].hex(),
                        }
                    )
                    i += 4 + 4 * count
                    continue
        i += 1
    lines.append(f"found {len(found_lists)} lists")
    for L in found_lists[:40]:
        lines.append(
            f"  @{L['abs']} count={L['count']} known={L['known']} "
            f"unique={len(set(L['uids']))}"
        )
        lines.append(f"    head={L['uids'][:15]}")
        lines.append(f"    pre32={L['pre32']}")

    all3 = [L for L in found_lists if len(set(L["known"])) >= 3]
    lines.append(f"\nlists with all 3 fixtures: {len(all3)}")
    for L in all3:
        idxs = {NAME_BY[u]: L["uids"].index(u) for u in L["uids"] if u in NAME_BY}
        lines.append(f"  @{L['abs']} count={L['count']} indices={idxs}")
        lines.append(f"    ALL uids={L['uids']}")
        lines.append(f"    pre32={L['pre32']}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
