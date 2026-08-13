"""Hunt team/club id 193616 (0x2F450) from First Team shortlist filters."""

from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-team-id-193616.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
TID = 193616
TID_PAT = struct.pack("<I", TID)
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


def main() -> None:
    lines: list[str] = []
    lines.append(f"=== team id {TID} (0x{TID:X}) hunt ===")

    # Pass 1: collect all TID offsets + classify by nearby strings/UIDs
    print("pass1: find all TID hits…", flush=True)
    hits: list[int] = []
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
                start = 0
                while True:
                    j = data.find(TID_PAT, start)
                    if j < 0:
                        break
                    hits.append(chunk_start + j)
                    start = j + 1
                abs_base += len(block)
                carry = data[-8:]
        finally:
            reader.close()

    lines.append(f"TID hits: {len(hits)}")
    print(f"  {len(hits)} hits", flush=True)

    # Sample categories by peeking ±64 around each hit (batched extracts hard;
    # instead stream once more with context)
    print("pass2: classify hits with context...", flush=True)
    categories = Counter()
    interesting: list[tuple[int, str, bytes]] = []
    hits_sorted = sorted(hits)
    hi = 0
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
                chunk_end = chunk_start + len(data)
                while hi < len(hits_sorted) and hits_sorted[hi] < chunk_start + 64:
                    hi += 1
                k = hi
                while k < len(hits_sorted) and hits_sorted[k] <= chunk_end - 64:
                    abs_i = hits_sorted[k]
                    rel = abs_i - chunk_start
                    ctx = data[rel - 64 : rel + 64]
                    kind = "other"
                    if b"First Team" in ctx or b"PlayerSL" in ctx:
                        kind = "shortlist_filter"
                    elif b"Schalke" in ctx:
                        kind = "schalke_near"
                    elif any(struct.pack("<I", u) in ctx for u in UIDS.values()):
                        kind = "fixture_uid_near"
                    elif b"\x01\x00\x6c\x07" in ctx or b"\x00\x6c\x07" in ctx:
                        kind = "obj_6c07_near"
                    uid_n = 0
                    for off in range(0, len(ctx) - 3, 1):
                        v = struct.unpack_from("<I", ctx, off)[0]
                        if UID_LO <= v <= UID_HI:
                            uid_n += 1
                    if uid_n >= 3 and kind == "other":
                        kind = f"uid_dense_{uid_n}"
                    categories[kind] += 1
                    if kind != "shortlist_filter" and kind != "other":
                        interesting.append((abs_i, kind, ctx))
                    k += 1
                abs_base += len(block)
                carry = data[-128:]
        finally:
            reader.close()

    lines.append("categories (approx, overlapping windows may double-count lightly):")
    for k, n in categories.most_common():
        lines.append(f"  {k}: {n}")

    # Dedupe interesting by abs
    seen = set()
    uniq_int = []
    for a, k, ctx in interesting:
        if a in seen:
            continue
        seen.add(a)
        uniq_int.append((a, k, ctx))
    lines.append(f"\ninteresting non-filter hits: {len(uniq_int)}")
    for a, k, ctx in uniq_int[:60]:
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
        lines.append(f"  @{a} {k}")
        lines.append(f"    {asc}")
        lines.append(f"    hex={ctx.hex()}")

    # Deep dive: TID near fixture UniqueIDs in double-UID / name records
    lines.append("\n======== TID near known player doubles ========")
    for name, dbl in [
        ("Seimen", 157471994),
        ("Bandeira", 264934792),
        ("Müller", 279879830),
    ]:
        win = extract(dbl, 4096, before=2048)
        base = dbl - 2048
        offs = []
        start = 0
        while True:
            j = win.find(TID_PAT, start)
            if j < 0:
                break
            offs.append(base + j)
            start = j + 1
        lines.append(f"{name} double±2KB: TID at {offs}")
        # also search personIndex sheet row
    for name, sheet in [
        ("Seimen", 252202),
        ("Bandeira", 206618),
        ("Müller", 209313),
    ]:
        win = extract(sheet, 128, before=16)
        j = win.find(TID_PAT)
        lines.append(f"{name} sheetROW TID: {j}")

    # Find TID occurrences that sit in a long UniqueID array (membership table)
    lines.append("\n======== TID as field inside stride records with UIDs ========")
    # Sample up to 40 TID hits that aren't in the shortlist zone (~100717xxxx)
    non_sl = [h for h in hits if not (1007100000 <= h <= 1007400000)]
    lines.append(f"non-shortlist-zone hits: {len(non_sl)}")
    # cluster TID hits
    clusters = []
    for h in sorted(non_sl):
        if clusters and h - clusters[-1][-1] < 2048:
            clusters[-1].append(h)
        else:
            clusters.append([h])
    clusters.sort(key=len, reverse=True)
    lines.append(f"TID clusters (≥1): {len(clusters)}; top sizes={[len(c) for c in clusters[:15]]}")

    for ci, cl in enumerate(clusters[:8]):
        mid = cl[len(cl) // 2]
        win = extract(mid, 8192, before=4096)
        base = mid - 4096
        lines.append(f"\n-- cluster#{ci} n={len(cl)} center@{mid} range={cl[0]}..{cl[-1]} --")
        # strings
        for needle in (b"Schalke", b"First", b"Reserve", b"U19", b"Team", b"Squad"):
            j = win.find(needle)
            if j >= 0:
                ctx = win[max(0, j - 10) : j + 40]
                s = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
                lines.append(f"  str {needle!r} @{base+j} {s!r}")
        # known UIDs
        for nm, uid in UIDS.items():
            j = win.find(struct.pack("<I", uid))
            if j >= 0:
                lines.append(f"  fixture {nm} @{base+j}")
        # dump around first TID in cluster
        j = win.find(TID_PAT)
        if j >= 0:
            lines.append("  dump around first TID in extract:")
            lines.extend(dump(win[max(0, j - 32) : j + 96], base + max(0, j - 32)))

        # Look for records: [UID][TID] or [TID][UID] pairs
        pair_uid_tid = 0
        pair_tid_uid = 0
        uids_with_tid = []
        for i in range(0, len(win) - 8):
            a = struct.unpack_from("<I", win, i)[0]
            b = struct.unpack_from("<I", win, i + 4)[0]
            if a == TID and UID_LO <= b <= UID_HI:
                pair_tid_uid += 1
                uids_with_tid.append(b)
            if b == TID and UID_LO <= a <= UID_HI:
                pair_uid_tid += 1
                uids_with_tid.append(a)
        lines.append(
            f"  pairs TID→UID={pair_tid_uid} UID→TID={pair_uid_tid} "
            f"unique_uids={len(set(uids_with_tid))}"
        )
        known = [NAME_BY[u] for u in uids_with_tid if u in NAME_BY]
        if known:
            lines.append(f"  known in pairs: {known}")
        if len(set(uids_with_tid)) >= 10:
            # likely membership table!
            uniq = list(dict.fromkeys(uids_with_tid))  # order preserve
            lines.append(f"  MEMBERSHIP CANDIDATE n={len(uniq)}")
            lines.append(f"  uids={uniq[:40]}")

    # Also: check contract-like linkage TID distance from each fixture UID across save
    # (min distance between any TID and any fixture UID hit)
    lines.append("\n======== min distance TID ↔ fixture UID ========")
    for name, uid in UIDS.items():
        # reuse hits from earlier squad hunt? re-scan uid quickly for nearest
        # cheaper: for each TID cluster center extract already done — now dedicated
        nearest = None
        for h in hits[:: max(1, len(hits)//2000)]:  # subsample if huge
            pass
        # do a proper single stream for this uid vs tid
    # Full pairwise is expensive; instead stream and track last seen
    last_tid = None
    last_uid_pos: dict[int, int] = {}
    best: dict[str, tuple[int, int, int]] = {}  # name -> (dist, tid_abs, uid_abs)
    abs_base = 0
    carry = b""
    pats = {uid: struct.pack("<I", uid) for uid in UIDS.values()}
    print("pass3: nearest TID<->UID...", flush=True)
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
                # merge event positions for tid and uids in this chunk
                events: list[tuple[int, str, int]] = []
                start = 0
                while True:
                    j = data.find(TID_PAT, start)
                    if j < 0:
                        break
                    events.append((chunk_start + j, "tid", TID))
                    start = j + 1
                for uid, pat in pats.items():
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        events.append((chunk_start + j, "uid", uid))
                        start = j + 1
                events.sort()
                for abs_i, kind, val in events:
                    if kind == "tid":
                        last_tid = abs_i
                        for uid, upos in last_uid_pos.items():
                            d = abs_i - upos
                            nm = NAME_BY[uid]
                            if nm not in best or d < best[nm][0]:
                                best[nm] = (d, abs_i, upos)
                    else:
                        last_uid_pos[val] = abs_i
                        if last_tid is not None:
                            d = abs_i - last_tid
                            nm = NAME_BY[val]
                            if nm not in best or d < best[nm][0]:
                                best[nm] = (d, last_tid, abs_i)
                abs_base += len(block)
                carry = data[-8:]
        finally:
            reader.close()

    for nm, (d, t, u) in best.items():
        lines.append(f"  {nm}: minΔ={d} tid@{t} uid@{u}")
        # dump that neighborhood
        win = extract(min(t, u), abs(t - u) + 128, before=64)
        base = min(t, u) - 64
        lines.append(f"    neighborhood dump:")
        lines.extend(dump(win, base, min(len(win), 256)))

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii")[:28000])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
