#!/usr/bin/env python3
"""
Fast First Team extract for ANY career .fm save.

Layout insight (FM24 career):
  - Squad job lists appear early (~tens of MB out).
  - Double-UID + 69-byte attr strips sit mid-file (~100–400MB).
  - jobId → UniqueID employment tags sit near the END of the stream.
    → resolve employment with mmap.rfind (search from the end).

Pipeline:
  1) Full stream-decompress to temp (no world squad/staff/stadium walk)
  2) mmap: this club FT/II/U19 only; rfind employment, names, attr doubles
  3) stderr PROGRESS JSON lines; stdout final JSON
"""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import sys
import tempfile
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import zstandard as zstd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ft_squad_discovery import (  # noqa: E402
    LIST_WINDOWS,
    ft_join_progress_fields,
    resolve_ft_squad,
    select_managed_ft_jobs,
)
from ii_squad_discovery import resolve_ii_squad  # noqa: E402
from u19_squad_discovery import (  # noqa: E402
    NAME_BAND_HI,
    NAME_BAND_LO,
    parse_list_near_name,
    read_lp32,
    resolve_u19_squad,
)

_emt_spec = importlib.util.spec_from_file_location(
    "extract_managed_team", ROOT / "scripts" / "extract-managed-team.py"
)
_emt = importlib.util.module_from_spec(_emt_spec)
assert _emt_spec and _emt_spec.loader
_emt_spec.loader.exec_module(_emt)
EARLY_SCAN = _emt.EARLY_SCAN
IDENTITY_DEADLINE = _emt.IDENTITY_DEADLINE
discover_managed_club = _emt.discover_managed_club
try_discover_managed_club = _emt.try_discover_managed_club
pick_game_date_near_identity = _emt.pick_game_date_near_identity


def refuse_live_fm_games_save(path: Path) -> None:
    """Copy Career Saves into data/saves. Live SI games/*.fm locks FM autosave."""
    parts = [p.lower() for p in Path(path).resolve().parts]
    if (
        "sports interactive" in parts
        and "games" in parts
        and Path(path).suffix.lower() == ".fm"
    ):
        raise SystemExit(
            "Refusing Sports Interactive/games/*.fm — copy the Career Save into data/saves"
        )

CHUNK = 8 * 1024 * 1024
LIST_SENTINEL = bytes.fromhex("7f02000000ffffffff")
LIST_SENTINEL_LOOSE = bytes.fromhex("7f02000000")  # without requiring ff×4
TAG_010302 = bytes.fromhex("010302")  # common after 7f02… on native FM26
ZSTD_MAGIC = bytes.fromhex("28b52ffd")
# Early-career native jobs/tids sit far below continued-save FM24 ranges.
JOB_LO, JOB_HI = 100, 50_000_000
TID_LO, TID_HI = 1, 50_000_000
# Continue-career UniqueID magnitude — heuristic only. Native / other-DB
# people sit outside this band; listed jobs are kept (T085), not dropped.
UID_LO, UID_HI = 1_500_000_000, 2_200_000_000
# Continue-career REAL vs NEWGEN split when uid is inside UID_LO..UID_HI.
# Not a drop filter; outside the band kind is UNKNOWN.
NEWGEN_UID_FLOOR = 2_002_000_000
STAFF_MARK = bytes.fromhex("011802")
# Search window before person double for CA/attr history cards.
ATTR_LOOKBACK = 20_000
# Locked geometry: live CA cards sit ~1.5–12KB before the person double.
# Prefer that band so far historical strips (e.g. ~19KB) cannot win on density.
ATTR_CARD_GAP_MIN = 1_200
ATTR_CARD_GAP_MAX = 14_000
OVERLAP = max(len(LIST_SENTINEL) + 4 + 2 + 4 * 60, 64)
EMPLOYMENT_TAIL = 128 * 1024 * 1024
PERSON_HEAD = 512 * 1024 * 1024
# Gap/loaned players often lack `\x00\x02`+uid inline names. Fallback reads
# first/second name IDs from the person stub MARK before uid||uid (T008).
PERSON_NAME_MARK = bytes.fromhex("01006c07")
PERSON_NAME_FIRST_OFF = 25
PERSON_NAME_SECOND_OFF = 30
# Mid-file first/surname/third name tables collide on the same id space;
# restrict hits to this band then take 1st hit = first name, 2nd = surname.
NAME_TABLE_LO = 100 * 1024 * 1024
NAME_TABLE_HI = 160 * 1024 * 1024
SQUAD_COUNT_LO, SQUAD_COUNT_HI = 11, 55
SQUAD_JOBS_MIN = 11
# Dynamics (T002): cap tail after FT job list; social lists after this motif.
DYNAMICS_SOCIAL_MOTIF = bytes.fromhex("b51ae70701f7020000")
DYNAMICS_SOCIAL_LABELS = ("core", "secondaryA", "secondaryB", "other")
DYNAMICS_SOCIAL_LIST_MAX = 80

# Lazy caches keyed by id(buf): nameId → mid-file strings in offset order
_NAME_ID_HITS: dict[int, dict[int, list[str]]] = {}


def name_id_hits(buf, nid: int) -> list[str]:
    """Mid-file name-table strings for `nid` in offset order (cached)."""
    if nid <= 0 or nid >= 2_000_000:
        return []
    buf_key = id(buf)
    cache = _NAME_ID_HITS.get(buf_key)
    if cache is None:
        cache = {}
        _NAME_ID_HITS[buf_key] = cache
    cached = cache.get(nid)
    if cached is not None:
        return cached
    hi = min(NAME_TABLE_HI, len(buf))
    lo = min(NAME_TABLE_LO, hi)
    pat = struct.pack("<I", nid)
    hits: list[str] = []
    j = buf.find(pat, lo, hi)
    while j >= 0 and len(hits) < 8:
        if j + 8 <= len(buf):
            ln = struct.unpack_from("<I", buf, j + 4)[0]
            if 1 <= ln <= 48 and j + 8 + ln <= len(buf):
                raw = bytes(buf[j + 8 : j + 8 + ln])
                if raw and raw[:1].isalpha() and all(
                    b >= 0x20 or b == 0x09 for b in raw
                ):
                    try:
                        hits.append(raw.decode("utf-8"))
                    except UnicodeDecodeError:
                        pass
        j = buf.find(pat, j + 1, hi)
    cache[nid] = hits
    return hits


def lookup_name_id(buf, nid: int, *, surname: bool) -> str | None:
    """Resolve a name id. First-name ids → hits[0]; surname ids → hits[1] else [0]."""
    hits = name_id_hits(buf, nid)
    if not hits:
        return None
    if surname:
        return hits[1] if len(hits) > 1 else hits[0]
    return hits[0]


def resolve_name_from_mark(
    buf, uid: int, doubles: list[int] | None = None
) -> str | None:
    """Name-id join: closest *valid* PERSON_NAME_MARK before uid||uid → +25/+30 ids.

    Skip marks whose first/second ids are out of range (noise closer to the
    double can sit on top of the real Igor Kasprzak-style mark).
    """
    sites = list(doubles or [])
    if not sites:
        pat = struct.pack("<II", uid, uid)
        end = min(len(buf), PERSON_HEAD)
        j = buf.find(pat, 0, end)
        while j >= 0 and len(sites) < 8:
            sites.append(j)
            j = buf.find(pat, j + 1, end)
    marks: list[int] = []
    for dab in sites:
        lo = max(0, dab - 2048)
        region = bytes(buf[lo:dab])
        start = 0
        while True:
            rel = region.find(PERSON_NAME_MARK, start)
            if rel < 0:
                break
            marks.append(lo + rel)
            start = rel + 1
    # Closest to the double first.
    for mark in sorted(marks, reverse=True):
        if mark + PERSON_NAME_SECOND_OFF + 4 > len(buf):
            continue
        fid = struct.unpack_from("<I", buf, mark + PERSON_NAME_FIRST_OFF)[0]
        sid = struct.unpack_from("<I", buf, mark + PERSON_NAME_SECOND_OFF)[0]
        if fid == 0 or sid == 0 or fid > 2_000_000 or sid > 2_000_000:
            continue
        first = lookup_name_id(buf, fid, surname=False)
        second = lookup_name_id(buf, sid, surname=True)
        if first and second:
            return f"{first} {second}"
        if second or first:
            return second or first
    return None

MENTAL = [
    "aggression",
    "anticipation",
    "bravery",
    "vision",
    "decisions",
    "determination",
    "flair",
    "leadership",
    "offTheBall",
    "positioning",
    "teamwork",
    "workRate",
    "composure",
    "concentration",
]
PHYS = [
    "acceleration",
    "agility",
    "balance",
    "pace",
    "stamina",
    "strength",
    "jumpingReach",
    "naturalFitness",
]
TECH = [
    "crossing",
    "dribbling",
    "finishing",
    "heading",
    "longShots",
    "longThrows",
    "marking",
    "passing",
    "penaltyTaking",
    "freeKickTaking",
    "tackling",
    "technique",
    "firstTouch",
    "corners",
]
GK_CORE = [
    "aerialReach",
    "commandOfArea",
    "communication",
    "eccentricity",
    "handling",
    "kicking",
    "reflexes",
    "rushingOutTendency",
    "punchingTendency",
    "throwing",
    "oneOnOnes",
]

# Locked save pack near person double (raw u8 1–20).
# Byte 0 = Adaptability (SI Hidden); bytes 1–7 feed Personality (minus Det/Lea).
PERSONALITY_PACK_ORDER = [
    "adaptability",
    "ambition",
    "loyalty",
    "pressure",
    "professionalism",
    "sportsmanship",
    "temperament",
    "controversy",
]
PERSONALITY_FROM_PACK = [
    "ambition",
    "loyalty",
    "pressure",
    "professionalism",
    "sportsmanship",
    "temperament",
    "controversy",
]
MENTAL_HA_TRAIL = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
MENTAL_HA_LOOKBACK = 2048
MENTAL_HA_LOOKAHEAD = 4096
# Locked CAPA core (see data/fixtures/capa-layout-locked.json).
CAPA_LOOKBACK = 48_000
CAPA_PTR_HI = 0x77


def progress(t0: float, **fields) -> None:
    payload = {"elapsedMs": int((time.perf_counter() - t0) * 1000), **fields}
    print(f"PROGRESS {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr, flush=True)


def fail(t0: float, message: str, *, code: int = 1, **diagnostics) -> int:
    """Always emit structured failure JSON on stdout so the UI never sees 'no JSON'."""
    progress(t0, phase="error", message=message, pct=100, **diagnostics)
    print(
        json.dumps(
            {
                "error": message,
                "diagnostics": diagnostics,
                "elapsedMs": int((time.perf_counter() - t0) * 1000),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return code


def probe_container(path: Path) -> dict:
    size = path.stat().st_size
    with path.open("rb") as f:
        head = f.read(256)
    magic4 = head[:4]
    zstd_offsets = []
    start = 0
    while True:
        j = head.find(ZSTD_MAGIC, start)
        if j < 0:
            break
        zstd_offsets.append(j)
        start = j + 1
    trials = []
    for off in sorted({26, *zstd_offsets, 0, 16, 24, 28, 32}):
        if off >= min(len(head), size):
            continue
        try:
            with path.open("rb") as f:
                f.seek(off)
                reader = zstd.ZstdDecompressor().stream_reader(f)
                try:
                    chunk = reader.read(8 * 1024)
                finally:
                    reader.close()
            if chunk:
                trials.append({"offset": off, "ok": True, "firstOut": len(chunk)})
            else:
                trials.append({"offset": off, "ok": False, "error": "empty"})
        except Exception as e:  # noqa: BLE001
            trials.append({"offset": off, "ok": False, "error": type(e).__name__})
    best = next((t["offset"] for t in trials if t.get("ok")), None)
    inferred = (
        "fm24_continue_style_zstd_at_26"
        if best == 26
        else (f"zstd_at_{best}" if best is not None else "unsupported_or_unknown")
    )
    return {
        "saveBytes": size,
        "magicHex": magic4.hex(),
        "magicAscii": "".join(chr(b) if 32 <= b < 127 else "." for b in magic4),
        "headerHex32": head[:32].hex(),
        "byte25": head[25] if len(head) > 25 else None,
        "zstdMagicOffsetsInHead": zstd_offsets,
        "zstdOffset": best,
        "zstdTrials": trials,
        "inferredLayout": inferred,
        "layout": classify_squad_layout(inferred_layout=inferred),
    }


def parse_cli_flags() -> tuple[bool, str | None]:
    """Return (names_only, parent_short_override)."""
    names_only = "--names-only" in sys.argv
    parent_short: str | None = None
    if "--parent-short" in sys.argv:
        idx = sys.argv.index("--parent-short")
        if idx + 1 < len(sys.argv):
            parent_short = sys.argv[idx + 1]
    return names_only, parent_short


def resolve_save() -> tuple[Path, bool]:
    """Return (path, is_predecompressed_bin)."""
    skip_next = False
    args: list[str] = []
    for a in sys.argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if a == "--names-only":
            continue
        if a == "--parent-short":
            skip_next = True
            continue
        args.append(a)
    if args:
        p = Path(args[0])
        if not p.is_file():
            raise FileNotFoundError(f"not found: {p}")
        refuse_live_fm_games_save(p)
        return p, p.suffix.lower() == ".bin"
    saves = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not saves:
        raise FileNotFoundError("no .fm in data/saves")
    refuse_live_fm_games_save(saves[0])
    return saves[0], False


def disp(b: bytes) -> list[int]:
    return [round(x / 5) for x in b]


def named(keys: list[str], vals: list[int]) -> dict[str, int]:
    return {k: v for k, v in zip(keys, vals)}


def read_lp(buf, off: int):
    if off + 4 > len(buf):
        return None
    ln = struct.unpack_from("<I", buf, off)[0]
    if not (1 <= ln <= 48) or off + 4 + ln > len(buf):
        return None
    raw = buf[off + 4 : off + 4 + ln]
    if isinstance(raw, memoryview):
        raw = raw.tobytes()
    elif not isinstance(raw, (bytes, bytearray)):
        raw = bytes(raw)
    if any(b < 0x20 and b not in (0x09,) for b in raw):
        return None
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        s = raw.decode("latin-1", errors="replace")
    if not any(c.isalpha() for c in s):
        return None
    return s, off + 4 + ln


def parse_name_at(buf, uid_off: int) -> str | None:
    off = uid_off + 4
    if (
        off + 5 <= len(buf)
        and buf[off] == 0x02
        and buf[off + 1 : off + 5] == b"\xff\xff\xff\xff"
    ):
        off += 5
    first = read_lp(buf, off)
    if not first:
        return None
    s1, n1 = first
    last = read_lp(buf, n1)
    name = f"{s1} {last[0]}" if last and last[0][:1].isupper() else s1
    return name if name[:1].isupper() else None


def is_attrish(buf: bytes, i: int) -> bool:
    if i + 69 > len(buf):
        return False
    if buf[i + 34] or buf[i + 35] or buf[i + 43] != 0x01:
        return False
    return sum(1 for x in buf[i : i + 22] if 25 <= x <= 105) >= 12


def _collect_attr_cards(window: bytes) -> list[tuple[int, bytes]]:
    """Return (offset_in_window, 69-byte record) for attrish cards."""
    cards: list[tuple[int, bytes]] = []
    start = 0
    while True:
        z = window.find(b"\x00\x00", start)
        if z < 0 or z + 35 > len(window):
            break
        i = z - 34
        if i >= 0 and z == i + 34 and is_attrish(window, i):
            cards.append((i, window[i : i + 69]))
            start = z + 69
        else:
            start = z + 1
    return cards


def score_attr_window(
    window: bytes,
    tip: dict | None = None,
) -> tuple[tuple[int, int, int, int], int, bytes] | None:
    """
    Pick the best CA/attr card in the lookback window before a person double.

    Returns (quality, offset_in_window, record) where quality is ordered for max():
      With a history tip (continuity path):
        (continuity, in_band, -gap, b23, offset)
      Without tip (legacy densest-strip path):
        (0, in_band, b23, offset, strip_len)

    Prefer cards whose gap-to-double sits in ATTR_CARD_GAP_* (locked geometry).
    When a history tip is provided, keep cards with low L1 to that tip (rejects
    foreign Det=20 decoys), then pick the **nearest** card (smallest gap). Max-b23
    is a poor “newest” proxy — it favoured stale duplicates (e.g. Seimen b23=253
    Cmp=14 over nearer Cmp=13 Progress Report tip).
    """
    cards = _collect_attr_cards(window)
    if not cards:
        return None

    win_len = len(window)

    def gap_before_double(off: int) -> int:
        # Distance from card start to the person double (= end of window).
        return win_len - off

    near = [
        (off, rec)
        for off, rec in cards
        if ATTR_CARD_GAP_MIN <= gap_before_double(off) <= ATTR_CARD_GAP_MAX
    ]
    pool = near if near else cards

    # Continuity pool: same contiguous CA strip as Progress Report history tip.
    # L1>80 almost always means a foreign / wrong-person card, not a real delta.
    # Tech-wiped cards may still qualify via mental+phys continuity (inherit tip tech).
    cont_pool: list[tuple[int, bytes]] = []
    if tip is not None:
        for off, rec in pool:
            point = _ca_point_from_rec(rec, gap=gap_before_double(off), tip=tip)
            if point is None:
                continue
            if _history_l1(tip, point) <= 80:
                cont_pool.append((off, rec))

    if cont_pool:
        # Newest = nearest to person double. Tie-break: higher b23, then offset.
        abs_in_win, rec = min(
            cont_pool,
            key=lambda t: (
                gap_before_double(t[0]),
                -t[1][23],
                -t[0],
            ),
        )
        gap = gap_before_double(abs_in_win)
        in_band = 1 if ATTR_CARD_GAP_MIN <= gap <= ATTR_CARD_GAP_MAX else 0
        quality = (1, in_band, -gap, rec[23], abs_in_win)
        return quality, abs_in_win, rec

    by_u16: dict[int, list[tuple[int, bytes]]] = defaultdict(list)
    for off, rec in pool:
        u16 = struct.unpack_from("<H", rec, 36)[0]
        by_u16[u16].append((off, rec))

    best_u16 = max(
        by_u16.keys(),
        key=lambda u: (
            max(r[1][23] for r in by_u16[u]),
            max(r[0] for r in by_u16[u]),
            len(by_u16[u]),
        ),
    )
    strip = by_u16[best_u16]
    strip.sort(key=lambda t: (t[1][23], t[0]))
    abs_in_win, rec = strip[-1]
    gap = gap_before_double(abs_in_win)
    in_band = 1 if ATTR_CARD_GAP_MIN <= gap <= ATTR_CARD_GAP_MAX else 0
    quality = (0, in_band, rec[23], abs_in_win, len(strip))
    return quality, abs_in_win, rec


def _attr_signature(decoded: dict) -> str:
    """Stable signature of CA nests (ignore meta)."""
    parts = []
    for nest in ("mental", "physical", "technical", "goalkeeping"):
        block = decoded.get(nest)
        if not isinstance(block, dict):
            continue
        for key in sorted(block.keys()):
            parts.append(f"{nest}.{key}={block[key]}")
    return "|".join(parts)


def _history_vec(
    point: dict,
    nests: tuple[str, ...] = ("mental", "physical", "technical", "goalkeeping"),
) -> dict[str, int]:
    out: dict[str, int] = {}
    for nest in nests:
        block = point.get(nest)
        if not isinstance(block, dict):
            continue
        for key, val in block.items():
            if isinstance(val, int):
                out[f"{nest}.{key}"] = val
    return out


def _history_l1(
    a: dict,
    b: dict,
    nests: tuple[str, ...] = ("mental", "physical", "technical", "goalkeeping"),
) -> int:
    va, vb = _history_vec(a, nests), _history_vec(b, nests)
    keys = set(va) | set(vb)
    return sum(abs(va.get(k, 0) - vb.get(k, 0)) for k in keys)


def _mental_phys_l1(a: dict, b: dict) -> int:
    """L1 on mental+physical only — ignores wiped/foreign technical tails."""
    return _history_l1(a, b, nests=("mental", "physical"))


def _technical_wiped(point: dict) -> bool:
    """False-positive outfield cards often decode with Technique 0 (FT 0 or 1)."""
    if point.get("kind") == "gk":
        return False
    tech = point.get("technical")
    if not isinstance(tech, dict) or not tech:
        return False
    return tech.get("technique") == 0


def _inherit_tech_from_tip(point: dict, tip: dict) -> dict:
    """Keep live mental/phys; reuse tip technical/gk when the live tech tail is junk."""
    out = dict(point)
    tip_tech = tip.get("technical")
    if isinstance(tip_tech, dict) and tip_tech:
        out["technical"] = dict(tip_tech)
    else:
        # Tip was a first wiped Progress Report (tech stripped). Drop junk tail.
        out.pop("technical", None)
    tip_gk = tip.get("goalkeeping")
    if isinstance(tip_gk, dict) and tip_gk and not out.get("goalkeeping"):
        out["goalkeeping"] = dict(tip_gk)
    elif not (isinstance(tip_gk, dict) and tip_gk):
        if not (isinstance(tip_tech, dict) and tip_tech):
            out.pop("goalkeeping", None)
    return out


def _accept_first_wiped_progress_tip(point: dict) -> dict | None:
    """
    Gilson-class first Progress Report tip: mental/phys are live, technical tail
    still Technique=0 junk, and there is no prior tip to inherit tech from.

    Require snapshotU16>0 (Progress Report class) and in-band gap when known so
    hist=0 foreign decoys (typically u16=0, e.g. Det20/Lea3) stay rejected.
    Strip technical so Technique=0 is not treated as a real CA value.
    """
    if int(point.get("snapshotU16") or 0) <= 0:
        return None
    gap = point.get("gap")
    if gap is None:
        return None
    g = int(gap)
    if not (ATTR_CARD_GAP_MIN <= g <= ATTR_CARD_GAP_MAX):
        return None
    mental = point.get("mental")
    if not isinstance(mental, dict):
        return None
    det, lea = mental.get("determination"), mental.get("leadership")
    if not isinstance(det, int) or not isinstance(lea, int):
        return None
    if not (1 <= det <= 20 and 0 <= lea <= 20):
        return None
    out = dict(point)
    out.pop("technical", None)
    out.pop("goalkeeping", None)
    return out


def _recover_wiped_against_tip(point: dict, tip: dict | None) -> dict | None:
    """
    Recent CA commits can update mental/phys while the technical tail is still
    foreign garbage (Technique 0). Sipho 01.12.2039: nearer Det=15/Lea=4 card
    matched FM exactly but was dropped as wiped. Recover when mental+phys stay
    continuous with the tip and inherit tip technical.

    First tip (no prior history): still keep mental/phys when the card looks like
    a Progress Report tip (T014 Gilson Det14/Lea16) — see
    `_accept_first_wiped_progress_tip`.
    """
    if not _technical_wiped(point):
        return point
    if tip is None:
        return _accept_first_wiped_progress_tip(point)
    if _mental_phys_l1(tip, point) > 80:
        return None
    return _inherit_tech_from_tip(point, tip)


def _filter_ca_history(points: list[dict]) -> list[dict]:
    """
    Drop unrecovered wiped technical cards and keep only the newest contiguous strip.

    Lookback windows can contain foreign attr cards; a large gap drop or L1
    jump marks a strip boundary. Progress-report-like history is the suffix
    nearest the person double.
    """
    cleaned = [p for p in points if not _technical_wiped(p)]
    if len(cleaned) <= 1:
        return cleaned

    # gaps decrease oldest→newest; large drop ⇒ skipped foreign region
    max_gap_drop = 2_000
    max_l1 = 80
    start = 0
    for i in range(1, len(cleaned)):
        prev, cur = cleaned[i - 1], cleaned[i]
        gap_drop = int(prev.get("gap") or 0) - int(cur.get("gap") or 0)
        if gap_drop < 0 or gap_drop > max_gap_drop or _history_l1(prev, cur) > max_l1:
            start = i
    out = cleaned[start:]
    for i, p in enumerate(out):
        p["index"] = i
    return out


def _ca_point_from_rec(
    rec: bytes,
    *,
    gap: int | None = None,
    tip: dict | None = None,
) -> dict | None:
    """Decode one CA card into a history point, or None if wiped/false-positive."""
    decoded = decode_attrs(rec)
    meta = decoded.pop("_cardMeta", {}) or {}
    kind = decoded.pop("_kind", None)
    point = {
        "index": 0,
        "date": None,
        "gap": gap,
        "snapshotU16": int(meta.get("snapshotU16") or 0),
        "b23": int(meta.get("b23") or 0),
        "kind": kind,
    }
    for nest in ("mental", "physical", "technical", "goalkeeping"):
        if nest in decoded:
            point[nest] = decoded[nest]
    if _technical_wiped(point):
        return _recover_wiped_against_tip(point, tip)
    return point


def ensure_live_ca_on_history(
    history: list[dict] | None,
    live_rec: bytes | None,
    *,
    gap: int | None = None,
) -> tuple[list[dict] | None, str]:
    """
    Append the preferred live CA card when it differs from the last change-point.

    History change-points skip snapshotU16==0 and may drop the live card in strip
    filters, so Progress Report "now" can lag the chart endpoint without this.
    Gap is nudged when needed so client/server contiguous-strip filters keep the
    prior series instead of restarting on the live tip.

    Returns (history, status) where status is:
      - "same": live matches tip (already current)
      - "appended": live appended as new tip
      - "rejected": live L1 too far / wiped — caller must not trust it for attrs
      - "empty": no live card
    """
    if live_rec is None:
        return history, "empty"
    points = list(history or [])
    tip = points[-1] if points else None
    live = _ca_point_from_rec(live_rec, gap=gap, tip=tip)
    if live is None:
        return history, "rejected"

    if points:
        last = points[-1]
        if _attr_signature(last) == _attr_signature(live):
            return points, "same"
        # Suspicious jumps are more often wrong cards than real CA deltas.
        if _history_l1(last, live) > 80:
            # Exception: a single tip that disagrees hard with a clean live card
            # is usually foreign lookback residue (Mayele: tip Det=7 vs live
            # Det=18 Driven). Prefer live as the only history point.
            if len(points) == 1 and not _technical_wiped(live):
                live = dict(live)
                live["index"] = 0
                return [live], "replaced_singleton"
            return points, "rejected"
        last_gap = int(last.get("gap") or 0)
        live_gap = int(gap) if gap is not None else last_gap
        if live_gap > last_gap or last_gap - live_gap > 2_000:
            live_gap = max(0, last_gap - 1)
        live["gap"] = live_gap

    live["index"] = len(points)
    points.append(live)
    return points, "appended"


def build_ca_history(window: bytes) -> list[dict]:
    """
    Collapse CA cards in a person lookback into change-points, oldest → newest.

    Ordering uses gap-to-double (larger gap = older). Calendar `date` is null until
    snapshotU16/b23 are mapped to the in-game calendar. Duplicate consecutive
    attribute vectors are dropped. Foreign/wiped cards are filtered so the
    retained suffix is the contiguous strip nearest the person double.
    Tech-wiped cards that stay continuous on mental+phys inherit prior technical
    so recent Det/Lea commits are not dropped (Sipho Fairly Professional→Resolute).
    """
    cards = _collect_attr_cards(window)
    if not cards:
        return []
    win_len = len(window)
    # farthest (oldest) first
    cards.sort(key=lambda t: t[0])
    points: list[dict] = []
    prev_sig: str | None = None
    prev_kept: dict | None = None
    for off, rec in cards:
        decoded = decode_attrs(rec)
        meta = decoded.pop("_cardMeta", {}) or {}
        kind = decoded.pop("_kind", None)
        u16 = int(meta.get("snapshotU16") or 0)
        if u16 == 0:
            continue
        point = {
            "index": len(points),
            "date": None,
            "gap": win_len - off,
            "snapshotU16": u16,
            "b23": int(meta.get("b23") or 0),
            "kind": kind,
        }
        for nest in ("mental", "physical", "technical", "goalkeeping"):
            if nest in decoded:
                point[nest] = decoded[nest]
        if _technical_wiped(point):
            recovered = _recover_wiped_against_tip(point, prev_kept)
            if recovered is None:
                continue
            point = recovered
        sig = _attr_signature(point)
        if sig == prev_sig:
            continue
        prev_sig = sig
        point["index"] = len(points)
        points.append(point)
        prev_kept = point
    return _filter_ca_history(points)


def decode_attrs(rec: bytes) -> dict:
    """CA strip → technical / goalkeeping / mental / physical (no general; no FT/Pas under GK)."""
    mental = named(MENTAL, disp(rec[0:14]))
    physical = named(PHYS, disp(rec[14:22]))
    mid = disp(rec[44:55])
    tail = disp(rec[55:69])
    looks_gk = mental["offTheBall"] <= 3 and mid[0] >= 8 and mid[6] >= 8
    kind = "gk" if looks_gk else "outfield"
    out: dict = {
        "mental": mental,
        "physical": physical,
        "_kind": kind,
        "_cardMeta": {
            "snapshotU16": struct.unpack_from("<H", rec, 36)[0],
            "b23": rec[23],
            "seal": [rec[22], rec[24]],
        },
    }
    if looks_gk:
        out["goalkeeping"] = named(GK_CORE, mid)
        # firstTouch / passing live in the tech/set tail (single source; not under GK_CORE).
        # Locked vs Contreras (FT=10 Pen=4 Tec=13) + Seimen (FT=Pen=Tec=11, FK=3):
        #   Pas=tail[7], Pen=tail[8], FK=tail[9], Tec=tail[11], FT=tail[12]
        tech: dict = {}
        if len(tail) >= 9:
            tech["passing"] = tail[7]
            tech["penaltyTaking"] = tail[8]
        if len(tail) > 9:
            tech["freeKickTaking"] = tail[9]
        if len(tail) > 11:
            tech["technique"] = tail[11]
        if len(tail) > 12:
            tech["firstTouch"] = tail[12]
        out["technical"] = tech
    else:
        out["technical"] = named(TECH, tail)
    return out


def empty_general() -> dict:
    return {
        "adaptability": None,
        "ambition": None,
        "consistency": None,
        "controversy": None,
        "dirtiness": None,
        "importantMatches": None,
        "injuryProneness": None,
        "loyalty": None,
        "pressure": None,
        "professionalism": None,
        "sportsmanship": None,
        "temperament": None,
        "versatility": None,
    }


# --- Dates (days since 1900-01-01) ---
DATE_EPOCH = date(1900, 1, 1)
# Prefaced calendar entries: c7 08 00 00 00 | days_u32 | twin_u32 | twin_u32
GAME_DATE_PRELUDE = bytes.fromhex("c708000000")
GAME_DATE_EARLY = 24 * 1024 * 1024


def days_y1900_to_iso(days: int) -> str | None:
    try:
        dt = DATE_EPOCH + timedelta(days=int(days))
    except Exception:
        return None
    if not (1900 <= dt.year <= 2100):
        return None
    return dt.isoformat()


def parse_save_game_date_hint(path: Path | None) -> date | None:
    """Filename 'In-game date DD.MM.YYYY' — unused for extract (T064: blob only)."""
    if path is None:
        return None
    import re

    m = re.search(
        r"(?:In-game date\s+)?(\d{2})\.(\d{2})\.(\d{4})",
        path.name,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def discover_game_date(
    buf: bytes | mmap.mmap,
    limit: int = GAME_DATE_EARLY,
    hint: date | None = None,
) -> dict | None:
    """
    Locate in-game date from early decompressed bytes.

    Filename dates are ignored (stale / T056 strips them). Prefer:
      1) latest today_ptr (not the dense July pre-season cluster)
      2) walk consecutive calendar prelude days after that ptr (run end)
      3) start of densest calendar run
    `hint` is accepted but never used.
    """
    _ = hint  # T064: filename dates are not a source
    hi = min(len(buf), limit)
    days_hits: set[int] = set()
    first_abs: dict[int, int] = {}
    start = 0
    while True:
        j = buf.find(GAME_DATE_PRELUDE, start, hi)
        if j < 0:
            break
        off = j + len(GAME_DATE_PRELUDE)
        if off + 12 > hi:
            break
        days = struct.unpack_from("<I", buf, off)[0]
        if 40_000 <= days <= 60_000:
            a = struct.unpack_from("<I", buf, off + 4)[0]
            b = struct.unpack_from("<I", buf, off + 8)[0]
            if a == b and a > 255:
                iso = days_y1900_to_iso(days)
                if iso and 2020 <= int(iso[:4]) <= 2050:
                    days_hits.add(days)
                    first_abs.setdefault(days, j)
        start = j + 1

    if not days_hits:
        return None

    ordered = sorted(days_hits)
    runs: list[tuple[int, int]] = []
    run_start = ordered[0]
    run_len = 1
    for i in range(1, len(ordered)):
        if ordered[i] == ordered[i - 1] + 1:
            run_len += 1
        else:
            if run_len >= 5:
                runs.append((run_start, run_len))
            run_start = ordered[i]
            run_len = 1
    if run_len >= 5:
        runs.append((run_start, run_len))

    best_start, best_len = (
        max(runs, key=lambda t: (t[1], t[0])) if runs else (ordered[0], 1)
    )

    today_by_day: dict[int, int] = {}
    for days in days_hits:
        needle = struct.pack("<II", days - 1, days) + b"\x00\x00\x00\x00"
        j = buf.find(needle, 0, hi)
        if j >= 0:
            today_by_day[days] = j

    chosen_days: int | None = None
    chosen_abs: int | None = None
    method = "calendar_run_start"

    if today_by_day:
        # Do not use densest 14-day window — that locks to the pre-season
        # table (2039-07-25) while later sparse ptrs are "today".
        ptr_days = max(today_by_day)
        chosen_days = ptr_days
        # today_ptr is sparse; consecutive prelude days after it are the
        # current calendar-run end (Jan 14+) without jumping to fixtures.
        while (chosen_days + 1) in days_hits:
            chosen_days += 1
        chosen_abs = first_abs.get(chosen_days, today_by_day[ptr_days])
        method = (
            "calendar_run_end" if chosen_days != ptr_days else "today_ptr_latest"
        )
    else:
        chosen_days = best_start
        chosen_abs = first_abs.get(best_start)
        method = "calendar_run_start"

    iso = days_y1900_to_iso(chosen_days)
    if not iso:
        return None
    return {
        "gameDate": iso,
        "daysY1900": chosen_days,
        "runLength": best_len,
        "runStart": days_y1900_to_iso(best_start),
        "abs": chosen_abs,
        "method": method,
        "longRunCount": len(runs),
        "hint": None,
    }


def dob_from_personality_pack(buf, pack_abs: int | None) -> str | None:
    """
    Date of birth beside the mental trait pack (validated 20/20 screenshot players):

      personalityPackAbs - 21  →  day_of_year_u16 (1..366)
      personalityPackAbs - 19  →  year_u16

    Separate mark+days_y1900 DOB sites also exist in the blob but are not linked
    to UniqueID yet — this pack-adjacent encoding is what we extract.
    """
    if pack_abs is None or pack_abs < 21:
        return None
    doy = struct.unpack_from("<H", buf, pack_abs - 21)[0]
    year = struct.unpack_from("<H", buf, pack_abs - 19)[0]
    if not (1970 <= year <= 2035):
        return None
    if not (1 <= doy <= 366):
        return None
    try:
        dob = date(year, 1, 1) + timedelta(days=doy - 1)
    except Exception:
        return None
    if dob.year != year:
        return None
    return dob.isoformat()


# --- Managed club identity (Club Site UniqueID) ---
CATALOG_LO = 500_000
CATALOG_TARGET = 12 * 1024 * 1024


def read_lp32(buf, off: int):
    if off + 4 > len(buf):
        return None
    n = struct.unpack_from("<I", buf, off)[0]
    if n == 0 or n > 200 or off + 4 + n > len(buf):
        return None
    raw = bytes(buf[off + 4 : off + 4 + n])
    if any(b < 9 or 13 < b < 32 for b in raw):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        if all(32 <= b < 127 for b in raw):
            return raw.decode("ascii")
        return None


def catalog_long_name(buf, club_short: str) -> str | None:
    raw = club_short.encode("utf-8")
    start = max(0, CATALOG_LO)
    end = min(len(buf), CATALOG_TARGET)
    best: str | None = None
    while start < end:
        j = buf.find(raw, start, end)
        if j < 0:
            break
        if j >= 4 and struct.unpack_from("<I", buf, j - 4)[0] == len(raw):
            for back in range(5, 120):
                long_off = j - 4 - back
                long = read_lp32(buf, long_off)
                if not long or not long[0].isalpha():
                    continue
                if struct.unpack_from("<I", buf, long_off)[0] + 4 != back:
                    continue
                if long.startswith(("Player", "Staff", "http")):
                    continue
                if club_short not in long and not long.endswith(club_short):
                    if club_short.lower() not in long.lower():
                        continue
                if best is None or len(long) > len(best):
                    best = long
        start = j + 1
    return best


def tid_bucket(tid: int) -> str:
    if tid < 1_000:
        return "<1k"
    if tid < 50_000:
        return "1k-50k"
    if tid < 500_000:
        return "50k-500k"
    if tid < 2_000_000:
        return "500k-2m"
    return ">=2m"


def count_bucket(c: int) -> str:
    if c <= 10:
        return "0-10"
    if c <= 20:
        return "11-20"
    if c <= 35:
        return "21-35"
    if c <= 60:
        return "36-60"
    if c <= 200:
        return "61-200"
    return ">200"


def job_magnitude_bucket(x: int) -> str:
    if x < 1_000:
        return "<1k"
    if x < 50_000:
        return "1k-50k"
    if x < 500_000:
        return "50k-500k"
    if x < 2_000_000:
        return "500k-2m"
    return ">=2m"


def classify_squad_layout(
    *,
    tag_hex: str | None = None,
    inferred_layout: str | None = None,
) -> str:
    """PROGRESS layout: continue (00950e02 / zstd@26) vs native (00950e01)."""
    hx = (tag_hex or "").replace(" ", "").lower()
    if hx == "00950e02":
        return "continue"
    if hx == "00950e01":
        return "native"
    if inferred_layout == "fm24_continue_style_zstd_at_26":
        return "continue"
    return "native"


def filter_jobs(jobs_raw: list[int], *, jobs_min: int | None = None) -> list[int] | None:
    """Keep unique plausible employment IDs; reject noise lists."""
    jobs: list[int] = []
    seen: set[int] = set()
    zeros = 0
    for x in jobs_raw:
        if x == 0:
            zeros += 1
            continue
        if JOB_LO <= x <= JOB_HI and x not in seen:
            seen.add(x)
            jobs.append(x)
    min_n = SQUAD_JOBS_MIN if jobs_min is None else jobs_min
    if len(jobs) < min_n:
        return None
    if zeros > max(3, len(jobs_raw) // 5):
        return None
    # Reject nearly-sequential small counters / dense pointer tables.
    if len(jobs) >= 12:
        span = max(jobs) - min(jobs)
        if span < len(jobs) * 2 and max(jobs) < 10_000:
            return None
    return jobs


def try_jobs_at(
    buf, tid: int, c_off: int, *, layout: str, native: bool = False
) -> tuple[int, int, int, list[int], str] | None:
    """Parse count_u16 + jobs at c_off. Returns (tid, jobs_off, count, jobs, layout)."""
    if not (TID_LO <= tid <= TID_HI):
        return None
    if c_off + 2 > len(buf):
        return None
    count = struct.unpack_from("<H", buf, c_off)[0]
    jobs_off = c_off + 2
    # Continue world-walk uses 11–55. Native this-club lists are not that gate.
    if native:
        if not (1 <= count <= 80):
            return None
    elif not (SQUAD_COUNT_LO <= count <= SQUAD_COUNT_HI):
        return None
    if jobs_off + 4 * count > len(buf):
        return None
    jobs_raw = [
        struct.unpack_from("<I", buf, jobs_off + 4 * k)[0] for k in range(count)
    ]
    jobs = filter_jobs(jobs_raw, jobs_min=1 if native else SQUAD_JOBS_MIN)
    if not jobs:
        return None
    return tid, jobs_off, count, jobs, layout


def parse_squad_candidates(
    buf,
    sentinel_off: int,
    *,
    native: bool = False,
    tid_hint: int | None = None,
) -> list[tuple[int, int, int, list[int], str]]:
    """
    Try known layouts at a 7f02000000 hit.
    Returns zero or more (tid, jobs_off, count, jobs, layout).
    Native nearby UniqueID may sit before padding; tid_hint is that club id
    when the 4 bytes immediately before 7f02 are not a persist tid.
    """
    if sentinel_off + 5 > len(buf) or buf[sentinel_off : sentinel_off + 5] != LIST_SENTINEL_LOOSE:
        return []
    out: list[tuple[int, int, int, list[int], str]] = []
    after = sentinel_off + 5
    pre_tid = struct.unpack_from("<I", buf, sentinel_off - 4)[0] if sentinel_off >= 4 else 0
    if (
        native
        and tid_hint not in (None, 0)
        and not (TID_LO <= pre_tid <= TID_HI)
    ):
        pre_tid = int(tid_hint)

    attempts: list[tuple[int, int, str]] = []  # tid, c_off, layout

    # A — Schalke / continue: [tid][7f02…][ffffffff][count][jobs]
    if after + 4 <= len(buf) and buf[after : after + 4] == b"\xff\xff\xff\xff":
        attempts.append((pre_tid, after + 4, "pre_tid_ff"))

    # B — native tag: [tid?][7f02…][01 03 02 xx][count][jobs]
    if after + 4 <= len(buf) and buf[after : after + 3] == TAG_010302:
        attempts.append((pre_tid, after + 4, "pre_tid_010302"))

    # C — zero pad: [tid][7f02…][00000000][count][jobs]
    if after + 4 <= len(buf) and buf[after : after + 4] == b"\x00\x00\x00\x00":
        attempts.append((pre_tid, after + 4, "pre_tid_zeros"))

    # D — tid AFTER sentinel (94db1300-style), then optional ff / count
    if after + 4 <= len(buf):
        post_tid = struct.unpack_from("<I", buf, after)[0]
        p = after + 4
        if p + 4 <= len(buf) and buf[p : p + 4] == b"\xff\xff\xff\xff":
            attempts.append((post_tid, p + 4, "post_tid_ff"))
        elif p + 3 <= len(buf) and buf[p : p + 3] == TAG_010302:
            attempts.append((post_tid, p + 4, "post_tid_010302"))
        else:
            attempts.append((post_tid, p, "post_tid_count"))

    # E — count directly after loose (no mask)
    attempts.append((pre_tid, after, "pre_tid_direct"))

    seen_keys: set[tuple[int, int]] = set()
    for tid, c_off, layout in attempts:
        parsed = try_jobs_at(buf, tid, c_off, layout=layout, native=native)
        if not parsed:
            continue
        key = (parsed[0], parsed[1])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        out.append(parsed)
    return out


def parse_squad_at(
    buf,
    sentinel_off: int,
    *,
    require_ff: bool | None = None,
) -> tuple[int, int, int, list[int]] | None:
    """
    Backward-compat wrapper: first matching layout (prefer ff when require_ff).
    Returns (tid, jobs_off, count, jobs) or None.
    """
    cands = parse_squad_candidates(buf, sentinel_off)
    if require_ff is True:
        cands = [c for c in cands if c[4] in ("pre_tid_ff", "post_tid_ff")]
    elif require_ff is False:
        cands = [c for c in cands if c[4] not in ("pre_tid_ff", "post_tid_ff")]
    if not cands:
        return None
    # Prefer denser unique job lists, then layouts that look like first-team size.
    cands.sort(key=lambda c: (-len(c[3]), abs(c[2] - 28), c[1]))
    tid, jobs_off, count, jobs, _layout = cands[0]
    return tid, jobs_off, count, jobs


def calibrate_squad_layout(buf) -> dict:
    """Anonymous structural probe — no player/club names."""
    hits_strict = 0
    hits_loose = 0
    count_hist: dict[str, int] = defaultdict(int)
    tid_hist: dict[str, int] = defaultdict(int)
    after_loose_hex: dict[str, int] = defaultdict(int)
    job_mag_hist: dict[str, int] = defaultdict(int)
    reject_hist: dict[str, int] = defaultdict(int)
    layout_hist: dict[str, int] = defaultdict(int)
    candidates: list[dict] = []
    strict_samples: list[dict] = []

    start = 0
    while True:
        j = buf.find(LIST_SENTINEL_LOOSE, start)
        if j < 0:
            break
        hits_loose += 1
        after = buf[j + 5 : j + 13]
        after_loose_hex[after[:4].hex()] += 1
        is_strict = (
            j + len(LIST_SENTINEL) <= len(buf)
            and buf[j : j + len(LIST_SENTINEL)] == LIST_SENTINEL
        )
        if is_strict:
            hits_strict += 1

        parsed_list = parse_squad_candidates(buf, j)
        if parsed_list:
            for tid, jobs_off, count, jobs, layout in parsed_list:
                count_hist[count_bucket(count)] += 1
                tid_hist[tid_bucket(tid)] += 1
                layout_hist[layout] += 1
                job_mag_hist[job_magnitude_bucket(min(jobs))] += 1
                job_mag_hist[job_magnitude_bucket(max(jobs))] += 1
                candidates.append(
                    {
                        "absMb": round(jobs_off / 1e6, 3),
                        "count": count,
                        "uniqueJobs": len(jobs),
                        "tidBucket": tid_bucket(tid),
                        "layout": layout,
                        "jobMin": min(jobs),
                        "jobMax": max(jobs),
                    }
                )
        else:
            # Diagnose strict (ff) hits that still failed filters.
            if is_strict and j >= 4:
                c_off = j + 9
                tid = struct.unpack_from("<I", buf, j - 4)[0]
                raw_c = struct.unpack_from("<H", buf, c_off)[0] if c_off + 2 <= len(buf) else -1
                count_hist[count_bucket(raw_c)] += 1
                tid_hist[tid_bucket(tid)] += 1
                reason = "other"
                sample: dict = {
                    "tidBucket": tid_bucket(tid),
                    "count": raw_c,
                }
                if not (SQUAD_COUNT_LO <= raw_c <= SQUAD_COUNT_HI):
                    reason = "count_range"
                elif c_off + 2 + 4 * max(0, raw_c) > len(buf):
                    reason = "oob"
                else:
                    jobs_raw = [
                        struct.unpack_from("<I", buf, c_off + 2 + 4 * k)[0]
                        for k in range(raw_c)
                    ]
                    in_range = sum(1 for x in jobs_raw if JOB_LO <= x <= JOB_HI and x)
                    uniq = len({x for x in jobs_raw if JOB_LO <= x <= JOB_HI and x})
                    sample["inRange"] = in_range
                    sample["uniqueInRange"] = uniq
                    sample["rawMin"] = min(jobs_raw) if jobs_raw else 0
                    sample["rawMax"] = max(jobs_raw) if jobs_raw else 0
                    sample["rawMag"] = {
                        job_magnitude_bucket(min(jobs_raw)): 1,
                        job_magnitude_bucket(max(jobs_raw)): 1,
                    }
                    if uniq < SQUAD_JOBS_MIN:
                        reason = "jobs_filtered"
                    else:
                        reason = "filter_other"
                reject_hist[reason] += 1
                sample["reason"] = reason
                if len(strict_samples) < 12:
                    strict_samples.append(sample)
            else:
                c_off = j + 5
                if c_off + 4 <= len(buf) and buf[c_off : c_off + 4] == b"\xff\xff\xff\xff":
                    c_off += 4
                elif c_off + 3 <= len(buf) and buf[c_off : c_off + 3] == TAG_010302:
                    c_off += 4
                if c_off + 2 <= len(buf):
                    raw_c = struct.unpack_from("<H", buf, c_off)[0]
                    count_hist[count_bucket(raw_c)] += 1
                    if j >= 4:
                        tid_hist[tid_bucket(struct.unpack_from("<I", buf, j - 4)[0])] += 1
        start = j + 1

    candidates.sort(key=lambda c: (-c["uniqueJobs"], c["absMb"]))
    return {
        "sentinelLooseHits": hits_loose,
        "sentinelStrictHits": hits_strict,
        "countHistogram": dict(count_hist),
        "tidBucketHistogram": dict(tid_hist),
        "layoutHits": dict(layout_hist),
        "jobMagnitudeEdges": dict(job_mag_hist),
        "strictRejectReasons": dict(reject_hist),
        "strictRejectSamples": strict_samples,
        "bytesAfterLooseTop": dict(
            sorted(after_loose_hex.items(), key=lambda kv: -kv[1])[:12]
        ),
        "topCandidates": candidates[:15],
    }


def discover_squads(buf) -> dict[int, tuple[int, int, list[int]]]:
    """tid -> (list_abs, count, jobs). Tries all known post-7f02 layouts."""
    squads: dict[int, tuple[int, int, list[int]]] = {}
    start = 0
    while True:
        j = buf.find(LIST_SENTINEL_LOOSE, start)
        if j < 0:
            break
        for tid, jobs_off, count, jobs, _layout in parse_squad_candidates(buf, j):
            prev = squads.get(tid)
            # Prefer first-team sized lists over giant staff dumps when both map to tid.
            score = len(jobs)
            prev_score = len(prev[2]) if prev else -1
            prefer = score > prev_score
            if prev and 18 <= score <= 40 and not (18 <= prev_score <= 40):
                prefer = True
            if prefer:
                squads[tid] = (jobs_off, count, jobs)
        start = j + 1
    return squads


def pick_tid(
    squads: dict[int, tuple[int, int, list[int]]], manager_hits: dict[int, int]
) -> int:
    def score(tid: int) -> tuple:
        jobs = squads[tid][2]
        n = len(jobs)
        size_bonus = 0
        if 18 <= n <= 32:
            size_bonus = 3
        elif 15 <= n <= 40:
            size_bonus = 2
        elif 11 <= n <= 45:
            size_bonus = 1
        # Continue-save First Team tids are usually large persist ids.
        persist_bonus = 1 if tid >= 100_000 else 0
        return (
            manager_hits.get(tid, 0),
            size_bonus,
            persist_bonus,
            n,
            -squads[tid][0],
        )

    ranked = sorted(squads.keys(), key=score, reverse=True)
    return ranked[0]


def _native_list_at_sentinel(
    buf, sentinel_off: int, *, tid_hint: int | None = None
) -> dict | None:
    """parse_squad_candidates layout B (010302) preferred; 11–55 is not law."""
    cands = parse_squad_candidates(
        buf, sentinel_off, native=True, tid_hint=tid_hint
    )
    if not cands:
        return None
    cands.sort(
        key=lambda c: (
            0 if "010302" in c[4] else 1,
            -len(c[3]),
            c[1],
        )
    )
    tid, jobs_off, count, jobs, list_layout = cands[0]
    if not jobs:
        return None
    return {
        "persistTid": tid,
        "sentinelAbs": sentinel_off,
        "countAbs": jobs_off - 2,
        "jobsAbs": jobs_off,
        "count": count,
        "jobs": jobs,
        "listLayout": list_layout,
    }


def _native_list_near_uniqueid(buf, uid_abs: int, club_id: int) -> dict | None:
    """Forward UniqueID → 7f02+010302. Same expanding windows as continue."""
    n = len(buf)
    scan_from = uid_abs + 4
    if scan_from >= n:
        return None
    cid = int(club_id)
    for win in LIST_WINDOWS:
        hi = min(n, scan_from + win)
        start = scan_from
        while start < hi:
            sent = buf.find(LIST_SENTINEL_LOOSE, start, hi)
            if sent < 0:
                break
            parsed = _native_list_at_sentinel(buf, sent, tid_hint=cid)
            if (
                parsed
                and parsed.get("jobs")
                and "010302" in parsed["listLayout"]
            ):
                return parsed
            start = sent + 1
    return None


def resolve_native_ft_squad(buf, club_id: int | None) -> dict | None:
    """This club's UniqueID, then nearby 7f02+010302. Not every 7f02 in the file."""
    if club_id in (None, 0):
        return None
    cid = int(club_id)
    packed = struct.pack("<I", cid)
    catalog_hits = 0
    best: dict | None = None
    best_key: tuple | None = None
    start = 0
    while True:
        j = buf.find(packed, start)
        if j < 0:
            break
        catalog_hits += 1
        parsed = _native_list_near_uniqueid(buf, j, cid)
        if parsed and parsed.get("jobs"):
            gap = parsed["sentinelAbs"] - (j + 4)
            key = (gap, -len(parsed["jobs"]))
            if best is None or best_key is None or key < best_key:
                best = parsed
                best_key = key
        start = j + 1

    if best:
        return {
            "parentShort": None,
            "clubId": cid,
            "catalogNameAbs": None,
            "catalogName": None,
            "team": None,
            "list": best,
            "catalogHits": catalog_hits,
            "teamObjects": 0,
            "jobsFound": len(best["jobs"]),
        }
    return {
        "parentShort": None,
        "clubId": cid,
        "catalogNameAbs": None,
        "catalogName": None,
        "team": None,
        "list": None,
        "catalogHits": catalog_hits,
        "teamObjects": 0,
        "jobsFound": 0,
    }


def resolve_managed_ft_for_layout(
    mm,
    club_short: str | None,
    club_id: int | None,
    *,
    layout: str,
) -> dict | None:
    """Continue = club-object 7f02. Native = UniqueID nearby 010302. Never pick_tid."""
    if layout == "native":
        return resolve_native_ft_squad(mm, club_id)
    return resolve_ft_squad(mm, club_short, club_id=club_id)


def empty_player_dynamics() -> dict:
    return {
        "captaincy": None,
        "hierarchy": None,
        "socialGroup": None,
        "socialRank": None,
    }


def read_ft_captaincy_jobs(
    buf, list_abs: int, jobs: list[int]
) -> tuple[int | None, int | None]:
    """Captain / VC jobIds immediately after the FT job u32 list."""
    n = len(jobs)
    if n <= 0 or list_abs < 0:
        return None, None
    tail = list_abs + 4 * n
    if tail + 8 > len(buf):
        return None, None
    cap, vc = struct.unpack_from("<II", buf, tail)
    job_set = set(jobs)
    if cap not in job_set:
        cap = None
    if vc not in job_set:
        vc = None
    return cap, vc


def _parse_social_job_lists(
    buf, off: int, job_set: set[int], n_lists: int = 4
) -> list[list[int]] | None:
    groups: list[list[int]] = []
    for _ in range(n_lists):
        if off + 2 > len(buf):
            return None
        n = struct.unpack_from("<H", buf, off)[0]
        off += 2
        if n > DYNAMICS_SOCIAL_LIST_MAX:
            return None
        need = 4 * n
        if off + need > len(buf):
            return None
        listed = [struct.unpack_from("<I", buf, off + 4 * i)[0] for i in range(n)]
        if any(job not in job_set for job in listed):
            return None
        groups.append(listed)
        off += need
    return groups


def find_ft_social_job_lists(buf, jobs: list[int]) -> list[list[int]] | None:
    """Four counted FT job lists after the social motif. None if missing."""
    job_set = set(jobs)
    if not job_set:
        return None
    pos = 0
    motif_len = len(DYNAMICS_SOCIAL_MOTIF)
    while True:
        hit = buf.find(DYNAMICS_SOCIAL_MOTIF, pos)
        if hit < 0:
            return None
        groups = _parse_social_job_lists(buf, hit + motif_len, job_set, 4)
        if groups is not None:
            return groups
        pos = hit + 1


def apply_ft_dynamics(
    buf, players: list[dict], list_abs: int, jobs: list[int]
) -> None:
    """Fill FT captaincy + social group + list-order rank. hierarchy stays None."""
    cap_job, vc_job = read_ft_captaincy_jobs(buf, list_abs, jobs)
    social_lists = find_ft_social_job_lists(buf, jobs)
    by_job: dict[int, tuple[str, int]] = {}
    if social_lists:
        for label, group in zip(DYNAMICS_SOCIAL_LABELS, social_lists):
            for rank, job in enumerate(group):
                by_job.setdefault(job, (label, rank))
    for player in players:
        job = int(player.get("jobId") or 0)
        cap = None
        if cap_job is not None and job == cap_job:
            cap = "captain"
        elif vc_job is not None and job == vc_job:
            cap = "viceCaptain"
        soc, rank = by_job.get(job, (None, None))
        player["dynamics"] = {
            "captaincy": cap,
            "hierarchy": None,
            "socialGroup": soc,
            "socialRank": rank,
        }


def scan_manager_hits(
    mm, tids: list[int], *, windows: list[tuple[int, int]] | None = None
) -> dict[int, int]:
    """Count 0b02 <tid> 02 <uid> manager/staff links for candidate squad tids."""
    hits: dict[int, int] = defaultdict(int)
    if not tids:
        return hits
    spans = windows or [(0, len(mm))]
    for tid in tids:
        pat = b"\x0b\x02" + struct.pack("<I", tid) + b"\x02"
        for lo, hi in spans:
            lo = max(0, lo)
            hi = min(len(mm), hi)
            if lo >= hi:
                continue
            j = mm.find(pat, lo, hi)
            while j >= 0 and j + 11 <= hi:
                uid = struct.unpack_from("<I", mm, j + 7)[0]
                if UID_LO <= uid <= UID_HI:
                    window = bytes(mm[max(lo, j - 48) : j])
                    hits[tid] += 3 if STAFF_MARK in window else 1
                j = mm.find(pat, j + 1, hi)
    return hits


def walk_world_squads_if_needed(
    mm,
    *,
    club_short: str | None,
    squads: dict[int, tuple[int, int, list[int]]],
    manager_hits: dict[int, int],
) -> tuple[dict[int, tuple[int, int, list[int]]], dict[int, int], str]:
    """All-club 7f02 + staff-link ranking only when club identity is unknown."""
    if club_short:
        return squads, manager_hits, "skipped_identity_known"
    if not squads:
        squads = discover_squads(mm)
    if not squads:
        return squads, manager_hits, "empty"
    ft_like = [
        tid
        for tid, (_abs, _count, jobs) in squads.items()
        if 15 <= len(jobs) <= 40
    ] or list(squads.keys())
    spans = [(0, min(len(mm), 400 * 1024 * 1024))]
    if len(mm) > EMPLOYMENT_TAIL:
        spans.append((len(mm) - EMPLOYMENT_TAIL, len(mm)))
    scanned = scan_manager_hits(mm, ft_like, windows=spans)
    for tid, n in scanned.items():
        manager_hits[tid] = max(manager_hits.get(tid, 0), n)
    return squads, manager_hits, "fallback_no_identity"


def collect_doubles(buf, uid: int, limit: int = 12) -> list[int]:
    """Only scan the head of the file — doubles for squad players live early."""
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(buf), PERSON_HEAD)
    j = buf.find(pat, 0, end)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = buf.find(pat, j + 1, end)
    return hits


def score_person_double(buf, dab: int) -> int:
    """Prefer person records with sparse 01-pad after the double UID."""
    blob = bytes(buf[dab : dab + 128])
    score = 0
    if b"\x01\x01\x01" in blob[8:80]:
        score += 5
    if len(blob) > 8 and blob[8] in (1, 2):
        score += 1
    return score


def find_mental_trait_pack(
    buf, doubles: list[int]
) -> tuple[dict[str, int], int, int] | None:
    """
    Find contiguous mental-trait pack near a person double-UID.

    Signature: ≥4 leading zeros, 8×(1..20), 2 arbitrary bytes, then 00×6 01.
    Returns (values, packAbs, doubleAbs) or None.

    Disambiguation: false signature hits often sit AFTER the person double
    (Marco Tassinari: Genie pack @ −652, Amb=4 decoy @ +701). Prefer packs
    with packAbs < doubleAbs, then nearest |pack − double|.
    """
    if not doubles:
        return None
    ranked = sorted(doubles, key=lambda d: (-score_person_double(buf, d), d))
    candidates: list[tuple[int, int, int, bytes, int]] = []
    for dab in ranked:
        lo = max(0, dab - MENTAL_HA_LOOKBACK)
        hi = min(len(buf), dab + MENTAL_HA_LOOKAHEAD)
        window = bytes(buf[lo:hi])
        start = 0
        while True:
            j = window.find(MENTAL_HA_TRAIL, start)
            if j < 0:
                break
            pack_off = j - 10  # 8 attrs + 2 trailer bytes before 00×6 01
            if pack_off >= 0:
                raw = window[pack_off : pack_off + 8]
                if len(raw) == 8 and all(1 <= b <= 20 for b in raw):
                    lead = window[max(0, pack_off - 6) : pack_off]
                    if lead.count(0) >= 4:
                        abs_pack = lo + pack_off
                        # after=1 ranks packs at/after the double below packs before it
                        after = 0 if abs_pack < dab else 1
                        dist = abs(abs_pack - dab)
                        candidates.append((after, dist, abs_pack, raw, dab))
            start = j + 1

    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1], t[2]))
    _, _, abs_pack, raw, dab = candidates[0]
    values = {k: int(raw[i]) for i, k in enumerate(PERSONALITY_PACK_ORDER)}
    return values, abs_pack, dab


def resolve_name(buf, uid: int, doubles: list[int] | None = None) -> str:
    """Prefer name near double-UID / employment tail — avoid scanning half the save."""
    pat = b"\x00\x02" + struct.pack("<I", uid)
    best = ""

    def consider_range(lo: int, hi: int, limit: int = 8) -> bool:
        nonlocal best
        j = buf.find(pat, lo, hi)
        checked = 0
        while j >= 0 and checked < limit:
            name = parse_name_at(buf, j + 2)
            if name and (not best or (" " in name and " " not in best)):
                best = name
                if " " in best:
                    return True
            checked += 1
            j = buf.find(pat, j + 1, hi)
        return False

    for dab in doubles or []:
        lo = max(0, dab - 16_384)
        hi = min(len(buf), dab + 8_192)
        if consider_range(lo, hi):
            return best

    tail_lo = max(0, len(buf) - EMPLOYMENT_TAIL)
    if consider_range(tail_lo, len(buf), limit=16):
        return best

    # Last resort: limited head search
    if consider_range(0, min(len(buf), PERSON_HEAD), limit=4):
        return best

    # Gap UIDs (Risse / Görrissen / Pérez): no `\x00\x02`+uid inline names.
    marked = resolve_name_from_mark(buf, uid, doubles)
    if marked:
        return marked
    return best or f"uid:{uid}"


def uid_in_continue_career_band(uid: int) -> bool:
    """True when uid sits in the continue-career magnitude band.

    Heuristic for ranking employment hits — not a filter that drops listed people.
    """
    return UID_LO <= uid <= UID_HI


def plausible_person_uid(uid: int, job: int | None = None) -> bool:
    """Reject padding / self-job echoes. Not a save-specific UniqueID floor."""
    if uid < 256 or uid == 0xFFFFFFFF:
        return False
    if job is not None and uid == job:
        return False
    return True


def has_person_double(buf, uid: int) -> bool:
    """Person object marker: uid||uid in the person-head span."""
    if not uid:
        return False
    pat = struct.pack("<II", uid, uid)
    end = min(len(buf), PERSON_HEAD)
    return buf.find(pat, 0, end) >= 0


def resolve_job_uid(buf, job: int) -> int:
    """Employment links sit near EOF — rfind-shaped tail scan (last hit wins)."""
    jb = struct.pack("<I", job)
    start = max(0, len(buf) - EMPLOYMENT_TAIL)
    band = 0
    oob = 0
    for tag in (0x09, 0x0B, 0x0A, 0x08):
        pat = bytes([tag, 0x02]) + jb + b"\x02"
        j = buf.find(pat, start)
        while j >= 0 and j + 11 <= len(buf):
            uid = struct.unpack_from("<I", buf, j + 7)[0]
            if plausible_person_uid(uid, job):
                if uid_in_continue_career_band(uid):
                    band = uid
                else:
                    oob = uid
            j = buf.find(pat, j + 1)
    if band:
        return band
    if oob and has_person_double(buf, oob):
        return oob
    return 0


def resolve_job_uids_double_fallback(
    mm: mmap.mmap, jobs: list[int]
) -> dict[int, int]:
    """
    Gap-job fallback (T004C): some loaned-out squad slots have no
    `<tag> 02 <job> 02 <uid>` employment. Instead: `job || uid || uid`.
    Prefer the optional 12-byte prefix when present.
    Continue-career band is preferred when both exist; out-of-band uid||uid is kept.
    """
    if not jobs:
        return {}
    prefix = bytes.fromhex("000000000802403004000000")
    out: dict[int, int] = {}
    for job in jobs:
        jb = struct.pack("<I", job)
        for needle_prefix in (prefix + jb, jb):
            pos = 0
            oob = 0
            band = 0
            while True:
                j = mm.find(needle_prefix, pos)
                if j < 0:
                    break
                uid_at = j + len(needle_prefix)
                if uid_at + 8 <= len(mm):
                    u1 = struct.unpack_from("<I", mm, uid_at)[0]
                    u2 = struct.unpack_from("<I", mm, uid_at + 4)[0]
                    if u1 == u2 and plausible_person_uid(u1, job):
                        if uid_in_continue_career_band(u1):
                            band = u1
                            break
                        oob = u1
                pos = j + 1
            if band:
                out[job] = band
                break
            if oob:
                out[job] = oob
                break
    return out


def _ingest_employment_uid(
    job: int,
    uid: int,
    *,
    wanted: set[int],
    job_uid: dict[int, int],
    oob_last: dict[int, int],
) -> None:
    if job not in wanted or job in job_uid:
        return
    if not plausible_person_uid(uid, job):
        return
    if uid_in_continue_career_band(uid):
        job_uid[job] = uid
        return
    oob_last[job] = uid


def resolve_job_uids_batch(mm: mmap.mmap, jobs: list[int]) -> dict[int, int]:
    """Map jobId → person UniqueID (tail scan, then whole-file fallback).

    Continue-career UniqueID magnitude is a preference. Out-of-band people are
    kept when the employment tag is confirmed by a person double (T085).
    """
    job_uid: dict[int, int] = {}
    oob_last: dict[int, int] = {}
    wanted = set(jobs)
    search_lo = max(0, len(mm) - EMPLOYMENT_TAIL)
    if len(mm) < EMPLOYMENT_TAIL * 2:
        search_lo = 0

    def scan_from(start: int) -> None:
        for tag in (0x09, 0x0B, 0x0A, 0x08):
            if len(job_uid) >= len(wanted):
                return
            prefix = bytes([tag, 0x02])
            j = mm.find(prefix, start)
            while j >= 0 and j + 11 <= len(mm):
                if mm[j + 6] == 0x02:
                    job = struct.unpack_from("<I", mm, j + 2)[0]
                    uid = struct.unpack_from("<I", mm, j + 7)[0]
                    _ingest_employment_uid(
                        job,
                        uid,
                        wanted=wanted,
                        job_uid=job_uid,
                        oob_last=oob_last,
                    )
                    if len(job_uid) >= len(wanted):
                        return
                j = mm.find(prefix, j + 1)

    scan_from(search_lo)
    if len(job_uid) < len(wanted) * 0.5 and search_lo > 0:
        scan_from(0)
    for job, uid in oob_last.items():
        if job not in job_uid and has_person_double(mm, uid):
            job_uid[job] = uid
    missing = [j for j in jobs if j not in job_uid]
    if missing:
        job_uid.update(resolve_job_uids_double_fallback(mm, missing))
    return job_uid


# Loaned-out object (T004A/B/T012): pad + `64 ff kind | A | 10×0 | B | club×2 | 0x000A`
# kind 0x26 = Sipho/international; 0x24 = domestic (Vlad / II / U19).
# Require `00×4 | FF×4 | FF | 00×4` immediately before the motif — without it,
# raising club-hi FPs at-club U19 (Eschweiler). Pad+hi tags Kasprakov / Boxleitner.
# Lookback 8..73 — Vlad needs 49; Risse (gap II) needs 57; Abbe (FT) needs 73.
# Per-unit job sets avoid cross-unit collisions (Abbe↔Zetzmann @904).
# Club hi 5M — youth host clubs (Kasprakov 877204). 3609393 is an II team-body
# dup, not a host — list-adjacent 64ff24 FPs that club (T040 Itu).
LOAN_OUT_MOTIF_PREFIX = b"\x64\xff"
LOAN_OUT_PAD = b"\x00\x00\x00\x00\xff\xff\xff\xff\xff\x00\x00\x00\x00"
LOAN_KIND_LO, LOAN_KIND_HI = 0x20, 0x30
LOAN_LOOKBACK_LO, LOAN_LOOKBACK_HI = 8, 73
LOAN_TEMPLATE_LEN = 3 + 4 + 10 + 4 + 4 + 4 + 2  # motif..0x000A
LOAN_CLUB_LO = 50
LOAN_CLUB_HI = 5_000_000
# Packed subunit job arrays sit 4 bytes apart. A team-body `64 ff 24` after the
# list matches the loan template; true loan objects have one unit job in
# lookback (Konya noise is 2). Reject runs of 3+.
LOAN_LIST_STRIDE4_RUN_MIN = 3


def _parse_loan_out_template(
    mm: mmap.mmap, motif_at: int, parent_club: int
) -> int | None:
    """Return loanClubId if motif_at matches the loan-out template, else None."""
    if motif_at + LOAN_TEMPLATE_LEN > len(mm):
        return None
    if motif_at < len(LOAN_OUT_PAD):
        return None
    if mm[motif_at - len(LOAN_OUT_PAD) : motif_at] != LOAN_OUT_PAD:
        return None
    if mm[motif_at : motif_at + 2] != LOAN_OUT_MOTIF_PREFIX:
        return None
    kind = mm[motif_at + 2]
    if not (LOAN_KIND_LO <= kind <= LOAN_KIND_HI):
        return None
    base = motif_at + 3
    if mm[base + 4 : base + 14] != b"\x00" * 10:
        return None
    c1 = struct.unpack_from("<I", mm, base + 18)[0]
    c2 = struct.unpack_from("<I", mm, base + 22)[0]
    marker = struct.unpack_from("<H", mm, base + 26)[0]
    if (
        c1 != c2
        or c1 == parent_club
        or not (LOAN_CLUB_LO <= c1 <= LOAN_CLUB_HI)
        or marker != 0x000A
    ):
        return None
    return c1


def _lookback_unit_stride4_run(mm: mmap.mmap, motif_at: int, jobs: set[int]) -> int:
    """Longest 4-byte-stride run of unit jobs in the loan lookback window."""
    backs: list[int] = []
    for back in range(LOAN_LOOKBACK_LO, LOAN_LOOKBACK_HI + 1):
        start = motif_at - back
        if start < 0:
            continue
        job = struct.unpack_from("<I", mm, start)[0]
        if job in jobs:
            backs.append(back)
    best = run = 0
    prev: int | None = None
    for b in backs:
        if prev is not None and b - prev == 4:
            run += 1
        else:
            run = 1
        if run > best:
            best = run
        prev = b
    return best


def detect_loaned_out_jobs(
    mm: mmap.mmap, jobs: set[int], parent_club: int
) -> dict[int, int | None]:
    """
    jobId → loanClubId (or None if template hit but club rejected).

    Motif-first scan: every `64 ff` with kind in 0x20..0x30 matching the
    FF-pad + 10-zero + dup-club + 0x000A template; look back 8..73 for a
    squad jobId.

    Extract calls this **per unit** (FT / II / U19 job sets separately). That
    avoids cross-unit collisions on shared motifs (Abbe FT @73 vs Zetzmann II
    @57 on club 904). Do not widen to endpoint multi-tag: on II-only pools the
    farthest match is at-club noise (Konya on Abbe's motif).

    Skip templates whose lookback is a packed subunit job-list (T040): the
    next team-body `64 ff 24` + dup satisfies the loan template and would
    tag the last at-club II/FT body (Itu) as loanedOut.
    """
    if not jobs:
        return {}
    out: dict[int, int | None] = {}
    pos = 0
    while True:
        j = mm.find(LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        loan_club = _parse_loan_out_template(mm, j, parent_club)
        if loan_club is None:
            pos = j + 1
            continue
        if _lookback_unit_stride4_run(mm, j, jobs) >= LOAN_LIST_STRIDE4_RUN_MIN:
            pos = j + 1
            continue
        matched_job: int | None = None
        for back in range(LOAN_LOOKBACK_LO, LOAN_LOOKBACK_HI + 1):
            start = j - back
            if start < 0:
                continue
            job = struct.unpack_from("<I", mm, start)[0]
            if job in jobs and job != loan_club:
                matched_job = job
                break
        if matched_job is not None and matched_job not in out:
            out[matched_job] = loan_club
        pos = j + 1
    return out


def detect_loaned_out_via_foreign_u19(
    mm: mmap.mmap,
    jobs: set[int],
    parent_club: int,
    parent_short: str,
) -> dict[int, int | None]:
    """
    Legacy T012 namelist attach. Not the extract youth-loan path (T086):
    outgoing = loan object on a unit job, same recipe FT / II / U19.
    """
    if not jobs:
        return {}
    parent_l = (parent_short or "").lower()
    out: dict[int, int | None] = {}
    pos = NAME_BAND_LO
    end = min(len(mm), NAME_BAND_HI)
    while True:
        j = mm.find(b" U19", pos, end)
        if j < 0:
            break
        name_abs: int | None = None
        name_len = 0
        name: str | None = None
        for back in range(4, 64):
            off = j - back
            if off < 0:
                continue
            n = struct.unpack_from("<I", mm, off)[0]
            if n == back and 5 <= n <= 60:
                label = read_lp32(mm, off)
                if label and label.endswith(" U19"):
                    name_abs = off
                    name_len = n
                    name = label
                break
        pos = j + 1
        if name_abs is None or not name:
            continue
        core = name[: -len(" U19")]
        if parent_l and parent_l in core.lower():
            continue
        lst = parse_list_near_name(mm, name_abs, name_len)
        if not lst:
            continue
        overlap = [jid for jid in lst["jobs"] if jid in jobs and jid not in out]
        if not overlap:
            continue
        club: int | None = None
        lo = max(0, name_abs - 96)
        hi = min(len(mm), name_abs + name_len + 96)
        for o in range(lo, hi - 3, 4):
            a = struct.unpack_from("<I", mm, o)[0]
            # Host club ids near youth labels are small catalog ids.
            if LOAN_CLUB_LO <= a <= 20_000 and a != parent_club:
                club = a
                break
        for jid in overlap:
            out[jid] = club
    return out


def merge_loan_hits(
    *maps: dict[int, int | None],
) -> dict[int, int | None]:
    """First non-empty hit wins (motif before foreign-list attach)."""
    out: dict[int, int | None] = {}
    for m in maps:
        for job, club in m.items():
            if job not in out:
                out[job] = club
    return out


def rehome_loaned_newgen_to_u19(
    reserves: dict | None, u19: dict | None
) -> None:
    """
    T012: Boxleitner-class youth sit on II discovery but are outgoing U19 loans.
    Move only NEWGEN loanedOut with high host clubId (>200k youth hosts) from
    II → U19 so Loans → Under 19s matches FM. Domestic II loans (Manole/Dunkel)
    stay on Reserves. T040: do not feed this with list-adjacent team-dup
    FPs (3609393) — detect drops those before rehome.
    """
    if not reserves or not u19:
        return
    ii_players = list(reserves.get("players") or [])
    u19_players = list(u19.get("players") or [])
    if not ii_players:
        return
    u19_uids = {int(p.get("uid") or 0) for p in u19_players}
    keep_ii: list[dict] = []
    moved: list[dict] = []
    for p in ii_players:
        uid = int(p.get("uid") or 0)
        loan = p.get("loan") or {}
        club = loan.get("loanClubId")
        try:
            club_i = int(club) if club is not None else 0
        except (TypeError, ValueError):
            club_i = 0
        if (
            loan.get("status") == "loanedOut"
            and (p.get("kind") == "NEWGEN")
            and club_i > 200_000
            and uid
            and uid not in u19_uids
        ):
            moved.append(p)
            u19_uids.add(uid)
        else:
            keep_ii.append(p)
    if not moved:
        return
    reserves["players"] = keep_ii
    u19["players"] = u19_players + moved


def apply_loan_status(
    players: list[dict],
    loaned_out: dict[int, int | None],
    *,
    parent_club: int,
) -> None:
    """Attach player.loan for mentoring / roster split (mutates players)."""
    for p in players:
        job = int(p.get("jobId") or 0)
        if job not in loaned_out:
            continue
        p["loan"] = {
            "status": "loanedOut",
            "parentClubId": parent_club,
            "loanClubId": loaned_out[job],
            "parentClubName": None,
            "loanClubName": None,
        }


def loan_hits_for_unit(
    mm: mmap.mmap, jobs: set[int], parent_club: int
) -> dict[int, int | None]:
    """Outgoing = loan object on this unit's jobs. Same recipe FT / II / U19."""
    return detect_loaned_out_jobs(mm, jobs, parent_club)


def census_unit_row(
    name: str,
    jobs: list[int],
    loaned: dict[int, int | None],
) -> dict:
    """One unit's employed / at-club / loaned counts. Empty loaned is honest 0."""
    employed = len(jobs)
    loaned_n = sum(1 for j in jobs if j in loaned)
    return {
        "name": name,
        "employed": employed,
        "atClub": employed - loaned_n,
        "loaned": loaned_n,
    }


def build_loan_census(
    *,
    club_id: int | None,
    club_name: str,
    units: list[dict],
) -> dict:
    """Census payload: missing units are omitted by the caller, not zero-filled."""
    return {
        "clubId": club_id,
        "clubName": club_name,
        "units": units,
    }


def emit_loan_census(t0: float, census: dict) -> None:
    """One PROGRESS/NDJSON line after the loan split, before remaining HA fill."""
    bits = [
        f"{u['name']} {u['atClub']} at-club / {u['loaned']} loaned"
        for u in (census.get("units") or [])
        if isinstance(u, dict) and u.get("name")
    ]
    club = census.get("clubName") or census.get("clubId") or ""
    progress(
        t0,
        phase="census",
        message=(
            f"{club}: " + " · ".join(bits) if bits else f"{club}: no units"
        ),
        pct=85,
        clubId=census.get("clubId"),
        clubName=census.get("clubName"),
        units=census.get("units") or [],
    )


def _person_doubles_capa(mm: mmap.mmap, uid: int, *, limit: int = 40) -> list[int]:
    nb = struct.pack("<I", uid)
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(nb, start)
        if j < 0:
            break
        if j < 800_000_000 and mm.find(nb, j + 4, min(len(mm), j + 48)) > 0:
            out.append(j)
        start = j + 1
    return out


def _nearest_capa_core(mm: mmap.mmap, dab: int) -> tuple[int, int, int] | None:
    lo = max(0, dab - CAPA_LOOKBACK)
    best_at = -1
    best: tuple[int, int] | None = None
    for off in range(lo, dab - 19):
        p1 = struct.unpack_from("<I", mm, off)[0]
        if ((p1 >> 24) & 0xFF) != CAPA_PTR_HI:
            continue
        p2 = struct.unpack_from("<I", mm, off + 4)[0]
        if p1 != p2 or mm[off + 8] != 0x02:
            continue
        ca = struct.unpack_from("<H", mm, off + 15)[0]
        pa = struct.unpack_from("<H", mm, off + 17)[0]
        if not (1 <= ca <= 200 and 1 <= pa <= 200):
            continue
        if off > best_at:
            best_at = off
            best = (ca, pa)
    if best is None:
        return None
    return best[0], best[1], dab - best_at


def person_population_kind(uid: int) -> str:
    """Classify REAL vs NEWGEN for personality regen_only rules.

    Continue-career UID magnitude only. Outside that band, kind is UNKNOWN —
    do not apply NEWGEN_UID_FLOOR as law, and do not drop the person.
    """
    if not uid or uid <= 0:
        return "UNKNOWN"
    if not uid_in_continue_career_band(uid):
        return "UNKNOWN"
    return "NEWGEN" if uid >= NEWGEN_UID_FLOOR else "REAL"


def enrich_capa_on_players(mm: mmap.mmap, players: list[dict]) -> int:
    """Attach ca/pa onto player dicts. Returns count resolved."""
    resolved = 0
    for p in players:
        uid = int(p.get("uid") or 0)
        if not uid:
            p["ca"] = None
            p["pa"] = None
            continue
        best: tuple[int, int, int] | None = None
        for dab in _person_doubles_capa(mm, uid):
            hit = _nearest_capa_core(mm, dab)
            if hit is None:
                continue
            if best is None or hit[2] < best[2]:
                best = hit
        if best is not None:
            p["ca"] = best[0]
            p["pa"] = best[1]
            resolved += 1
        else:
            p["ca"] = None
            p["pa"] = None
    return resolved


def build_players_from_jobs(
    mm: mmap.mmap,
    jobs: list[int],
    job_uid: dict[int, int],
    *,
    names_only: bool,
    t0: float,
    phase: str,
    progress_base_pct: int = 80,
    progress_span_pct: int = 18,
) -> list[dict]:
    """Resolve names + CA attrs for a squad job list.

    Every listed job is kept (T085). Missing UniqueID / pack / CA card → attrs
    stay None (UI —). One pack blob + one CA card per person; no third extract.
    """
    players: list[dict] = []
    listed = max(1, len(jobs))
    for i, job in enumerate(jobs):
        uid = int(job_uid.get(job) or 0)
        doubles = collect_doubles(mm, uid) if uid else []
        name = resolve_name(mm, uid, doubles) if uid else f"job:{job}"
        best_double = None
        attrs = None
        general = None
        personality_pack_abs = None
        attr_card_abs = None
        attr_kind = None

        pack = find_mental_trait_pack(mm, doubles)
        date_of_birth = None
        if pack is not None:
            pack_vals, personality_pack_abs, best_double = pack
            general = empty_general()
            general["adaptability"] = pack_vals["adaptability"]
            for k in PERSONALITY_FROM_PACK:
                general[k] = pack_vals[k]
            date_of_birth = dob_from_personality_pack(mm, personality_pack_abs)

        best_quality: tuple[int, int, int, int, int] | None = None
        best_rec = None
        best_card_abs = None
        best_history: list[dict] | None = None
        ca_double = best_double
        for dab in doubles:
            lo = max(0, dab - ATTR_LOOKBACK)
            window = bytes(mm[lo:dab])
            history = build_ca_history(window)
            tip = history[-1] if history else None
            scored = score_attr_window(window, tip=tip)
            if not scored:
                continue
            quality, win_off, rec = scored
            if best_quality is None or quality > best_quality:
                best_quality = quality
                ca_double = dab
                best_rec = rec
                best_card_abs = lo + win_off
                best_history = history
        attribute_history = best_history
        live_status = "empty"
        if best_rec is not None and ca_double is not None and best_card_abs is not None:
            attribute_history, live_status = ensure_live_ca_on_history(
                attribute_history,
                best_rec,
                gap=ca_double - best_card_abs,
            )
        if best_rec is not None and ca_double is not None:
            decoded = decode_attrs(best_rec)
            attr_kind = decoded.pop("_kind", None)
            decoded.pop("_cardMeta", None)
            attr_card_abs = best_card_abs
            if best_double is None:
                best_double = ca_double
            # Trusted CA tip only. When live_status is "rejected" the lookback card
            # is foreign/wiped (Gilson-class Det20/Lea3 decoy) — never apply it as
            # live mental, even if there is no history tip to fall back on.
            tip = attribute_history[-1] if attribute_history else None
            if live_status == "rejected":
                if tip is not None:
                    mental_src = tip.get("mental") or {}
                    if names_only:
                        attrs = {
                            "mental": {
                                "determination": mental_src.get("determination"),
                                "leadership": mental_src.get("leadership"),
                            },
                            "general": general,
                        }
                    else:
                        attrs = {
                            nest: dict(tip[nest])
                            for nest in (
                                "mental",
                                "physical",
                                "technical",
                                "goalkeeping",
                            )
                            if isinstance(tip.get(nest), dict)
                        }
                        if general is not None:
                            attrs["general"] = general
                        if tip.get("kind"):
                            attr_kind = tip.get("kind")
                else:
                    # hist=0 + rejected decoy: HA pack only; Det/Lea stay unknown
                    attrs = {
                        "mental": {
                            "determination": None,
                            "leadership": None,
                        },
                        "general": general,
                    }
                    attr_card_abs = None
                    attr_kind = None
            elif names_only:
                mental = decoded.get("mental") or {}
                attrs = {
                    "mental": {
                        "determination": mental.get("determination"),
                        "leadership": mental.get("leadership"),
                    },
                    "general": general,
                }
            else:
                attrs = decoded
                if general is not None:
                    attrs["general"] = general
        elif general is not None:
            attrs = {
                "mental": {
                    "determination": None,
                    "leadership": None,
                },
                "general": general,
            }

        players.append(
            {
                "jobId": job,
                "uid": uid,
                "name": name,
                "kind": person_population_kind(uid),
                "dateOfBirth": date_of_birth,
                "nation": None,
                "secondNation": None,
                "positions": None,
                "dynamics": empty_player_dynamics(),
                "training": {"unit": None},
                "attributes": attrs,
                "attributeHistory": attribute_history,
                "_extract": {
                    "doubleUidAbs": best_double,
                    "personalityPackAbs": personality_pack_abs,
                    "attrCardAbs": attr_card_abs,
                    "kind": attr_kind,
                    "historyPoints": (
                        len(attribute_history) if attribute_history else 0
                    ),
                },
            }
        )
        if i % 4 == 0 or i + 1 == len(jobs):
            progress(
                t0,
                phase=phase if names_only else f"{phase}-attrs",
                message=(
                    f"{phase.title()} {len(players)}/{listed}"
                    if names_only
                    else f"{phase.title()} attrs {len(players)}/{listed}"
                ),
                pct=progress_base_pct
                + int(progress_span_pct * (i + 1) / max(1, len(jobs))),
                playersDone=len(players),
            )
    return players


def main() -> int:
    names_only, parent_short_override = parse_cli_flags()
    save, is_bin = resolve_save()
    t0 = time.perf_counter()
    save_size = save.stat().st_size
    estimate_out = max(save_size * 3, 64 * 1024 * 1024)

    squads: dict[int, tuple[int, int, list[int]]] = {}
    manager_hits: dict[int, int] = defaultdict(int)
    out_bytes = 0
    container: dict = {}
    tmp: Path
    delete_tmp = False
    squad_layout = "native"

    if is_bin:
        tmp = save
        out_bytes = save_size
        container = {
            "inferredLayout": "predecompressed_bin",
            "saveBytes": save_size,
            "zstdOffset": None,
        }
        squad_layout = classify_squad_layout(
            inferred_layout=container["inferredLayout"]
        )
        progress(
            t0,
            phase="start",
            message=f"Opening {save.name}",
            pct=0,
            saveBytes=save_size,
            layout=squad_layout,
            inferredLayout=container["inferredLayout"],
        )
    else:
        container = probe_container(save)
        squad_layout = str(container.get("layout") or classify_squad_layout(
            inferred_layout=container.get("inferredLayout")
        ))
        progress(
            t0,
            phase="start",
            message=f"Opening {save.name}",
            pct=0,
            saveBytes=save_size,
            layout=squad_layout,
            inferredLayout=container.get("inferredLayout"),
            zstdOffset=container.get("zstdOffset"),
        )

        zstd_off = container.get("zstdOffset")
        if zstd_off is None:
            return fail(
                t0,
                "Unsupported .fm container — no readable zstd stream in the header. "
                "Native FM26 career saves may use a different layout than FM24→FM26 continue saves.",
                code=1,
                **container,
            )

        fd, tmp_name = tempfile.mkstemp(prefix="fmt-fm-", suffix=".bin")
        os.close(fd)
        tmp = Path(tmp_name)
        delete_tmp = True

        last_progress_out = 0

        with save.open("rb") as f, tmp.open("wb") as out:
            f.seek(int(zstd_off))
            reader = zstd.ZstdDecompressor().stream_reader(f)
            try:
                while True:
                    try:
                        block = reader.read(CHUNK)
                    except zstd.ZstdError as e:
                        if out_bytes == 0:
                            tmp.unlink(missing_ok=True)
                            return fail(
                                t0,
                                f"zstd decompress failed at offset {zstd_off}: {e}",
                                code=1,
                                **container,
                            )
                        break
                    if not block:
                        break
                    out.write(block)
                    out_bytes += len(block)

                    step = (
                        4 * 1024 * 1024
                        if save_size < 80 * 1024 * 1024
                        else 32 * 1024 * 1024
                    )
                    if out_bytes - last_progress_out >= step:
                        last_progress_out = out_bytes
                        elapsed = time.perf_counter() - t0
                        rate = out_bytes / elapsed if elapsed > 0.05 else 0
                        remain = max(0, estimate_out - out_bytes)
                        eta = int(1000 * remain / rate) if rate > 0 else None
                        progress(
                            t0,
                            phase="decompress",
                            message="Decompressing save",
                            pct=min(70, int(70 * out_bytes / max(1, estimate_out))),
                            outBytes=out_bytes,
                            etaMs=eta,
                        )
            finally:
                try:
                    reader.close()
                except zstd.ZstdError:
                    pass

        progress(
            t0,
            phase="resolve",
            message="Resolving First Team",
            pct=72,
            outBytes=out_bytes,
        )

        if out_bytes == 0:
            tmp.unlink(missing_ok=True)
            return fail(
                t0,
                "Decompress produced 0 bytes — container not handled yet.",
                code=1,
                **container,
            )

    players: list[dict] = []
    reserves: dict | None = None
    u19: dict | None = None
    club_id = None
    club_short = None
    club_name = None
    game_date = None
    game_date_info = None
    best_tid = 0
    list_abs = 0
    count = 0
    jobs: list[int] = []
    ft_discovery_method = "max_manager_staff_link_among_squad_lists"
    ft_hit: dict | None = None
    ft_list: dict | None = None
    abort_world: dict | None = None
    world_lists = "skipped_identity_known"
    ident_diag: dict = {}
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            identity, ident_diag = try_discover_managed_club(
                mm,
                limits=(EARLY_SCAN, IDENTITY_DEADLINE, CATALOG_TARGET, len(mm)),
            )
            club_id = identity["clubId"] if identity else None
            club_short = identity["clubNameShort"] if identity else None
            club_name = catalog_long_name(mm, club_short) if club_short else None
            if club_short and not club_name:
                club_name = club_short
            if not club_short and parent_short_override:
                club_short = parent_short_override
                club_name = club_name or club_short
            squad_layout = classify_squad_layout(
                tag_hex=(identity or {}).get("tagHex"),
                inferred_layout=container.get("inferredLayout"),
            )
            if identity:
                progress(
                    t0,
                    phase="identity",
                    message=f"club={club_name} id={club_id}",
                    pct=73,
                    layout=squad_layout,
                    tagHex=identity.get("tagHex"),
                )
            elif ident_diag:
                progress(
                    t0,
                    phase="identity",
                    message=(
                        "No managed-club identity "
                        f"(scanned {ident_diag.get('bytesScanned')} bytes)"
                    ),
                    pct=73,
                    layout=squad_layout,
                    **{
                        k: ident_diag[k]
                        for k in ("bytesScanned", "lastTagAbs", "searchBound", "tagHexes")
                        if k in ident_diag
                    },
                )

            squads, manager_hits, world_lists = walk_world_squads_if_needed(
                mm,
                club_short=club_short,
                squads=squads,
                manager_hits=manager_hits,
            )
            if world_lists == "empty":
                abort_world = {
                    "calibration": None if is_bin else calibrate_squad_layout(mm)
                }
            elif world_lists == "skipped_identity_known":
                progress(
                    t0,
                    phase="resolve",
                    message="Skipping world squad/staff lists — this club only",
                    pct=73,
                    layout=squad_layout,
                )

            # Employment rule (T006/T009): a managed-club employee is a jobId on
            # the club's unit squad list — FT via club-object → 7f02 join; II via
            # affiliate join; U19 via namelist. Never admit pick_tid foreign lists
            # when identity is known (non-employees poison Mentoring).
            if world_lists != "empty" and (club_short or club_id):
                ft_hit = resolve_managed_ft_for_layout(
                    mm, club_short, club_id, layout=squad_layout
                )
            fallback_jobs: list[int] | None = None
            if abort_world is None and not club_short and not club_id and squads:
                best_tid = pick_tid(squads, manager_hits)
                list_abs, count, fallback_jobs = squads[best_tid]
            selected = select_managed_ft_jobs(
                club_short,
                ft_hit,
                fallback_jobs=fallback_jobs,
                club_id=club_id,
            )
            ft_discovery_method = str(selected["method"])
            ft_list = (ft_hit or {}).get("list") if ft_hit else None
            jobs = list(selected["jobs"])
            if ft_discovery_method == "ft-club-squad-join-v1" and ft_list:
                best_tid = int(ft_list["persistTid"])
                list_abs = int(ft_list["jobsAbs"])
                count = int(ft_list["count"])
                squads[best_tid] = (list_abs, count, jobs)
            elif ft_discovery_method == "ft-club-squad-join-miss":
                best_tid = 0
                list_abs = 0
                count = 0
            # else: best_tid/list_abs/count already set from pick_tid fallback
            # (identity unknown only — never when club short or UniqueID is known)

            join_progress = ft_join_progress_fields(
                club_id, ft_hit, selected, layout=squad_layout
            )
            miss_reason = join_progress.get("missReason")
            progress(
                t0,
                phase="resolve",
                message=(
                    f"tid={best_tid} · {len(jobs)} jobIds · "
                    f"mgr={manager_hits.get(best_tid, 0)} · {ft_discovery_method}"
                    + (f" · {miss_reason}" if miss_reason else "")
                ),
                pct=74,
                jobsTarget=len(jobs),
                **join_progress,
            )

            # T086: loan object on unit jobs (same recipe FT/II/U19) before HA.
            ft_loaned: dict[int, int | None] = {}
            ii_loaned: dict[int, int | None] = {}
            u19_loaned: dict[int, int | None] = {}
            ii_hit: dict | None = None
            u19_hit: dict | None = None
            ii_jobs_listed: list[int] | None = None
            u19_jobs_listed: list[int] | None = None
            parent_club = int(club_id) if club_id else 0
            if parent_club:
                ft_loaned = loan_hits_for_unit(mm, set(jobs), parent_club)

            if club_short:
                progress(
                    t0,
                    phase="reserves",
                    message="Discovering reserves unit…",
                    pct=76,
                )
                ii_hit = resolve_ii_squad(mm, club_short)
                if ii_hit and ii_hit.get("list"):
                    ii_jobs_listed = list(ii_hit["list"]["jobs"])
                    if parent_club:
                        ii_loaned = loan_hits_for_unit(
                            mm, set(ii_jobs_listed), parent_club
                        )
                progress(
                    t0,
                    phase="u19",
                    message="Discovering youth unit…",
                    pct=78,
                )
                u19_hit = resolve_u19_squad(mm, club_short)
                if u19_hit and u19_hit.get("list"):
                    u19_jobs_listed = list(u19_hit["list"]["jobs"])
                    if parent_club:
                        u19_loaned = loan_hits_for_unit(
                            mm, set(u19_jobs_listed), parent_club
                        )

            census_units: list[dict] = [
                census_unit_row("FT", jobs, ft_loaned),
            ]
            if ii_jobs_listed is not None:
                census_units.append(
                    census_unit_row(
                        (ii_hit or {}).get("iiName") or "II",
                        ii_jobs_listed,
                        ii_loaned,
                    )
                )
            if u19_jobs_listed is not None:
                census_units.append(
                    census_unit_row(
                        (u19_hit or {}).get("u19Name") or "U19",
                        u19_jobs_listed,
                        u19_loaned,
                    )
                )
            emit_loan_census(
                t0,
                build_loan_census(
                    club_id=club_id,
                    club_name=club_name or club_short or "",
                    units=census_units,
                ),
            )

            job_uid = resolve_job_uids_batch(mm, jobs)
            progress(
                t0,
                phase="resolve",
                message="Mapped jobIds",
                pct=80,
                jobsResolved=len(job_uid),
                jobsTarget=len(jobs),
            )

            date_pick = pick_game_date_near_identity(mm, identity)
            game_date = date_pick.get("gameDate") if date_pick else None
            game_date_info = (
                {k: v for k, v in date_pick.items() if k != "candidates"}
                if date_pick
                else None
            )
            if game_date:
                progress(
                    t0,
                    phase="identity",
                    message=f"gameDate={game_date}",
                    pct=82,
                )

            players = build_players_from_jobs(
                mm,
                jobs,
                job_uid,
                names_only=names_only,
                t0=t0,
                phase="players",
            )
            apply_ft_dynamics(mm, players, list_abs, jobs)
            if parent_club:
                apply_loan_status(players, ft_loaned, parent_club=parent_club)

            if club_short:
                if ii_hit and ii_jobs_listed is not None:
                    ii_list = ii_hit["list"]
                    ii_jobs = ii_jobs_listed
                    ii_team = ii_hit.get("team")
                    progress(
                        t0,
                        phase="reserves",
                        message=f"II n={len(ii_jobs)} · resolving jobs…",
                        pct=89,
                    )
                    ii_job_uid = resolve_job_uids_batch(mm, ii_jobs)
                    ii_players = build_players_from_jobs(
                        mm,
                        ii_jobs,
                        ii_job_uid,
                        names_only=names_only,
                        t0=t0,
                        phase="reserves",
                        progress_base_pct=89,
                        progress_span_pct=4,
                    )
                    if parent_club:
                        apply_loan_status(
                            ii_players, ii_loaned, parent_club=parent_club
                        )
                    ii_capa = enrich_capa_on_players(mm, ii_players)
                    ii_general = sum(
                        1
                        for p in ii_players
                        if (p.get("attributes") or {}).get("general")
                    )
                    reserves = {
                        "iiName": ii_hit["iiName"],
                        "clubId": ii_hit["clubId"],
                        "teamId": ii_team["teamId"] if ii_team else None,
                        "listAbs": ii_list["countAbs"],
                        "countHeader": ii_list["count"],
                        "players": ii_players,
                        "capaResolved": ii_capa,
                        "discovery": {
                            "method": "ii-club-object-join-v1",
                            "catalogNameAbs": ii_hit["catalogNameAbs"],
                            "has64ff24": ii_list.get("has64ff24"),
                            "jobsResolved": len(ii_job_uid),
                        },
                    }
                    progress(
                        t0,
                        phase="reserves",
                        message=(
                            f"II {len(ii_players)} players · {ii_capa} CA/PA · "
                            f"{ii_general} general"
                        ),
                        pct=93,
                    )
                elif ii_hit:
                    reserves = {
                        "iiName": ii_hit["iiName"],
                        "clubId": ii_hit["clubId"],
                        "teamId": (ii_hit.get("team") or {}).get("teamId"),
                        "players": [],
                        "discovery": {
                            "method": "ii-club-object-join-miss",
                            "listFound": False,
                        },
                    }
                else:
                    reserves = {
                        "iiName": None,
                        "clubId": None,
                        "teamId": None,
                        "players": [],
                        "discovery": {
                            "method": "ii-unit-absent",
                            "listFound": False,
                        },
                    }

                if u19_hit and u19_jobs_listed is not None:
                    u19_list = u19_hit["list"]
                    u19_jobs = u19_jobs_listed
                    progress(
                        t0,
                        phase="u19",
                        message=f"U19 n={len(u19_jobs)} · resolving jobs…",
                        pct=95,
                    )
                    u19_job_uid = resolve_job_uids_batch(mm, u19_jobs)
                    u19_players = build_players_from_jobs(
                        mm,
                        u19_jobs,
                        u19_job_uid,
                        names_only=names_only,
                        t0=t0,
                        phase="u19",
                        progress_base_pct=95,
                        progress_span_pct=3,
                    )
                    if parent_club:
                        apply_loan_status(
                            u19_players, u19_loaned, parent_club=parent_club
                        )
                    u19_capa = enrich_capa_on_players(mm, u19_players)
                    u19_general = sum(
                        1
                        for p in u19_players
                        if (p.get("attributes") or {}).get("general")
                    )
                    u19 = {
                        "u19Name": u19_hit["u19Name"],
                        "listAbs": u19_list["countAbs"],
                        "countHeader": u19_list["count"],
                        "players": u19_players,
                        "capaResolved": u19_capa,
                        "discovery": {
                            "method": "u19-squad-namelist-v1",
                            "nameAbs": u19_hit["nameAbs"],
                            "matchMethod": u19_hit.get("method"),
                            "matchScore": u19_hit.get("matchScore"),
                            "delta": u19_list.get("delta"),
                            "listSide": (
                                "before"
                                if (u19_list.get("delta") or 0) < 0
                                else "after"
                            ),
                            "jobsResolved": len(u19_job_uid),
                        },
                    }
                    rehome_loaned_newgen_to_u19(reserves, u19)
                    progress(
                        t0,
                        phase="u19",
                        message=(
                            f"U19 {len(u19_players)} players · {u19_capa} CA/PA · "
                            f"{u19_general} general"
                        ),
                        pct=98,
                    )
                elif u19_hit:
                    u19 = {
                        "u19Name": u19_hit.get("u19Name"),
                        "players": [],
                        "discovery": {
                            "method": "u19-join-miss",
                            "listFound": False,
                        },
                    }
                else:
                    u19 = {
                        "u19Name": None,
                        "players": [],
                        "discovery": {
                            "method": "u19-unit-absent",
                            "listFound": False,
                        },
                    }
        finally:
            mm.close()

    if abort_world is not None:
        if delete_tmp:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        if is_bin:
            return fail(
                t0,
                "No squad job-lists found in pre-decompressed bin.",
                code=1,
                decompressedBytes=out_bytes,
                **container,
            )
        return fail(
            t0,
            "No squad job-lists found after decompress. "
            "Native FM26 needs calibration — paste the diagnostics below (no save names needed).",
            code=1,
            decompressedBytes=out_bytes,
            calibration=abort_world.get("calibration") or {},
            **container,
        )

    if delete_tmp:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    with_attrs = sum(
        1
        for p in players
        if (p.get("attributes") or {}).get("technical")
        or (p.get("attributes") or {}).get("physical")
    )
    with_general = sum(
        1
        for p in players
        if (p.get("attributes") or {}).get("general")
        and (p["attributes"]["general"].get("ambition") is not None
             or p["attributes"]["general"].get("adaptability") is not None)
    )
    with_det = sum(
        1
        for p in players
        if ((p.get("attributes") or {}).get("mental") or {}).get("determination")
        is not None
    )
    ranked = sorted(
        squads.keys(),
        key=lambda tid: (
            manager_hits.get(tid, 0),
            len(squads[tid][2]),
            -squads[tid][0],
        ),
        reverse=True,
    )
    result = {
        "savePath": str(save),
        "saveName": save.name,
        "clubId": club_id,
        "clubName": club_name or club_short or "",
        "clubNameShort": club_short,
        "teamId": best_tid,
        "listAbs": list_abs,
        "countHeader": count,
        "players": players,
        "reserves": reserves,
        "u19": u19,
        "discovery": {
            "squadTidCount": len(squads),
            "managerHits": {
                str(t): manager_hits[t] for t in ranked[:8] if t in manager_hits
            },
            "rankedTids": ranked[:8],
            "method": ft_discovery_method,
            "worldLists": world_lists,
            "skippedWorldLists": (
                [
                    "all-club 7f02 squad lists",
                    "manager/staff links for foreign teamIds",
                    "stadiums (never walked)",
                ]
                if world_lists == "skipped_identity_known"
                else []
            ),
            "employmentRule": (
                "jobId on managed-club unit squad list "
                "(FT: club-object→7f02; II: affiliate; U19: namelist); "
                "Squad = employed ∩ ¬loanedOut; Loans = employed ∩ loan object; "
                "Mentoring pool = Squad"
            ),
            "employmentSearch": "tail_128mb_scan",
            "ftJoin": (
                {
                    "bodyTeamId": (ft_hit.get("team") or {}).get("teamId")
                    if ft_hit
                    else None,
                    "dup": (ft_hit.get("team") or {}).get("dup") if ft_hit else None,
                    "catalogNameAbs": ft_hit.get("catalogNameAbs") if ft_hit else None,
                    "persistTid": (ft_list or {}).get("persistTid") if ft_list else None,
                    "listAbs": (ft_list or {}).get("jobsAbs") if ft_list else None,
                }
                if ft_discovery_method == "ft-club-squad-join-v1"
                else None
            ),
            "ftJoinMiss": (
                selected.get("missReason")
                if ft_discovery_method == "ft-club-squad-join-miss"
                else None
            ),
            "playersWithAttrs": with_attrs,
            "playersWithGeneral": with_general,
            "playersWithDetLea": with_det,
            "namesOnly": names_only,
            "clubId": club_id,
            "identityFound": bool(ident_diag.get("identityFound")) if ident_diag else False,
            "identitySearchBound": ident_diag.get("searchBound"),
            "identityBytesScanned": ident_diag.get("bytesScanned"),
            "identityLastTagAbs": ident_diag.get("lastTagAbs"),
            "identityTagHexes": ident_diag.get("tagHexes"),
            "gameDate": game_date_info,
            "dobStatus": (
                "dateOfBirth from personalityPackAbs-21 (dayOfYear_u16) + "
                "-19 (year_u16); null when pack missing. Separate mark+days "
                "DOB sites remain unlinked to UniqueID."
            ),
        },
        "elapsedMs": elapsed_ms,
        "decompressedBytes": out_bytes,
        "gameDate": game_date,
    }

    progress(
        t0,
        phase="done",
        message=(
            f"{len(players)} players, {with_general} general, {with_det} Det/Lea, "
            f"{with_attrs} CA"
            + (f", gameDate={game_date}" if game_date else "")
        ),
        pct=100,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if players else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as e:
        t0 = time.perf_counter()
        raise SystemExit(fail(t0, str(e), code=1))
    except Exception as e:  # noqa: BLE001
        t0 = time.perf_counter()
        raise SystemExit(
            fail(t0, f"{type(e).__name__}: {e}", code=1)
        )
