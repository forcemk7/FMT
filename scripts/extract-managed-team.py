#!/usr/bin/env python3
"""
Managed club identity from a career .fm save.

Locked path (continue + native FM26):
  1) Tag 00 95 0e 01|02 → manager lp32 → club short lp32 → club UniqueID u32
  2) Optional catalog: long/short name pair for the official club name

EARLY_SCAN / IDENTITY_DEADLINE are first-pass bounds, not a save's byte as law.
If the tag sits later, search continues. Miss = diagnostic (tags / offset /
bytes scanned), not a silent wrong club.

Stops as soon as identity (+ optional catalog name) is resolved — no squad-list
scan in this phase (First Team teamId / players come later).
"""

from __future__ import annotations

import json
import struct
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import zstandard as zstd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHUNK = 2 * 1024 * 1024
ZSTD_MAGIC = bytes.fromhex("28b52ffd")
HUMAN_TAGS = (
    bytes.fromhex("00950e01"),  # native FM26
    bytes.fromhex("00950e02"),  # FM24→FM26 continue
)

EARLY_SCAN = 500_000
IDENTITY_DEADLINE = 2 * 1024 * 1024
# Give-up cap after expanding past the deadline — a bound, not a save offset.
IDENTITY_SCAN_MAX = 64 * 1024 * 1024
CATALOG_LO = 500_000
CATALOG_TARGET = 12 * 1024 * 1024
CALIB_DUMP = ROOT / "tmp" / "calib" / "early-last.bin"
CALIB_META = ROOT / "tmp" / "calib" / "early-last.json"
IDENTITY_DUMP_DIR = ROOT / "tmp" / "identity"
# Neighborhood dump only — pick is UniqueID-tail u16 doy + u16 year (T099), not 24MB c708.
IDENTITY_DATE_WINDOW = 64 * 1024
IDENTITY_HEX_RADIUS = 256
DATE_EPOCH = date(1900, 1, 1)
GAME_DATE_PRELUDE = bytes.fromhex("c708000000")
# Valid in-game years for the UniqueID-tail u16. Not a fitted club/day.
DATE_YEAR_LO, DATE_YEAR_HI = 2020, 2050
DAYS_Y1900_LO, DAYS_Y1900_HI = 40_000, 60_000


def progress(t0: float, **fields) -> None:
    payload = {"elapsedMs": int((time.perf_counter() - t0) * 1000), **fields}
    print(f"PROGRESS {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr, flush=True)


def fail(t0: float, message: str, *, code: int = 1, **diagnostics) -> int:
    progress(t0, phase="error", message=message, pct=100, **diagnostics)
    print(
        json.dumps({"error": message, "diagnostics": diagnostics}, ensure_ascii=False),
        flush=True,
    )
    return code


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


def parse_cli(argv: list[str] | None = None) -> tuple[Path | None, Path | None]:
    """Return (save_path or None, dump_path override or None)."""
    args = list(sys.argv[1:] if argv is None else argv)
    save: Path | None = None
    dump: Path | None = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--dump":
            nxt = args[i + 1] if i + 1 < len(args) else None
            if nxt and not nxt.startswith("-") and not nxt.lower().endswith(".fm"):
                dump = Path(nxt)
                i += 2
                continue
            i += 1
            continue
        if a.startswith("-"):
            raise SystemExit(f"Unknown flag: {a}")
        save = Path(a)
        i += 1
    return save, dump


def resolve_save(cli_save: Path | None) -> Path:
    if cli_save is not None:
        p = cli_save
        if not p.is_file():
            raise SystemExit(f"Save not found: {p}")
        refuse_live_fm_games_save(p)
        return p
    saves = sorted(
        Path(ROOT, "data", "saves").glob("*.fm"),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    if not saves:
        raise SystemExit("No .fm in data/saves")
    refuse_live_fm_games_save(saves[0])
    return saves[0]


def probe_zstd_offset(save: Path) -> tuple[int | None, dict]:
    head = save.read_bytes()[:64]
    info: dict = {
        "saveBytes": save.stat().st_size,
        "magicAscii": head[:4].decode("latin-1", errors="replace"),
    }
    if len(head) > 30 and head[26:30] == ZSTD_MAGIC:
        info["inferredLayout"] = "fm24_continue_style_zstd_at_26"
        return 26, info
    j = head.find(ZSTD_MAGIC)
    if j >= 0:
        info["inferredLayout"] = f"zstd_at_{j}"
        return j, info
    info["inferredLayout"] = "unknown"
    return None, info


def read_lp32(buf, off: int) -> str | None:
    if off < 0 or off + 4 > len(buf):
        return None
    n = struct.unpack_from("<I", buf, off)[0]
    if not (2 <= n <= 64) or off + 4 + n > len(buf):
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


def _looks_comp_name(s: str) -> bool:
    low = s.lower()
    return any(
        k in low
        for k in (
            "liga",
            "league",
            "division",
            "premier",
            "serie",
            "bundes",
            "championship",
            "cup",
            "divisi",
            "wsl",
        )
    )


def _looks_person_name(s: str) -> bool:
    return 3 <= len(s) <= 48 and s[0].isalpha() and not _looks_comp_name(s)


def _looks_club_short(s: str) -> bool:
    return 3 <= len(s) <= 48 and s[0].isalpha() and not _looks_comp_name(s)


def discover_managed_club(buf, limit: int = EARLY_SCAN) -> dict | None:
    """
    00 95 0e 01|02 + manager + club short + club UniqueID (u32).
    Searches [0, limit). Callers expand limit if this returns None.
    """
    hi = min(limit, len(buf))
    best: dict | None = None
    for tag in HUMAN_TAGS:
        start = 0
        while start + 12 < hi:
            j = buf.find(tag, start, hi)
            if j < 0:
                break
            off = j + len(tag)
            person = read_lp32(buf, off)
            if not person or not _looks_person_name(person):
                start = j + 1
                continue
            n1 = struct.unpack_from("<I", buf, off)[0]
            o2 = off + 4 + n1
            club = read_lp32(buf, o2)
            if not club or not _looks_club_short(club):
                start = j + 1
                continue
            n2 = struct.unpack_from("<I", buf, o2)[0]
            id_off = o2 + 4 + n2
            if id_off + 4 > len(buf):
                start = j + 1
                continue
            club_id = struct.unpack_from("<I", buf, id_off)[0]
            if club_id in (0, 0xFFFFFFFF) or club_id > 3_000_000_000:
                start = j + 1
                continue
            score = 0
            if " " in person:
                score += 2
            if person.lower().startswith(("mr ", "mrs ", "ms ", "dr ")):
                score += 2
            if 1 <= club_id <= 100_000:
                score += 1
            cand = {
                "managerName": person,
                "clubNameShort": club,
                "clubId": club_id,
                "identityAbs": off,
                "clubIdAbs": id_off,
                "tagHex": tag.hex(),
                "score": score,
                "method": "human_tag_club_uid",
            }
            if best is None or cand["score"] > best["score"]:
                best = cand
            start = j + 1
    return best


def identity_scan_diagnostics(buf, limit: int) -> dict:
    """Tag hit counts / offsets for a miss — not a guessed club."""
    hi = min(max(0, int(limit)), len(buf))
    tags: dict[str, dict] = {}
    last_tag_abs: int | None = None
    for tag in HUMAN_TAGS:
        first: int | None = None
        count = 0
        start = 0
        while start + len(tag) <= hi:
            j = buf.find(tag, start, hi)
            if j < 0:
                break
            count += 1
            if first is None:
                first = j
            last_tag_abs = j if last_tag_abs is None else max(last_tag_abs, j)
            start = j + 1
        tags[tag.hex()] = {"count": count, "firstAbs": first}
    return {
        "bytesScanned": hi,
        "tags": tags,
        "lastTagAbs": last_tag_abs,
        "tagHexes": [t.hex() for t in HUMAN_TAGS],
    }


def try_discover_managed_club(
    buf,
    *,
    limits: tuple[int, ...] | None = None,
) -> tuple[dict | None, dict]:
    """Expanding bounds. First bound that parses wins. Deadline is not fail."""
    n = len(buf)
    raw = limits if limits is not None else (EARLY_SCAN, IDENTITY_DEADLINE, n)
    seen: list[int] = []
    for x in raw:
        b = min(n, max(0, int(x)))
        if not seen or b > seen[-1]:
            seen.append(b)
    hit: dict | None = None
    bound = seen[-1] if seen else 0
    for bound in seen:
        hit = discover_managed_club(buf, bound)
        if hit:
            break
    scan_hi = bound if hit else (seen[-1] if seen else 0)
    diag = identity_scan_diagnostics(buf, scan_hi)
    diag["searchBound"] = bound
    diag["identityFound"] = hit is not None
    if hit:
        diag["tagHex"] = hit.get("tagHex")
        diag["identityAbs"] = hit.get("identityAbs")
    return hit, diag


def days_y1900_to_iso(days: int) -> str | None:
    try:
        dt = DATE_EPOCH + timedelta(days=int(days))
    except Exception:
        return None
    if not (1900 <= dt.year <= 2100):
        return None
    return dt.isoformat()


def doy_year_to_iso(doy: int, year: int) -> str | None:
    """date(year, 1, 1) + (doy - 1). Invalid doy/year → None (UI —)."""
    y = int(year)
    n = int(doy)
    if not (DATE_YEAR_LO <= y <= DATE_YEAR_HI):
        return None
    if not (1 <= n <= 366):
        return None
    try:
        dt = date(y, 1, 1) + timedelta(days=n - 1)
    except Exception:
        return None
    if dt.year != y:
        return None
    return dt.isoformat()


def _dense_calendar_days(days_hits: set[int]) -> set[int]:
    """Consecutive prelude days of length ≥5 — a calendar table, not today."""
    if not days_hits:
        return set()
    ordered = sorted(days_hits)
    table: set[int] = set()
    run = [ordered[0]]
    for d in ordered[1:]:
        if d == run[-1] + 1:
            run.append(d)
        else:
            if len(run) >= 5:
                table.update(run)
            run = [d]
    if len(run) >= 5:
        table.update(run)
    return table


def collect_date_candidates(buf, lo: int, hi: int) -> list[dict]:
    """Prelude + today_ptr hits in [lo, hi). Does not pick a date."""
    lo = max(0, int(lo))
    hi = min(len(buf), int(hi))
    out: list[dict] = []
    start = lo
    while True:
        j = buf.find(GAME_DATE_PRELUDE, start, hi)
        if j < 0:
            break
        off = j + len(GAME_DATE_PRELUDE)
        if off + 12 > hi:
            break
        days = struct.unpack_from("<I", buf, off)[0]
        if DAYS_Y1900_LO <= days <= DAYS_Y1900_HI:
            a = struct.unpack_from("<I", buf, off + 4)[0]
            b = struct.unpack_from("<I", buf, off + 8)[0]
            if a == b and a > 255:
                iso = days_y1900_to_iso(days)
                if iso and DATE_YEAR_LO <= int(iso[:4]) <= DATE_YEAR_HI:
                    nearby = bytes(buf[max(lo, j - 8) : min(hi, off + 16)])
                    out.append(
                        {
                            "kind": "prelude",
                            "iso": iso,
                            "daysY1900": days,
                            "abs": j,
                            "nearbyHex": nearby.hex(),
                        }
                    )
        start = j + 1

    days_seen = {c["daysY1900"] for c in out}
    for days in sorted(days_seen):
        needle = struct.pack("<II", days - 1, days) + b"\x00\x00\x00\x00"
        p = lo
        while True:
            j = buf.find(needle, p, hi)
            if j < 0:
                break
            iso = days_y1900_to_iso(days)
            nearby = bytes(buf[max(lo, j - 8) : min(hi, j + len(needle) + 8)])
            out.append(
                {
                    "kind": "today_ptr",
                    "iso": iso,
                    "daysY1900": days,
                    "abs": j,
                    "nearbyHex": nearby.hex(),
                }
            )
            p = j + 1
    out.sort(key=lambda c: (c["abs"], c["kind"]))
    return out


def pick_game_date_near_identity(buf, identity: dict | None) -> dict | None:
    """
    In-game date from the UniqueID tail (T099).

    After club UniqueID u32: u16 LE raw at UniqueID+4, u16 LE year at UniqueID+6.
    ``doy = raw`` if 1..366 else ``raw & 0x1FF``.
    ``date(year, 1, 1) + (doy - 1)``. Not packed day/month. Not 24MB ``c708``.
    Invalid doy/year → None.
    """
    if not identity:
        return None
    abs0 = int(identity.get("identityAbs") or 0)
    club_id_abs = int(identity.get("clubIdAbs") or abs0)
    tail = club_id_abs + 4
    lo = max(0, abs0 - IDENTITY_DATE_WINDOW)
    hi = min(len(buf), abs0 + IDENTITY_DATE_WINDOW)
    neighborhood = collect_date_candidates(buf, lo, hi)
    empty = {
        "gameDate": None,
        "daysY1900": None,
        "abs": None,
        "method": "identity_unsure",
        "candidates": neighborhood,
        "windowLo": lo,
        "windowHi": hi,
        "doy": None,
        "year": None,
        "tailAbs": tail,
        "tailHex": None,
    }
    if tail + 4 > len(buf):
        return empty
    raw, year = struct.unpack_from("<HH", buf, tail)
    doy = raw if 1 <= raw <= 366 else (raw & 0x1FF)
    iso = doy_year_to_iso(doy, year)
    tail_bytes = bytes(buf[tail : tail + 4])
    tail_cand = {
        "kind": "uniqueid_tail_doy_year",
        "iso": iso,
        "doy": doy,
        "year": year,
        "abs": tail,
        "nearbyHex": tail_bytes.hex(),
    }
    cands = [tail_cand, *neighborhood]
    if not iso:
        empty["candidates"] = cands
        empty["doy"] = doy
        empty["year"] = year
        empty["tailHex"] = tail_bytes.hex()
        return empty
    dt = date.fromisoformat(iso)
    return {
        "gameDate": iso,
        "daysY1900": (dt - DATE_EPOCH).days,
        "abs": tail,
        "method": "uniqueid_tail_doy_year",
        "candidates": cands,
        "windowLo": lo,
        "windowHi": hi,
        "doy": doy,
        "year": year,
        "tailAbs": tail,
        "tailHex": tail_bytes.hex(),
    }


def _hexdump(buf, start: int, end: int, width: int = 16) -> list[str]:
    start = max(0, start)
    end = min(len(buf), end)
    lines: list[str] = []
    off = start - (start % width)
    while off < end:
        chunk = bytes(buf[off : min(off + width, len(buf))])
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        marker = ">>" if start <= off < end else "  "
        lines.append(f"{marker}{off:08x}  {hexpart:<{width * 3}} {ascii_part}")
        off += width
    return lines


def _printable_strings(buf, start: int, end: int, min_len: int = 4) -> list[str]:
    start = max(0, start)
    end = min(len(buf), end)
    raw = bytes(buf[start:end])
    out: list[str] = []
    cur: list[int] = []
    cur_at = 0
    for i, b in enumerate(raw):
        if 32 <= b < 127:
            if not cur:
                cur_at = start + i
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append(f"{cur_at:08x}  {bytes(cur).decode('ascii')}")
            cur = []
    if len(cur) >= min_len:
        out.append(f"{cur_at:08x}  {bytes(cur).decode('ascii')}")
    return out


def format_identity_report(
    *,
    save: Path,
    buf,
    container: dict,
    identity: dict | None,
    ident_diag: dict,
    club_long: str | None,
    date_info: dict | None,
) -> str:
    lines: list[str] = []
    lines.append("# FMT identity dump (T097)")
    lines.append(f"saveName: {save.name}")
    lines.append(f"saveBytes: {save.stat().st_size if save.is_file() else 'n/a'}")
    lines.append(f"decompressedBytes: {len(buf)}")
    for k in ("inferredLayout", "zstdOffset", "saveBytes"):
        if k in container:
            lines.append(f"{k}: {container[k]}")
    lines.append("")
    lines.append("## Identity")
    if identity:
        lines.append(f"tagHex: {identity.get('tagHex')}")
        lines.append(f"identityAbs: {identity.get('identityAbs')}")
        lines.append(f"clubIdAbs: {identity.get('clubIdAbs')}")
        lines.append(f"managerName: {identity.get('managerName')}")
        lines.append(f"clubNameShort: {identity.get('clubNameShort')}")
        lines.append(f"clubId: {identity.get('clubId')}")
        lines.append(f"clubName: {club_long or identity.get('clubNameShort')}")
        lines.append(f"method: {identity.get('method')}")
    else:
        lines.append("identity: (not found)")
        lines.append(f"bytesScanned: {ident_diag.get('bytesScanned')}")
        lines.append(f"searchBound: {ident_diag.get('searchBound')}")
        lines.append(f"tags: {ident_diag.get('tags')}")
        lines.append(f"lastTagAbs: {ident_diag.get('lastTagAbs')}")
    lines.append("")
    picked = (date_info or {}).get("gameDate")
    lines.append("## Game date")
    lines.append(f"gameDate: {picked if picked else '—'}")
    lines.append(f"method: {(date_info or {}).get('method') or 'none'}")
    lines.append(f"doy: {(date_info or {}).get('doy')}")
    lines.append(f"year: {(date_info or {}).get('year')}")
    lines.append(f"tailAbs: {(date_info or {}).get('tailAbs')}")
    lines.append(f"tailHex: {(date_info or {}).get('tailHex')}")
    lines.append(
        "rule: after UniqueID u32, u16 LE doy at +4 then u16 LE year at +6; "
        "doy=raw if 1..366 else raw&0x1FF; date(year, 1, 1)+(doy-1). "
        "Not day/month. Invalid doy/year → —"
    )
    lines.append("")
    lines.append("## Date candidates (iso, days-from-1900, offset, kind, nearby bytes)")
    cands = (date_info or {}).get("candidates") or []
    if not cands:
        abs0 = int((identity or {}).get("identityAbs") or 0)
        lo = max(0, abs0 - IDENTITY_DATE_WINDOW)
        hi = min(
            len(buf),
            abs0 + IDENTITY_DATE_WINDOW if abs0 else min(len(buf), IDENTITY_DATE_WINDOW),
        )
        cands = collect_date_candidates(buf, lo, hi)
    if not cands:
        lines.append("(none in identity neighborhood)")
    for c in cands:
        lines.append(
            f"- iso={c.get('iso')}  daysY1900={c.get('daysY1900')}  "
            f"abs={c.get('abs')}  kind={c.get('kind')}  nearby={c.get('nearbyHex')}"
        )
    lines.append("")
    abs0 = int((identity or {}).get("identityAbs") or 0)
    club_id_abs = int((identity or {}).get("clubIdAbs") or abs0)
    lines.append("## Hex around identity")
    if identity:
        lines.append(f"(identityAbs {abs0} ±{IDENTITY_HEX_RADIUS})")
        lines.extend(_hexdump(buf, abs0 - IDENTITY_HEX_RADIUS, abs0 + IDENTITY_HEX_RADIUS))
        lines.append("")
        lines.append(f"(clubIdAbs {club_id_abs} ±64)")
        lines.extend(_hexdump(buf, club_id_abs - 64, club_id_abs + 64))
        lines.append("")
        lines.append("## UniqueID tail (u8 + u8 doy + u16 LE year)")
        tail = club_id_abs + 4
        if tail + 16 <= len(buf):
            u16s = struct.unpack_from("<HHHHHHHH", buf, tail)
            u32s = struct.unpack_from("<IIII", buf, tail)
            lines.append(
                "u16: " + " ".join(f"{v}(0x{v:04x})" for v in u16s)
            )
            lines.append(
                "u32: " + " ".join(f"{v}(0x{v:08x})" for v in u32s)
            )
            for i, v in enumerate(u16s):
                if DATE_YEAR_LO <= v <= DATE_YEAR_HI:
                    doy_at = tail + i * 2 - 1
                    doy = buf[doy_at] if doy_at >= 0 else None
                    iso = doy_year_to_iso(doy, v) if doy is not None else None
                    lines.append(
                        f"u16[{i}] year={v} @ {tail + i * 2}  "
                        f"doy_before={doy}  iso={iso or '—'}"
                    )
            for i, v in enumerate(u32s):
                iso = days_y1900_to_iso(v) if DAYS_Y1900_LO <= v <= DAYS_Y1900_HI else None
                if iso and DATE_YEAR_LO <= int(iso[:4]) <= DATE_YEAR_HI:
                    lines.append(
                        f"u32[{i}] days-from-1900 candidate: {iso} ({v}) @ {tail + i * 4}"
                    )
        else:
            lines.append("(tail truncated)")
    else:
        lines.append("(no identity hit — first 512 decompressed bytes)")
        lines.extend(_hexdump(buf, 0, min(len(buf), 512)))
    lines.append("")
    lines.append("## Printable strings around identity")
    str_lo = max(0, abs0 - IDENTITY_HEX_RADIUS * 2) if identity else 0
    str_hi = min(len(buf), (abs0 + IDENTITY_HEX_RADIUS * 2) if identity else 2048)
    strs = _printable_strings(buf, str_lo, str_hi)
    if not strs:
        lines.append("(none)")
    else:
        lines.extend(strs)
    lines.append("")
    return "\n".join(lines) + "\n"


def write_identity_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _path_for_json(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p)


def catalog_long_name(
    buf, club_short: str, *, scan_lo: int = CATALOG_LO, scan_hi: int | None = None
) -> tuple[str | None, dict]:
    """Best-effort official long name from catalog long/short pair."""
    raw = club_short.encode("utf-8")
    diag: dict = {"catalogShortHits": 0, "catalogPairHits": 0}
    start = max(0, scan_lo)
    end = min(len(buf), scan_hi if scan_hi is not None else CATALOG_TARGET)
    while start < end:
        j = buf.find(raw, start, end)
        if j < 0:
            break
        diag["catalogShortHits"] += 1
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
                if (
                    club_short not in long
                    and long.replace("FC ", "") != club_short
                    and long != club_short
                ):
                    continue
                # Prefer longer official names (FC X / X City).
                if len(long) >= len(club_short):
                    diag["catalogPairHits"] += 1
                    diag["catalogAbs"] = long_off
                    return long, diag
        start = j + 1
    return None, diag


def write_calib_dump(buf, meta: dict) -> None:
    try:
        CALIB_DUMP.parent.mkdir(parents=True, exist_ok=True)
        CALIB_DUMP.write_bytes(bytes(buf[: min(len(buf), IDENTITY_DEADLINE)]))
        CALIB_META.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def main() -> int:
    cli_save, dump_override = parse_cli()
    save = resolve_save(cli_save)
    t0 = time.perf_counter()
    zstd_off, container = probe_zstd_offset(save)
    progress(
        t0,
        phase="start",
        message=f"Opening {save.name}",
        pct=0,
        **container,
        zstdOffset=zstd_off,
    )
    if zstd_off is None:
        return fail(t0, "No zstd stream found in .fm header.", **container)

    buf = bytearray()
    identity: dict | None = None
    ident_diag: dict = {}
    club_long: str | None = None
    cat_diag: dict = {}
    zstd_exc: str | None = None
    last_prog = 0
    scan_cap = max(CATALOG_TARGET, IDENTITY_SCAN_MAX)
    dump_path = dump_override if dump_override is not None else (
        IDENTITY_DUMP_DIR / f"{save.stem}.txt"
    )
    if not dump_path.is_absolute():
        dump_path = ROOT / dump_path

    def emit_dump(date_info: dict | None = None) -> None:
        try:
            text = format_identity_report(
                save=save,
                buf=buf,
                container=container,
                identity=identity,
                ident_diag=ident_diag,
                club_long=club_long,
                date_info=date_info,
            )
            write_identity_report(dump_path, text)
        except OSError:
            pass

    with save.open("rb") as f:
        f.seek(int(zstd_off))
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while len(buf) < scan_cap:
                try:
                    block = reader.read(CHUNK)
                except zstd.ZstdError as e:
                    zstd_exc = str(e)
                    if not buf:
                        emit_dump()
                        return fail(
                            t0,
                            f"zstd decompress failed (empty output): {e}. "
                            "If this was an upload, the file may be truncated — retry the upload.",
                            **container,
                        )
                    break
                if not block:
                    break
                buf.extend(block)

                if len(buf) - last_prog >= CHUNK:
                    last_prog = len(buf)
                    progress(
                        t0,
                        phase="decompress",
                        message="Decompressing (club identity)",
                        pct=min(80, int(80 * len(buf) / scan_cap)),
                        outBytes=len(buf),
                    )

                if identity is None:
                    identity, ident_diag = try_discover_managed_club(
                        buf,
                        limits=(EARLY_SCAN, IDENTITY_DEADLINE, len(buf)),
                    )
                    if identity:
                        progress(
                            t0,
                            phase="resolve",
                            message=(
                                f"club={identity['clubNameShort']} "
                                f"id={identity['clubId']}"
                            ),
                            pct=50,
                            outBytes=len(buf),
                            searchBound=ident_diag.get("searchBound"),
                        )

                if identity and club_long is None and len(buf) >= max(CATALOG_LO, 2 << 20):
                    club_long, cat_diag = catalog_long_name(
                        buf, identity["clubNameShort"]
                    )
                    if club_long:
                        progress(
                            t0,
                            phase="resolve",
                            message=f"catalog={club_long}",
                            pct=90,
                            outBytes=len(buf),
                        )

                date_hi = (
                    int(identity["identityAbs"]) + IDENTITY_DATE_WINDOW
                    if identity
                    else 0
                )
                if identity and club_long and len(buf) >= date_hi:
                    break
                if identity and len(buf) >= max(CATALOG_TARGET, date_hi):
                    break
                if identity is None and len(buf) >= IDENTITY_SCAN_MAX:
                    break
        finally:
            reader.close()

    date_info = pick_game_date_near_identity(buf, identity)
    emit_dump(date_info)

    if identity is None:
        if not ident_diag:
            ident_diag = identity_scan_diagnostics(buf, len(buf))
            ident_diag["searchBound"] = len(buf)
            ident_diag["identityFound"] = False
        write_calib_dump(buf, {"saveName": save.name, **container, **ident_diag})
        return fail(
            t0,
            "No managed-club identity (human tag → club UniqueID).",
            decompressedBytes=len(buf),
            calibDump=str(CALIB_DUMP.relative_to(ROOT)),
            identityDump=_path_for_json(dump_path),
            **container,
            **ident_diag,
        )

    if club_long is None:
        club_long, cat_diag = catalog_long_name(buf, identity["clubNameShort"])

    club_short = identity["clubNameShort"]
    club_id = identity["clubId"]
    club_name = club_long or club_short
    game_date = date_info.get("gameDate") if date_info else None

    result = {
        "savePath": str(save),
        "saveName": save.name,
        # Club Site UniqueID (primary).
        "clubId": club_id,
        # Alias kept for existing UI/store wiring.
        "teamId": club_id,
        "clubName": club_name,
        "clubNameShort": club_short,
        "gameDate": game_date,
        "players": [],
        "metaOnly": True,
        "discovery": {
            "method": identity["method"],
            "tagHex": identity["tagHex"],
            "identityAbs": identity["identityAbs"],
            "clubIdAbs": identity["clubIdAbs"],
            "managerNameLen": len(identity["managerName"]),
            "earlyStop": True,
            "identityFound": True,
            "searchBound": ident_diag.get("searchBound"),
            "bytesScanned": ident_diag.get("bytesScanned"),
            "gameDateMethod": (date_info or {}).get("method"),
            "gameDateAbs": (date_info or {}).get("abs"),
            "identityDump": _path_for_json(dump_path),
            **cat_diag,
            "zstdNote": zstd_exc,
        },
        "elapsedMs": int((time.perf_counter() - t0) * 1000),
        "decompressedBytes": len(buf),
        **container,
    }
    progress(
        t0,
        phase="done",
        message=f"clubId={club_id} · {club_name}"
        + (f" · gameDate={game_date}" if game_date else " · gameDate=—"),
        pct=100,
    )
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
