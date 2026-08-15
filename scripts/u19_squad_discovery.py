"""Locked U19 squad discovery (parent short → catalog name → colocated job-list).

Unlike II (affiliate clubId + mid-file team body), U19 youth rows keep the
subunit job-list within ~220 bytes of the lp32 team name in the mid-file
name table. The live list sits *before* the name label (list → name); a
second decoy list often sits after the short name. See
data/fixtures/u19-squad-namelist-locked.json.
"""

from __future__ import annotations

import mmap
import struct
from typing import Any

MOTIF_LIST = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"
# Youth name table on the probe lives ~55–70MB; keep a generous mid-file window.
NAME_BAND_LO = 40_000_000
NAME_BAND_HI = 120_000_000
# Live list precedes the name (Δ ≈ −120…−250). After-name lists are decoys.
# König 2040 short-row list drifted to Δ≈−229; 220 missed it and took the after-name decoy.
LIST_WINDOW_BEFORE = 400
LIST_WINDOW_AFTER = 150
FUZZY_MIN_SCORE = 70


def find_all(
    mm: mmap.mmap | bytes,
    needle: bytes,
    limit: int = 40,
    lo: int = 0,
    hi: int | None = None,
) -> list[int]:
    out: list[int] = []
    start = lo
    end = hi if hi is not None else len(mm)
    while len(out) < limit:
        j = mm.find(needle, start, end)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def read_lp32(mm: mmap.mmap | bytes, off: int) -> str | None:
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


def _parse_list_at_motif(
    mm: mmap.mmap | bytes,
    motif_abs: int,
    *,
    name_abs: int,
) -> dict[str, Any] | None:
    count_abs = motif_abs + len(MOTIF_LIST)
    if count_abs + 2 > len(mm):
        return None
    cnt = struct.unpack_from("<H", mm, count_abs)[0]
    if not (3 <= cnt <= 50):
        return None
    jobs_abs = count_abs + 2
    if jobs_abs + 4 * cnt > len(mm):
        return None
    jobs = [
        struct.unpack_from("<I", mm, jobs_abs + 4 * i)[0] for i in range(cnt)
    ]
    ok = sum(1 for jid in jobs if 50_000 <= jid <= 2_000_000)
    if ok < max(3, (cnt + 1) // 2):
        return None
    return {
        "motifAbs": motif_abs,
        "countAbs": count_abs,
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
    """Fallback: job-list within `window` bytes after the UTF-8 name.

    Often a neighbour/decoy row on current FM26 continues — prefer
    ``parse_list_before_name`` first.
    """
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
    """Live list before name, else after-name fallback."""
    return parse_list_before_name(mm, name_abs) or parse_list_after_name(
        mm, name_abs, name_len
    )


def _core_name(u19_name: str) -> str:
    return u19_name[: -len(" U19")] if u19_name.endswith(" U19") else u19_name


def match_u19_name_score(parent_short: str, u19_name: str) -> int:
    """Score how well a mid-file U19 label matches the managed parent short."""
    if not u19_name.endswith(" U19"):
        return 0
    core = _core_name(u19_name)
    if core == parent_short:
        return 100
    if core.endswith(parent_short) or parent_short.endswith(core):
        return 90
    parent_tokens = set(parent_short.lower().replace("-", " ").split())
    core_tokens = set(core.lower().replace("-", " ").split())
    if parent_tokens and parent_tokens <= core_tokens:
        return 80
    inter = len(parent_tokens & core_tokens)
    if inter:
        return 50 + inter * 10
    # Stem: Karlsruhe → Karlsruher SC
    a = parent_short.lower()
    b = core.lower()
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    if n >= 6 and n >= min(len(a), len(b)) * 0.7:
        return 70
    return 0


def discover_u19_exact(
    mm: mmap.mmap | bytes,
    parent_short: str,
    *,
    band_lo: int = NAME_BAND_LO,
    band_hi: int = NAME_BAND_HI,
) -> dict[str, Any] | None:
    """Exact lp32 match for f'{parentShort} U19' with colocated job-list."""
    u19_name = f"{parent_short} U19"
    raw = u19_name.encode("utf-8")
    hi = min(len(mm), band_hi)
    for h in find_all(mm, raw, limit=40, lo=max(0, band_lo), hi=hi):
        if h < 4:
            continue
        if struct.unpack_from("<I", mm, h - 4)[0] != len(raw):
            continue
        lst = parse_list_near_name(mm, h, len(raw))
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


def _iter_u19_names_in_band(
    mm: mmap.mmap | bytes,
    *,
    band_lo: int,
    band_hi: int,
) -> list[tuple[int, str]]:
    """Collect lp32 names ending in ' U19' inside the youth name table band."""
    out: list[tuple[int, str]] = []
    needle = b" U19"
    hi = min(len(mm), band_hi)
    for j in find_all(mm, needle, limit=800, lo=max(0, band_lo), hi=hi):
        found: tuple[int, str] | None = None
        for back in range(5, 60):
            s = read_lp32(mm, j - back)
            if s and s.endswith(" U19") and len(s.encode("utf-8")) == back:
                found = (j - back, s)
                break
        if found:
            out.append(found)
    return out


def discover_u19_fuzzy(
    mm: mmap.mmap | bytes,
    parent_short: str,
    *,
    band_lo: int = NAME_BAND_LO,
    band_hi: int = NAME_BAND_HI,
    min_score: int = FUZZY_MIN_SCORE,
) -> dict[str, Any] | None:
    """Fallback when short form differs (e.g. Karlsruhe → Karlsruher SC U19)."""
    scored: list[tuple[int, int, int, str, dict[str, Any]]] = []
    for name_abs, name in _iter_u19_names_in_band(
        mm, band_lo=band_lo, band_hi=band_hi
    ):
        score = match_u19_name_score(parent_short, name)
        if score < min_score:
            continue
        lst = parse_list_near_name(mm, name_abs, len(name.encode("utf-8")))
        if not lst:
            continue
        scored.append((score, len(name), name_abs, name, lst))
    if not scored:
        return None
    # Prefer higher score, then shorter label (short form over long form).
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
    """Parent short → U19 name (exact, else fuzzy) → colocated subunit jobs."""
    hit = discover_u19_exact(mm, parent_short)
    if hit:
        return hit
    return discover_u19_fuzzy(mm, parent_short)
