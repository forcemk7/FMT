#!/usr/bin/env python3
"""Tighter follow-up: structural clubId edges, not loose neighborhood scores.

v1 showed raw u32==920 is as common as nearby ids — noise. Distinct signal was
FT uid proximity (employment). This spike:

  A) Dump every 0a02||0b02||0902||0802 + clubId hit (rare tags).
  B) Learn relative offsets of clubId vs known FT UIDs (positive templates).
  C) Search person-centric pattern: UID … 02 <clubId> <affinity:u8 1-100>
     and club-centric: 02 <clubId> <affinity> … UID  — require exact layouts.
  D) Resolve names for UIDs that match C repeatedly.
"""

from __future__ import annotations

import json
import struct
import time
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "favoured-club-structural.txt"
EXTRACT = ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json"

CLUB_ID = 920
CLUB = struct.pack("<I", CLUB_ID)
TAG_CLUB = b"\x02" + CLUB  # 02 98 03 00 00
UID_LO, UID_HI = 1_900_000_000, 2_100_000_000
# Slightly tighter: real/newgen UniqueIDs in this save cluster ~2.000e9–2.003e9
UID_CORE_LO, UID_CORE_HI = 2_000_000_000, 2_004_000_000


def log(s: str = "") -> None:
    print(s, flush=True)


def load_ft() -> tuple[set[int], dict[int, str]]:
    d = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
    names = {}
    for p in d.get("players") or []:
        if p.get("uid"):
            names[int(p["uid"])] = p.get("name") or f"uid:{p['uid']}"
    return set(names), names


def stream_blocks(path: Path):
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf." and head[25] == 3
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            reader.close()


def is_core_uid(v: int) -> bool:
    return UID_CORE_LO <= v <= UID_CORE_HI


def is_wide_uid(v: int) -> bool:
    return UID_LO <= v <= UID_HI


def read_lp_ascii(buf: bytes, off: int) -> str | None:
    if off + 4 > len(buf):
        return None
    n = struct.unpack_from("<I", buf, off)[0]
    if not (2 <= n <= 40) or off + 4 + n > len(buf):
        return None
    raw = buf[off + 4 : off + 4 + n]
    if not raw.isascii() or not all(32 <= b < 127 for b in raw):
        return None
    s = raw.decode("ascii")
    if s[0].isalpha() and any(c.isalpha() for c in s):
        return s
    return None


def resolve_names(uids: list[int], limit_each: int = 2) -> dict[int, str]:
    """Find lp32 names near 0002||uid markers (same trick as other spikes)."""
    want = {u: limit_each for u in uids}
    found: dict[int, str] = {}
    pats = {u: b"\x00\x02" + struct.pack("<I", u) for u in uids}
    abs_base = 0
    carry = b""
    for block in stream_blocks(SAVE):
        data = carry + block
        for uid, pat in list(pats.items()):
            if want.get(uid, 0) <= 0:
                continue
            start = 0
            while want.get(uid, 0) > 0:
                j = data.find(pat, start)
                if j < 0:
                    break
                # scan ahead for lp name
                for off in range(j + 6, min(len(data) - 8, j + 180)):
                    name = read_lp_ascii(data, off)
                    if name and (" " in name or len(name) >= 4):
                        cur = found.get(uid, "")
                        if " " in name or " " not in cur:
                            found[uid] = name
                        want[uid] -= 1
                        break
                start = j + 1
        abs_base += len(block)
        carry = data[-200:]
        if all(v <= 0 for v in want.values()):
            break
    return found


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ft_uids, ft_names = load_ft()
    log(f"save={SAVE.name} clubId={CLUB_ID} ft={len(ft_uids)}")

    # --- collect ---
    tag_hits: list[dict] = []  # rare employment-style tags before clubId
    offset_hist: Counter[int] = Counter()  # clubId_abs - uid_abs for FT uids in ±64
    # Structural patterns:
    #   P1: TAG_CLUB + affinity_u8 + (optional padding) + uid
    #   P2: uid + … + TAG_CLUB + affinity_u8
    p1_hits: list[dict] = []
    p2_hits: list[dict] = []
    p1_uid_freq: Counter[int] = Counter()
    p2_uid_freq: Counter[int] = Counter()

    overlap = 96
    abs_base = 0
    carry = b""
    t0 = time.perf_counter()
    est = max(SAVE.stat().st_size * 3, 1)
    last = -1
    total_tag_club = 0

    ft_pack = {u: struct.pack("<I", u) for u in ft_uids}

    for block in stream_blocks(SAVE):
        data = carry + block
        search_end = len(data) - (0 if abs_base == 0 else overlap)
        if search_end < 4:
            abs_base += len(block)
            carry = data[-overlap:]
            continue

        start0 = max(0, len(carry) - overlap - 3) if abs_base else 0

        # All TAG_CLUB occurrences
        start = start0
        while True:
            j = data.find(TAG_CLUB, start, search_end + 5)
            if j < 0 or j >= search_end:
                break
            abs_hit = abs_base - len(carry) + j
            total_tag_club += 1

            # rare tags: byte before TAG_CLUB in {08..0F}
            if j >= 1 and data[j - 1] in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F):
                lo = max(0, j - 32)
                hi = min(len(data), j + 48)
                win = data[lo:hi]
                tag_hits.append(
                    {
                        "abs": abs_hit,
                        "tag": f"{data[j - 1]:02x}02",
                        "win": win,
                        "rel": j - lo,
                    }
                )

            # P1: after clubId, next byte affinity 1..100, scan +1..+24 for core UID
            if j + 5 < len(data):
                aff = data[j + 5]
                if 1 <= aff <= 100:
                    for k in range(j + 6, min(len(data) - 3, j + 30)):
                        uid = struct.unpack_from("<I", data, k)[0]
                        if is_core_uid(uid) and uid not in ft_uids:
                            # require preceding 02 on uid (typed id) OR immediate
                            typed = k >= 1 and data[k - 1] == 0x02
                            rec = {
                                "abs": abs_hit,
                                "aff": aff,
                                "uid": uid,
                                "gap": k - (j + 5),
                                "typed": typed,
                            }
                            p1_hits.append(rec)
                            p1_uid_freq[uid] += 1
                            break

            # P2: look back ≤28 bytes for core UID, then TAG_CLUB + affinity
            if j + 5 < len(data):
                aff = data[j + 5]
                if 1 <= aff <= 100:
                    for k in range(max(0, j - 28), j - 3):
                        uid = struct.unpack_from("<I", data, k)[0]
                        if is_core_uid(uid) and uid not in ft_uids:
                            typed = k >= 1 and data[k - 1] == 0x02
                            rec = {
                                "abs": abs_hit,
                                "aff": aff,
                                "uid": uid,
                                "gap": j - (k + 4),
                                "typed": typed,
                            }
                            p2_hits.append(rec)
                            p2_uid_freq[uid] += 1
                            break

            # B) offsets vs FT UIDs in ±64
            lo = max(0, j - 64)
            hi = min(len(data), j + 4 + 64)
            chunk = data[lo:hi]
            for uid, pb in ft_pack.items():
                p = chunk.find(pb)
                while p >= 0:
                    uid_abs = abs_hit - (j - lo) + p
                    offset_hist[abs_hit - uid_abs] += 1
                    p = chunk.find(pb, p + 1)

            start = j + 1

        abs_base += len(block)
        carry = data[-overlap:]
        pct = int(min(99, abs_base * 100 / est))
        if pct != last and pct % 10 == 0:
            last = pct
            log(f"  … ~{pct}%  tag_club={total_tag_club}  p1={len(p1_hits)} p2={len(p2_hits)}")

    log(f"scan {time.perf_counter() - t0:.1f}s  bytes={abs_base:,}")

    # Prefer typed UIDs (02 <uid>) — stronger
    p1_typed = [h for h in p1_hits if h["typed"]]
    p2_typed = [h for h in p2_hits if h["typed"]]
    top_uids = [u for u, _ in (p1_uid_freq + p2_uid_freq).most_common(40)]
    # boost typed-only freq
    typed_freq: Counter[int] = Counter()
    for h in p1_typed + p2_typed:
        typed_freq[h["uid"]] += 1
    top_typed = [u for u, _ in typed_freq.most_common(25)]

    log(f"resolving names for {len(set(top_uids + top_typed))} candidate UIDs…")
    names = resolve_names(list(dict.fromkeys(top_typed + top_uids))[:50])

    lines: list[str] = []
    lines.append("# favoured-club structural spike")
    lines.append(f"save={SAVE.name}")
    lines.append(f"clubId={CLUB_ID}  TAG_CLUB hits={total_tag_club}")
    lines.append("")
    lines.append("## A) rare tag+clubId hits (0x08-0x0F before 02 <clubId>)")
    lines.append(f"count={len(tag_hits)}")
    tag_hist = Counter(h["tag"] for h in tag_hits)
    for t, n in tag_hist.most_common():
        lines.append(f"  {t}: {n}")
    for h in tag_hits[:20]:
        lines.append(f"\n### {h['tag']} abs={h['abs']}")
        rel = h["rel"]
        win = h["win"]
        for i in range(0, len(win), 16):
            chunk = win[i : i + 16]
            hx = " ".join(f"{b:02x}" for b in chunk)
            lines.append(f"  +{i:04x}  {hx}")
            if i <= rel < i + 16:
                lines.append("        " + " " * ((rel - i) * 3) + "^^ clubId")

    lines.append("")
    lines.append("## B) clubId−uid offsets for FT players (±64)")
    for off, n in offset_hist.most_common(25):
        lines.append(f"  delta={off:+d}: {n}")

    lines.append("")
    lines.append(
        f"## C) structural P1 (02 clubId aff … uid) hits={len(p1_hits)} typed={len(p1_typed)}"
    )
    gap_hist = Counter(h["gap"] for h in p1_typed)
    aff_hist = Counter(h["aff"] for h in p1_typed)
    lines.append(f"  typed gap hist: {dict(gap_hist.most_common(10))}")
    lines.append(f"  typed aff hist: {dict(aff_hist.most_common(15))}")

    lines.append("")
    lines.append(
        f"## C) structural P2 (uid … 02 clubId aff) hits={len(p2_hits)} typed={len(p2_typed)}"
    )
    gap_hist2 = Counter(h["gap"] for h in p2_typed)
    aff_hist2 = Counter(h["aff"] for h in p2_typed)
    lines.append(f"  typed gap hist: {dict(gap_hist2.most_common(10))}")
    lines.append(f"  typed aff hist: {dict(aff_hist2.most_common(15))}")

    lines.append("")
    lines.append("## D) top typed UIDs (likely relation endpoints)")
    for u, n in typed_freq.most_common(25):
        nm = names.get(u, ft_names.get(u, "?"))
        lines.append(f"  uid={u}  n={n}  name={nm}")

    lines.append("")
    lines.append("## D) top untyped UIDs (weaker)")
    for u, n in (p1_uid_freq + p2_uid_freq).most_common(20):
        if u in typed_freq:
            continue
        nm = names.get(u, "?")
        lines.append(f"  uid={u}  n={n}  name={nm}")

    # Sample a few typed hit windows for inspection
    lines.append("")
    lines.append("## sample typed P1/P2 windows (re-scan top 5 uids)")
    # quick re-find one window per top uid via second pass skipped — print hit meta only
    for h in (p1_typed + p2_typed)[:15]:
        nm = names.get(h["uid"], "?")
        lines.append(
            f"  abs={h['abs']} uid={h['uid']} aff={h['aff']} gap={h['gap']} name={nm}"
        )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    # stdout summary
    for line in lines[:35]:
        log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
