#!/usr/bin/env python3
"""Club-side reverse hunt for favoured-club / preference links.

Hypothesis (from FMRTE Relations): players store favourite teams as
(clubId, affinity 0–100) edges. A club-centric index may also exist — if so,
scanning for managed clubId near foreign person UIDs is cheaper than a full
person walk.

Approach:
  1) Stream-decompress once.
  2) Collect every u32le == managed clubId (default: 920 Schalke).
  3) Classify ±64-byte neighborhoods: tag patterns, nearby person UIDs,
     affinity-like bytes, proximity to known FT roster UIDs / teamId.
  4) Baseline against nearby small clubIds to see if 920 is special.
"""

from __future__ import annotations

import json
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "favoured-club-reverse.txt"
EXTRACT = ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json"

CLUB_ID = 920  # Schalke Club Site UniqueID / DB id from FT extract
TEAM_ID = 193616
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000
WIN = 64  # bytes either side
MAX_DUMP_HITS = 40  # detailed hex dumps of strongest non-FT candidates
BASELINE_IDS = (910, 915, 918, 919, 921, 922, 925, 930, 1000, 2000)


def log(s: str = "") -> None:
    print(s, flush=True)


def load_ft_uids() -> set[int]:
    if not EXTRACT.exists():
        return set()
    d = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    return {int(p["uid"]) for p in d.get("players") or [] if p.get("uid")}


def stream_blocks(path: Path):
    with path.open("rb") as f:
        head = f.read(26)
        if head[2:6] != b"fmf." or head[25] != 3:
            raise SystemExit(f"unexpected container header: {path.name}")
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                yield block
        finally:
            reader.close()


def pack_u32(n: int) -> bytes:
    return struct.pack("<I", n & 0xFFFFFFFF)


def nearby_uids(window: bytes, abs_hit: int, win_start: int) -> list[tuple[int, int]]:
    """Return (abs_off, uid) for every aligned-ish u32 in UID range inside window."""
    out: list[tuple[int, int]] = []
    # Scan every offset — relation packs are not always 4-aligned to hit.
    for i in range(0, max(0, len(window) - 3)):
        v = struct.unpack_from("<I", window, i)[0]
        if UID_LO <= v <= UID_HI:
            out.append((win_start + i, v))
    return out


def classify_hit(
    data: bytes,
    local_off: int,
    abs_hit: int,
    ft_uids: set[int],
) -> dict:
    lo = max(0, local_off - WIN)
    hi = min(len(data), local_off + 4 + WIN)
    window = data[lo:hi]
    rel = local_off - lo  # clubId start inside window
    before = window[:rel]
    after = window[rel + 4 :]

    # Tag just before clubId (employment style: tag 08–0B then 02)
    pre2 = before[-2:] if len(before) >= 2 else b""
    pre1 = before[-1:] if before else b""
    tag_pair = None
    if len(pre2) == 2 and pre2[1] == 0x02 and pre2[0] in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F):
        tag_pair = f"{pre2[0]:02x}02"
    elif len(pre1) == 1 and pre1[0] == 0x02:
        tag_pair = "02"

    # Affinity candidates: u8 1–100 in ±8 around clubId, or u16le same range
    affinity_u8: list[tuple[str, int]] = []
    for name, blob, base in (("b", before, -len(before)), ("a", after, 4)):
        for i, b in enumerate(blob):
            if 1 <= b <= 100:
                dist = abs(base + i) if name == "b" else i + 4
                if dist <= 12:
                    affinity_u8.append((f"{name}{i:+d}", b))

    uids = nearby_uids(window, abs_hit, abs_hit - rel)
    uid_vals = [u for _, u in uids]
    ft_near = [u for u in uid_vals if u in ft_uids]
    foreign = [u for u in uid_vals if u not in ft_uids]

    # teamId near hit?
    team_near = pack_u32(TEAM_ID) in window

    # Score: foreign person UIDs + affinity + non-FT + not teamId squad context
    score = 0
    score += min(3, len(set(foreign))) * 3
    if affinity_u8:
        score += 2
    if tag_pair:
        score += 1
    if ft_near:
        score -= 2
    if team_near:
        score -= 3

    return {
        "abs": abs_hit,
        "score": score,
        "tag": tag_pair,
        "affinity": affinity_u8[:6],
        "ft_uids": sorted(set(ft_near))[:6],
        "foreign_uids": sorted(set(foreign))[:8],
        "team_near": team_near,
        "window": window,
        "rel": rel,
    }


def hexdump(window: bytes, mark: int, width: int = 16) -> list[str]:
    lines = []
    for i in range(0, len(window), width):
        chunk = window[i : i + width]
        hx = " ".join(f"{b:02x}" for b in chunk)
        mark_row = " " * (mark - i) * 3 if i <= mark < i + width else ""
        caret = ""
        if i <= mark < i + width:
            caret = " " * ((mark - i) * 3) + "^^"
        lines.append(f"  +{i:04x}  {hx}")
        if caret:
            lines.append(f"        {caret}  clubId")
    return lines


def scan(club_ids: list[int], ft_uids: set[int]) -> dict[int, dict]:
    needles = {cid: pack_u32(cid) for cid in club_ids}
    stats: dict[int, dict] = {
        cid: {
            "count": 0,
            "tag_hist": Counter(),
            "with_foreign_uid": 0,
            "with_ft_uid": 0,
            "with_affinity": 0,
            "with_team": 0,
            "score_hist": Counter(),
            "candidates": [],
        }
        for cid in club_ids
    }

    overlap = WIN + 8
    abs_base = 0
    carry = b""
    t0 = time.perf_counter()
    last_pct = -1

    # Rough size guess for progress (compressed * ~3)
    est = max(SAVE.stat().st_size * 3, 1)

    for block in stream_blocks(SAVE):
        data = carry + block
        searchable = len(data) - overlap if abs_base else len(data)
        # On first chunk search all; later leave overlap for next carry
        search_end = len(data) - (0 if abs_base == 0 and len(block) < 8 * 1024 * 1024 else overlap)
        if search_end < 0:
            search_end = 0

        for cid, needle in needles.items():
            start = 0
            # carry region already scanned except overlap zone from previous
            if abs_base and len(carry) >= 4:
                start = max(0, len(carry) - overlap - 3)
            while True:
                j = data.find(needle, start, max(start, search_end) + 3)
                if j < 0 or j >= search_end:
                    break
                abs_hit = abs_base - len(carry) + j
                hit = classify_hit(data, j, abs_hit, ft_uids)
                st = stats[cid]
                st["count"] += 1
                if hit["tag"]:
                    st["tag_hist"][hit["tag"]] += 1
                if hit["foreign_uids"]:
                    st["with_foreign_uid"] += 1
                if hit["ft_uids"]:
                    st["with_ft_uid"] += 1
                if hit["affinity"]:
                    st["with_affinity"] += 1
                if hit["team_near"]:
                    st["with_team"] += 1
                st["score_hist"][hit["score"]] += 1
                if cid == CLUB_ID and hit["score"] >= 3:
                    # Keep strongest windows (drop blob for list size later)
                    st["candidates"].append(hit)
                start = j + 1

        abs_base += len(block)
        carry = data[-overlap:]
        pct = int(min(99, abs_base * 100 / est))
        if pct != last_pct and pct % 5 == 0:
            last_pct = pct
            log(f"  … ~{pct}%  abs={abs_base:,}  clubHits={stats[CLUB_ID]['count']:,}")

    log(f"scan done in {time.perf_counter() - t0:.1f}s  abs={abs_base:,}")
    return stats


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ft_uids = load_ft_uids()
    log(f"save={SAVE.name}")
    log(f"clubId={CLUB_ID} teamId={TEAM_ID} ft_uids={len(ft_uids)}")

    club_ids = sorted(set([CLUB_ID, *BASELINE_IDS]))
    stats = scan(club_ids, ft_uids)

    lines: list[str] = []
    lines.append(f"# favoured-club reverse spike")
    lines.append(f"save={SAVE.name}")
    lines.append(f"clubId={CLUB_ID} teamId={TEAM_ID} ft_uids={len(ft_uids)}")
    lines.append("")
    lines.append("## hit counts (u32le == id)")
    for cid in club_ids:
        st = stats[cid]
        mark = " <-- managed" if cid == CLUB_ID else ""
        lines.append(
            f"  id={cid:>5}  hits={st['count']:>8}  "
            f"foreignUid={st['with_foreign_uid']:>6}  ftUid={st['with_ft_uid']:>5}  "
            f"affinity={st['with_affinity']:>6}  teamNear={st['with_team']:>5}{mark}"
        )

    st = stats[CLUB_ID]
    lines.append("")
    lines.append("## managed clubId tag histogram (byte before + 02)")
    for tag, n in st["tag_hist"].most_common(20):
        lines.append(f"  {tag}: {n}")

    lines.append("")
    lines.append("## managed clubId score histogram")
    for sc, n in sorted(st["score_hist"].items()):
        lines.append(f"  score={sc:+d}: {n}")

    # Deduplicate candidates by foreign uid set, keep highest score
    cands = st["candidates"]
    cands.sort(key=lambda h: (-h["score"], h["abs"]))
    best_by_uid: dict[int, dict] = {}
    for h in cands:
        for u in h["foreign_uids"]:
            prev = best_by_uid.get(u)
            if prev is None or h["score"] > prev["score"]:
                best_by_uid[u] = h

    lines.append("")
    lines.append(
        f"## top non-FT candidates (score>=3): "
        f"{len(cands)} windows / {len(best_by_uid)} distinct foreign UIDs"
    )
    shown = 0
    seen_abs: set[int] = set()
    for h in cands:
        if h["abs"] in seen_abs:
            continue
        seen_abs.add(h["abs"])
        lines.append(
            f"\n### abs={h['abs']} score={h['score']} tag={h['tag']} "
            f"team_near={h['team_near']}"
        )
        lines.append(f"  foreign_uids={h['foreign_uids']}")
        lines.append(f"  ft_uids={h['ft_uids']}")
        lines.append(f"  affinity={h['affinity']}")
        lines.extend(hexdump(h["window"], h["rel"]))
        shown += 1
        if shown >= MAX_DUMP_HITS:
            break

    # Aggregate: foreign UIDs that co-occur often with clubId (without teamId)
    uid_freq: Counter[int] = Counter()
    for h in cands:
        if h["team_near"]:
            continue
        for u in h["foreign_uids"]:
            uid_freq[u] += 1
    lines.append("")
    lines.append("## foreign UIDs co-occurring most (score>=3, no teamId near)")
    for u, n in uid_freq.most_common(30):
        lines.append(f"  uid={u}  windows={n}")

    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    log(f"wrote {OUT}")
    # Also print summary to stdout
    sys.stdout.buffer.write(
        ("\n".join(lines[:40]) + "\n… (full report in txt)\n").encode("utf-8", "replace")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
