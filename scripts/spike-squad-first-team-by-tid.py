"""First Team via teamId 193616: TID-first, then nearby double-UID."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-first-team-by-tid.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
TID = 193616
TID_PAT = struct.pack("<I", TID)
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000
# From fixture: TID is 2596 / 299 / 395 before double — use 8KB forward scan
FORWARD = 8192


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


def main() -> None:
    lines: list[str] = []
    lines.append(f"=== TID {TID} → forward {FORWARD}B double-UID harvest ===")

    # Pass 1: all TID offsets (fast)
    print("pass1: TID offsets…", flush=True)
    tid_hits: list[int] = []
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
                    tid_hits.append(chunk_start + j)
                    start = j + 1
                abs_base += len(block)
                carry = data[-8:]
        finally:
            reader.close()
    lines.append(f"TID hits: {len(tid_hits)}")
    print(f"  {len(tid_hits)}", flush=True)

    # Pass 2: single stream — when at a TID, scan forward in-window for double-UID
    print("pass2: harvest double-UIDs after TID…", flush=True)
    members: dict[int, dict] = {}  # uid -> best record
    tid_sorted = tid_hits
    ti = 0
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

                # advance ti to TIDs that could affect this chunk
                while ti < len(tid_sorted) and tid_sorted[ti] < chunk_start - FORWARD:
                    ti += 1
                k = ti
                while k < len(tid_sorted) and tid_sorted[k] < chunk_end:
                    tid_abs = tid_sorted[k]
                    # scan [tid_abs+4, tid_abs+FORWARD] for double-UID, data-relative
                    scan_lo = tid_abs + 4 - chunk_start
                    scan_hi = tid_abs + FORWARD - chunk_start
                    scan_lo = max(0, scan_lo)
                    scan_hi = min(len(data) - 8, scan_hi)
                    # 4-byte aligned
                    i = scan_lo - (scan_lo % 4)
                    while i <= scan_hi:
                        uid = struct.unpack_from("<I", data, i)[0]
                        if UID_LO <= uid <= UID_HI:
                            if struct.unpack_from("<I", data, i + 4)[0] == uid:
                                abs_dbl = chunk_start + i
                                delta = abs_dbl - tid_abs
                                if 8 <= delta <= FORWARD:
                                    prev = members.get(uid)
                                    # prefer smallest positive delta (closest TID before double)
                                    if prev is None or delta < prev["tid_delta"]:
                                        members[uid] = {
                                            "uid": uid,
                                            "double_abs": abs_dbl,
                                            "tid_abs": tid_abs,
                                            "tid_delta": delta,
                                        }
                                i += 8
                                continue
                        i += 4
                    k += 1

                abs_base += len(block)
                carry = data[-(FORWARD + 16) :]
        finally:
            reader.close()

    rows = sorted(members.values(), key=lambda m: m["double_abs"])
    lines.append(f"unique players with TID→double: {len(rows)}")
    print(f"  {len(rows)} players", flush=True)

    # Name resolve
    print("resolving names…", flush=True)
    resolved = dict(NAME_BY)
    remaining = [m["uid"] for m in rows if m["uid"] not in resolved]
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
                done = []
                for uid in remaining:
                    pat = pats[uid]
                    j = data.find(pat)
                    if j < 0:
                        continue
                    best = None
                    for off in range(j + 6, min(len(data) - 8, j + 120)):
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
                            done.append(uid)
                for uid in done:
                    if uid in remaining:
                        remaining.remove(uid)
                abs_base += len(block)
                carry = data[-160:]
        finally:
            reader.close()

    # Filter: keep only "canonical" deltas near fixture deltas (100..4000)
    # First report all, then a tight subset matching fixture delta band
    fix_deltas = []
    for n, u in UIDS.items():
        if u in members:
            fix_deltas.append(members[u]["tid_delta"])
    lines.append(f"fixture tidΔs: {fix_deltas}")

    lines.append("\n## ALL TID→double members")
    fix_n = 0
    for i, m in enumerate(rows):
        nm = resolved.get(m["uid"], "?")
        fix = ""
        if m["uid"] in NAME_BY:
            fix = " <<FIX"
            fix_n += 1
        lines.append(
            f"  [{i:03d}] {m['uid']}  {nm}{fix}  "
            f"double@{m['double_abs']} tidΔ={m['tid_delta']}"
        )
    lines.append(f"\nfixture coverage in ALL: {fix_n}/3 total={len(rows)}")

    # Tight band around fixture deltas
    if fix_deltas:
        lo, hi = min(fix_deltas) - 200, max(fix_deltas) + 500
    else:
        lo, hi = 200, 4000
    tight = [m for m in rows if lo <= m["tid_delta"] <= hi]
    lines.append(f"\n## TIGHT band tidΔ [{lo},{hi}] n={len(tight)}")
    fix_n = 0
    for i, m in enumerate(tight):
        nm = resolved.get(m["uid"], "?")
        fix = ""
        if m["uid"] in NAME_BY:
            fix = " <<FIX"
            fix_n += 1
        lines.append(
            f"  [{i:02d}] {m['uid']}  {nm}{fix}  "
            f"double@{m['double_abs']} tidΔ={m['tid_delta']}"
        )
    lines.append(f"fixture coverage in TIGHT: {fix_n}/3")
    missing = [n for n, u in UIDS.items() if u not in {m['uid'] for m in tight}]
    lines.append(f"fixtures missing from TIGHT: {missing}")

    # Even tighter: require personIndex-like field after double (optional sniff)
    # From layout: personIndex around +31 after double
    lines.append("\n## verify personIndex present @double+31 for tight set")
    for m in tight[:5] + [m for m in tight if m["uid"] in NAME_BY]:
        hdr = extract(m["double_abs"], 64, before=0)
        if len(hdr) >= 35:
            pidx = struct.unpack_from("<I", hdr, 31)[0]
            lines.append(
                f"  {resolved.get(m['uid'],'?')} double@{m['double_abs']} "
                f"u32@+31={pidx}"
            )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
