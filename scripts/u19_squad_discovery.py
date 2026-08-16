"""Youth/U19 squad join (this club's youth unit → before-name job-list).

Youth labels vary (U19 / U18 / U17 / Youth). The live list sits *before* the
name (list → name). After-name lists are decoys — not a fallback. Join is
that shape, not a megabyte band or one suffix string.
"""

from __future__ import annotations

import mmap
import sys
import struct
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ii_squad_discovery import (  # noqa: E402
    find_all,
    lp32_name_ending_at,
    match_unit_core_score,
    parse_count_jobs,
)

MOTIF_LIST = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"
# First-pass name-table hint only — not a join gate. Loan scan may still use these.
NAME_BAND_LO = 40_000_000
NAME_BAND_HI = 120_000_000
# Live list precedes the name within this window. After-name lists are decoys.
LIST_WINDOW_BEFORE = 400
LIST_WINDOW_AFTER = 150
FUZZY_MIN_SCORE = 70
YOUTH_SUFFIXES = (" U19", " U18", " U17", " Youth")


def read_lp32(mm: mmap.mmap | bytes, off: int) -> str | None:
    """Youth labels can be longer than the II catalog cap."""
    if off + 4 > len(mm):
        return None
    n = struct.unpack_from("<I", mm, off)[0]
    if not (2 <= n <= 80) or off + 4 + n > len(mm):
        return None
    raw = bytes(mm[off + 4 : off + 4 + n])
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not s or not s[0].isalpha():
        return None
    return s


def _youth_suffix(name: str) -> str | None:
    for suf in YOUTH_SUFFIXES:
        if name.endswith(suf):
            return suf
    return None


def _parse_list_at_motif(
    mm: mmap.mmap | bytes,
    motif_abs: int,
    *,
    name_abs: int,
) -> dict[str, Any] | None:
    parsed = parse_count_jobs(mm, motif_abs + len(MOTIF_LIST))
    if not parsed:
        return None
    cnt, jobs_abs, jobs = parsed
    return {
        "motifAbs": motif_abs,
        "countAbs": jobs_abs - 2,
        "jobsAbs": jobs_abs,
        "count": cnt,
        "jobs": jobs,
        "delta": motif_abs - name_abs,
    }


def parse_list_before_name(
    mm: mmap.mmap | bytes,
    name_abs: int,
    *,
    window: int = LIST_WINDOW_BEFORE,
) -> dict[str, Any] | None:
    """Parse subunit job-list within `window` bytes *before* the UTF-8 name.

    Mid-file youth table layout is list → long/short labels. Prefer the last
    motif before the name (nearest preceding list).
    """
    lo = max(0, name_abs - window)
    start = lo
    last: int | None = None
    while True:
        m = mm.find(MOTIF_LIST, start, name_abs)
        if m < 0:
            break
        last = m
        start = m + 1
    if last is None:
        return None
    return _parse_list_at_motif(mm, last, name_abs=name_abs)


def parse_list_after_name(
    mm: mmap.mmap | bytes,
    name_abs: int,
    name_len: int,
    *,
    window: int = LIST_WINDOW_AFTER,
) -> dict[str, Any] | None:
    """After-name job-list — decoy/neighbour. Not the live youth list."""
    after = name_abs + name_len
    hi = min(len(mm), after + window)
    m = mm.find(MOTIF_LIST, after, hi)
    if m < 0:
        return None
    return _parse_list_at_motif(mm, m, name_abs=name_abs)


def parse_list_near_name(
    mm: mmap.mmap | bytes,
    name_abs: int,
    name_len: int,
) -> dict[str, Any] | None:
    """Live list is before the name. After-name is a decoy — do not take it."""
    del name_len
    return parse_list_before_name(mm, name_abs)


def _core_name(youth_name: str) -> str:
    suf = _youth_suffix(youth_name)
    if suf is None:
        return youth_name
    return youth_name[: -len(suf)]


def match_u19_name_score(parent_short: str, u19_name: str) -> int:
    """Score how well a mid-file youth label matches the managed parent short."""
    if _youth_suffix(u19_name) is None:
        return 0
    return match_unit_core_score(parent_short, _core_name(u19_name))


def _name_search_spans(mm: mmap.mmap | bytes) -> list[tuple[int, int]]:
    n = len(mm)
    if n > NAME_BAND_LO:
        spans = [(max(0, NAME_BAND_LO), min(n, NAME_BAND_HI))]
        spans.append((0, NAME_BAND_LO))
        if n > NAME_BAND_HI:
            spans.append((NAME_BAND_HI, n))
        return spans
    return [(0, n)]


def discover_u19_exact(
    mm: mmap.mmap | bytes,
    parent_short: str,
    *,
    band_lo: int | None = None,
    band_hi: int | None = None,
) -> dict[str, Any] | None:
    """Exact lp32 match for parent + youth suffix with a before-name job-list."""
    if band_lo is None and band_hi is None:
        spans = _name_search_spans(mm)
    else:
        lo = 0 if band_lo is None else max(0, band_lo)
        hi = len(mm) if band_hi is None else min(len(mm), band_hi)
        spans = [(lo, hi)]
    for suf in YOUTH_SUFFIXES:
        u19_name = f"{parent_short}{suf}"
        raw = u19_name.encode("utf-8")
        for lo, hi in spans:
            for h in find_all(mm, raw, limit=40, lo=lo, hi=hi):
                if h < 4:
                    continue
                if struct.unpack_from("<I", mm, h - 4)[0] != len(raw):
                    continue
                lst = parse_list_before_name(mm, h)
                if not lst:
                    continue
                return {
                    "parentShort": parent_short,
                    "u19Name": u19_name,
                    "nameAbs": h,
                    "method": "exact",
                    "matchScore": 100,
                    "list": lst,
                }
    return None


def _iter_youth_names(
    mm: mmap.mmap | bytes,
    *,
    band_lo: int,
    band_hi: int,
) -> list[tuple[int, str]]:
    """Collect lp32 names ending in a youth suffix."""
    out: list[tuple[int, str]] = []
    hi = min(len(mm), band_hi)
    for suf in YOUTH_SUFFIXES:
        needle = suf.encode("utf-8")
        for j in find_all(mm, needle, limit=800, lo=max(0, band_lo), hi=hi):
            found = lp32_name_ending_at(mm, j, suf)
            if found:
                out.append(found)
    return out


def discover_u19_fuzzy(
    mm: mmap.mmap | bytes,
    parent_short: str,
    *,
    band_lo: int | None = None,
    band_hi: int | None = None,
    min_score: int = FUZZY_MIN_SCORE,
) -> dict[str, Any] | None:
    """Fallback when short form differs (long youth label vs parent short)."""
    if band_lo is None and band_hi is None:
        spans = _name_search_spans(mm)
    else:
        lo = 0 if band_lo is None else max(0, band_lo)
        hi = len(mm) if band_hi is None else min(len(mm), band_hi)
        spans = [(lo, hi)]
    scored: list[tuple[int, int, int, str, dict[str, Any]]] = []
    seen: set[int] = set()
    for lo, hi in spans:
        for name_abs, name in _iter_youth_names(mm, band_lo=lo, band_hi=hi):
            if name_abs in seen:
                continue
            seen.add(name_abs)
            score = match_u19_name_score(parent_short, name)
            if score < min_score:
                continue
            lst = parse_list_before_name(mm, name_abs)
            if not lst:
                continue
            scored.append((score, len(name), name_abs, name, lst))
    if not scored:
        return None
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))
    score, _nlen, name_abs, name, lst = scored[0]
    return {
        "parentShort": parent_short,
        "u19Name": name,
        "nameAbs": name_abs,
        "method": "fuzzy",
        "matchScore": score,
        "list": lst,
    }


def resolve_u19_squad(
    mm: mmap.mmap | bytes,
    parent_short: str,
) -> dict[str, Any] | None:
    """Parent short → this club's youth unit → before-name subunit jobs."""
    hit = discover_u19_exact(mm, parent_short)
    if hit:
        return hit
    return discover_u19_fuzzy(mm, parent_short)
