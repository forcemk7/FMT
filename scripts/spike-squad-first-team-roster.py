"""Parse First Team roster at TID 193616 @ ~1042346592."""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-first-team-roster.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
TID = 193616
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


def resolve_names(uids: list[int]) -> dict[int, str]:
    resolved = dict(NAME_BY)
    need = [u for u in uids if u not in resolved]
    if not need:
        return resolved
    pats = {u: b"\x00\x02" + struct.pack("<I", u) for u in need}
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
                for uid, pat in pats.items():
                    if uid in resolved and uid not in NAME_BY:
                        # already have a candidate
                        continue
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        for off in range(j + 6, min(len(data) - 8, j + 96)):
                            ln = struct.unpack_from("<I", data, off)[0]
                            if 4 <= ln <= 48 and off + 4 + ln <= len(data):
                                raw = data[off + 4 : off + 4 + ln]
                                if raw.isascii() and all(32 <= b < 127 for b in raw):
                                    name = raw.decode("ascii")
                                    if name[0].isupper() and any(c.isalpha() for c in name):
                                        # prefer names with space (full name)
                                        if uid not in resolved or (
                                            " " not in resolved[uid] and " " in name
                                        ):
                                            resolved[uid] = name
                                        break
                        start = j + 1
                abs_base += len(block)
                carry = data[-128:]
                if all(u in resolved for u in need):
                    # still continue a bit for better full names
                    pass
        finally:
            reader.close()
    return resolved


def main() -> None:
    lines: list[str] = []
    anchor = 1042346592
    # Large window after TID — expect full first-team roster
    buf = extract(anchor, 65536, before=256)
    base = anchor - 256
    lines.append(f"======== roster window @{anchor} ========")
    lines.extend(dump(buf[256 - 64 : 256 + 512], anchor - 64, 576))

    # Find TID at start
    rel = buf.find(struct.pack("<I", TID))
    lines.append(f"\nTID rel={rel} abs={base+rel}")

    # Strategy A: after `XX 0b 02` markers, collect following UIDs that look like person records
    # Common pattern from dump: `09 0b 02 <UID> 04 00 00 00 ...`
    lines.append("\n--- 0b 02 tagged UID entries ---")
    entries = []
    i = 0
    while i + 12 <= len(buf):
        if buf[i + 1] == 0x0B and buf[i + 2] == 0x02:
            uid = struct.unpack_from("<I", buf, i + 3)[0]
            if UID_LO <= uid <= UID_HI:
                tag0 = buf[i]
                nxt = struct.unpack_from("<I", buf, i + 7)[0] if i + 11 <= len(buf) else None
                entries.append(
                    {
                        "abs": base + i,
                        "tag0": tag0,
                        "uid": uid,
                        "next_u32": nxt,
                        "tail16": buf[i : i + 16].hex(),
                    }
                )
                i += 3
                continue
        i += 1
    lines.append(f"tagged entries: {len(entries)}")
    for e in entries[:50]:
        lines.append(
            f"  @{e['abs']} tag0=0x{e['tag0']:02X} uid={e['uid']} next={e['next_u32']} "
            f"{e['tail16']}"
        )

    # Strategy B: walk from TID: headers then list of records starting with UID
    # From dump: TID, 03 00 00 00, 09 0b 02, UID, 04..., then nested until next UID?
    lines.append("\n--- sequential UID scan after TID (any alignment) ---")
    start = rel + 4 if rel >= 0 else 256
    uids_seq = []
    for i in range(start, min(len(buf), start + 20000)):
        v = struct.unpack_from("<I", buf, i)[0]
        if UID_LO <= v <= UID_HI:
            # filter false positives: require nearby small structural bytes
            # e.g. previous bytes look like 0b 02 or record header
            pre = buf[max(0, i - 3) : i]
            uids_seq.append((base + i, v, pre.hex()))
    # Deduplicate keeping order, merge close duplicates
    uniq = []
    seen = set()
    for a, v, pre in uids_seq:
        if v in seen:
            continue
        # skip if too many densetimeseries style (UID followed by many repeating u16)
        # Heuristic: if next 4 bytes are small count 1..20 and then NOT another UID quickly
        seen.add(v)
        uniq.append((a, v, pre))
    lines.append(f"unique UIDs after TID in +20KB: {len(uniq)}")

    # Prefer UIDs that appear with `0b 02` prefix (person list form)
    roster_uids = [e["uid"] for e in entries]
    # Also add from uniq if 0b02 in pre
    for a, v, pre in uniq:
        if pre.endswith("0b02") or "0b02" in pre:
            if v not in roster_uids:
                roster_uids.append(v)

    # Better: records with pattern `0b 02 UID` only = cleanest
    roster_uids = list(dict.fromkeys(e["uid"] for e in entries))
    lines.append(f"\nRoster candidates from 0b02 tags: {len(roster_uids)}")

    print(f"resolving {len(roster_uids)} names…", flush=True)
    names = resolve_names(roster_uids)

    known_hits = [NAME_BY[u] for u in roster_uids if u in NAME_BY]
    lines.append(f"fixture players in list: {known_hits}")
    lines.append("\n## ROSTER")
    for i, uid in enumerate(roster_uids):
        nm = names.get(uid, "?")
        fix = " <<FIX" if uid in NAME_BY else ""
        lines.append(f"  [{i:02d}] {uid}  {nm}{fix}")

    # Check if all 3 fixtures present
    missing = [n for n, u in UIDS.items() if u not in set(roster_uids)]
    lines.append(f"\nfixture missing from 0b02 list: {missing}")

    # If missing, widen: include UID→TID adjacency in bigger window
    if missing or len(roster_uids) < 15:
        lines.append("\n--- widen: UIDs within 64KB after TID with mid-record heuristics ---")
        big = extract(anchor, 128 * 1024, before=64)
        bbase = anchor - 64
        # Find all 0b02 UID in big window
        ents = []
        i = 0
        while i + 12 <= len(big):
            if big[i + 1] == 0x0B and big[i + 2] == 0x02:
                uid = struct.unpack_from("<I", big, i + 3)[0]
                if UID_LO <= uid <= UID_HI:
                    ents.append((bbase + i, uid, big[i]))
            i += 1
        # Group continuous regions (gaps < 2KB)
        groups = []
        for a, uid, tag0 in ents:
            if groups and a - groups[-1][-1][0] < 2000:
                groups[-1].append((a, uid, tag0))
            else:
                groups.append([(a, uid, tag0)])
        lines.append(f"0b02 groups in ±64KB: {len(groups)} sizes={[len(g) for g in groups[:20]]}")
        # Pick group containing Seimen or largest near TID
        best = None
        for g in groups:
            uids = [u for _, u, _ in g]
            score = (len(set(uids) & set(UIDS.values())), len(g), -abs(g[0][0] - anchor))
            if best is None or score > best[0]:
                best = (score, g)
        if best:
            g = best[1]
            uids = list(dict.fromkeys(u for _, u, _ in g))
            lines.append(
                f"BEST group @{g[0][0]}..{g[-1][0]} n={len(uids)} "
                f"fixtures={[NAME_BY[u] for u in uids if u in NAME_BY]}"
            )
            names2 = resolve_names(uids)
            lines.append("\n## BEST GROUP ROSTER")
            for i, uid in enumerate(uids):
                nm = names2.get(uid, "?")
                fix = " <<FIX" if uid in NAME_BY else ""
                lines.append(f"  [{i:02d}] {uid}  {nm}{fix}")
            lines.append(
                f"fixtures missing: {[n for n,u in UIDS.items() if u not in set(uids)]}"
            )

    # Also dump the exact 32 bytes at TID for schema notes
    lines.append("\n======== schema note at TID ========")
    lines.append(
        "Observed: <u32 teamId> <u32 ?> <u8 ?><u8 0x0b><u8 0x02> <u32 UniqueID> ..."
    )
    lines.append(
        "Shortlist filters for PlayerSL_FirstTeam_* also embed teamId 193616 "
        "(managed First Team)."
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
