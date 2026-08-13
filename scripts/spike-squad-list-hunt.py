"""Faster First Team / squad-list hunt.

Pass 1: locate known UniqueID offsets only.
Pass 2: extract windows around multi-UID clusters; look for packed UID arrays.
"""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-list-hunt.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY_UID = {v: k for k, v in UIDS.items()}
KNOWN = list(UIDS.values())
UID_LO = 1_000_000_000
UID_HI = 3_000_000_000


def stream_known_hits() -> dict[int, list[int]]:
    pats = {uid: struct.pack("<I", uid) for uid in KNOWN}
    hits: dict[int, list[int]] = {uid: [] for uid in KNOWN}
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
    for uid in hits:
        hits[uid] = sorted(set(hits[uid]))
    return hits


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


def cluster_events(hits: dict[int, list[int]], window: int) -> list[dict]:
    events = [(o, uid) for uid, offs in hits.items() for o in offs]
    events.sort()
    out = []
    n = len(events)
    i = 0
    while i < n:
        j = i
        uids = {events[i][1]}
        while j + 1 < n and events[j + 1][0] - events[i][0] <= window:
            j += 1
            uids.add(events[j][1])
        if len(uids) >= 2:
            out.append(
                {
                    "start": events[i][0],
                    "end": events[j][0],
                    "span": events[j][0] - events[i][0],
                    "uids": sorted(uids),
                    "names": [NAME_BY_UID[u] for u in sorted(uids)],
                    "positions": [(a, NAME_BY_UID[u]) for a, u in events[i : j + 1]],
                }
            )
        nxt = i + 1
        while nxt < n and events[nxt][0] == events[i][0]:
            nxt += 1
        i = nxt
    # unique by start-bucket + uid set
    seen = set()
    deduped = []
    for c in out:
        key = (c["start"] // 128, tuple(c["uids"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    deduped.sort(key=lambda c: (-len(c["uids"]), c["span"], c["start"]))
    return deduped


def find_strict_arrays(buf: bytes, base: int) -> list[dict]:
    """Stride-4 UniqueID runs; step by 4 after a miss (fast)."""
    arrays = []
    i = 0
    n = len(buf)
    while i + 4 <= n:
        v = struct.unpack_from("<I", buf, i)[0]
        if not (UID_LO <= v <= UID_HI):
            i += 1
            continue
        vals = []
        j = i
        while j + 4 <= n:
            vv = struct.unpack_from("<I", buf, j)[0]
            if not (UID_LO <= vv <= UID_HI):
                break
            vals.append(vv)
            j += 4
        if len(vals) >= 8:
            known = [u for u in vals if u in NAME_BY_UID]
            arrays.append(
                {
                    "abs": base + i,
                    "n": len(vals),
                    "unique": len(set(vals)),
                    "known": [NAME_BY_UID[u] for u in known],
                    "uids": vals,
                    "pre32": buf[max(0, i - 32) : i].hex(),
                }
            )
        i = max(i + 4, j)
    arrays.sort(key=lambda a: (-len(a["known"]), -a["unique"], a["abs"]))
    return arrays


def find_record_arrays(buf: bytes, base: int, strides: list[int]) -> list[dict]:
    """UniqueID at start of fixed-stride records (UID every `stride` bytes)."""
    out: list[dict] = []
    for stride in strides:
        i = 0
        while i + stride * 8 <= len(buf):
            v0 = struct.unpack_from("<I", buf, i)[0]
            if not (UID_LO <= v0 <= UID_HI):
                i += 1
                continue
            vals: list[int] = []
            j = i
            while j + 4 <= len(buf) and len(vals) < 80:
                v = struct.unpack_from("<I", buf, j)[0]
                if not (UID_LO <= v <= UID_HI):
                    break
                vals.append(v)
                j += stride
            if len(vals) >= 8:
                known = [u for u in vals if u in NAME_BY_UID]
                if known:
                    out.append(
                        {
                            "abs": base + i,
                            "stride": stride,
                            "n": len(vals),
                            "unique": len(set(vals)),
                            "known": [NAME_BY_UID[u] for u in known],
                            "uids": vals,
                            "pre32": buf[max(0, i - 32) : i].hex(),
                        }
                    )
                i += stride
            else:
                i += 1
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for a in sorted(out, key=lambda x: (-len(x["known"]), -x["n"], x["abs"])):
        key = (a["abs"] // 8, a["stride"], a["n"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(a)
    return deduped[:40]


def strings_near(buf: bytes, base: int) -> list[str]:
    out = []
    needles = [
        b"Schalke",
        b"First",
        b"Reserve",
        b"U19",
        b"U18",
        b"Youth",
        b"Senior",
        b"Squad",
        b"Team",
    ]
    for needle in needles:
        start = 0
        while True:
            j = buf.find(needle, start)
            if j < 0:
                break
            ctx = buf[max(0, j - 8) : j + len(needle) + 24]
            # keep printable
            try:
                s = ctx.decode("latin-1")
            except Exception:
                s = repr(ctx)
            out.append(f"@{base+j} {needle!r} ctx={s!r}")
            start = j + 1
            if len(out) >= 30:
                return out
    return out


def main() -> None:
    lines: list[str] = []
    lines.append("=== squad-list hunt (fast) ===")
    lines.append(f"save={SAVE.name}")
    print("pass1: known UID hits…", flush=True)
    hits = stream_known_hits()
    for uid, offs in hits.items():
        lines.append(f"{NAME_BY_UID[uid]}: {len(offs)} hits")
        print(f"  {NAME_BY_UID[uid]}: {len(offs)}", flush=True)

    for window in (256, 1024, 4096, 16384):
        cs = cluster_events(hits, window)
        all3 = [c for c in cs if len(c["uids"]) == 3]
        lines.append(
            f"\n## window={window}: clusters={len(cs)} all3={len(all3)}"
        )
        print(f"window={window}: clusters={len(cs)} all3={len(all3)}", flush=True)
        for c in (all3[:12] if all3 else cs[:8]):
            lines.append(
                f"  @{c['start']}..{c['end']} span={c['span']} names={c['names']}"
            )
            lines.append(
                "    "
                + ", ".join(f"{a}:{n}" for a, n in c["positions"][:10])
            )

    # Deep dive distinct all3 regions (4KB)
    all3 = [c for c in cluster_events(hits, 4096) if len(c["uids"]) == 3]
    # collapse overlapping
    regions = []
    for c in all3:
        if regions and c["start"] <= regions[-1]["end"] + 2048:
            regions[-1]["end"] = max(regions[-1]["end"], c["end"])
            regions[-1]["names"] = sorted(
                set(regions[-1]["names"]) | set(c["names"])
            )
        else:
            regions.append(
                {"start": c["start"], "end": c["end"], "names": list(c["names"])}
            )

    lines.append(f"\n======== deep dive regions n={len(regions)} ========")
    print(f"deep dive {len(regions)} regions…", flush=True)

    best_arrays: list[dict] = []
    for idx, r in enumerate(regions[:20]):
        mid = (r["start"] + r["end"]) // 2
        before = mid - r["start"] + 1024
        after = r["end"] - mid + 1024
        # cap extract size
        before = min(before, 20000)
        after = min(after, 20000)
        buf = extract(mid, after, before=before)
        base = mid - before
        lines.append(
            f"\n-- region#{idx} @{r['start']}..{r['end']} "
            f"span={r['end']-r['start']} extract@{base}+{len(buf)} --"
        )
        print(f"  region#{idx} @{r['start']} len={len(buf)}", flush=True)
        for s in strings_near(buf, base)[:12]:
            lines.append(f"  str {s}")

        strict = find_strict_arrays(buf, base)
        with_known = [a for a in strict if a["known"]]
        lines.append(f"  strict arrays: {len(strict)} with_known={len(with_known)}")
        for a in with_known[:8]:
            lines.append(
                f"    @{a['abs']} n={a['n']} unique={a['unique']} known={a['known']}"
            )
            lines.append(f"      head={a['uids'][:20]}")
            lines.append(f"      pre32={a['pre32']}")
            best_arrays.append(a)

        for a in find_record_arrays(buf, base, [8, 12, 16, 20, 24, 28, 32])[:10]:
            if not a["known"]:
                continue
            lines.append(
                f"    stride{a['stride']} @{a['abs']} n={a['n']} "
                f"unique={a['unique']} known={a['known']}"
            )
            lines.append(f"      head={a['uids'][:16]}")
            lines.append(f"      pre32={a['pre32']}")
            best_arrays.append(a)

    # Summarize arrays containing all 3
    lines.append("\n======== ARRAYS WITH ALL 3 ========")
    all3_arrays = [a for a in best_arrays if len(set(a["known"])) >= 3]
    all3_arrays.sort(key=lambda a: (a.get("stride", 4), -a["n"], a["abs"]))
    for a in all3_arrays[:20]:
        lines.append(
            f"  @{a['abs']} stride={a.get('stride', 4)} n={a['n']} "
            f"unique={a['unique']} known={a['known']}"
        )
        # indices of known
        idxs = {NAME_BY_UID[u]: a["uids"].index(u) for u in a["uids"] if u in NAME_BY_UID}
        lines.append(f"    indices={idxs}")
        lines.append(f"    uids={a['uids']}")

    # Also: co-occurrence of UIDs as personIndex? unlikely
    # Pairwise distance histogram for nearest Seimen-Bandeira etc.
    lines.append("\n======== nearest pairwise distances ========")
    names = list(UIDS.keys())
    for a in names:
        for b in names:
            if a >= b:
                continue
            ha, hb = hits[UIDS[a]], hits[UIDS[b]]
            best = None
            ib = 0
            for xa in ha:
                while ib < len(hb) - 1 and hb[ib + 1] <= xa:
                    ib += 1
                for cand in (hb[ib], hb[min(ib + 1, len(hb) - 1)]):
                    d = abs(cand - xa)
                    if best is None or d < best[0]:
                        best = (d, xa, cand)
            if best:
                lines.append(f"  {a}↔{b}: minΔ={best[0]} @{best[1]} / @{best[2]}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = OUT.read_text(encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
