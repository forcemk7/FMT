"""Reserves/II squad join (this club's team object → job-list).

Catalog PRE_NAME → teamId/dup → team-body subunit list. Reserve unit names
vary by nation (II / B / U21 / …). Missing unit in FM = empty, not a failed
extract. Join is object shape, not a megabyte band or one suffix string.
"""

from __future__ import annotations

import mmap
import struct
from collections.abc import Iterator
from typing import Any

SENTINELS = frozenset({0, 1, 255, 256, 65535, 65536, 0xFFFFFFFF})
AFTER_MARKER = bytes.fromhex("0000ffffffff00000100")
CLUB_ID_REL = 23
PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")
MOTIF_LIST = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"
# Catalog search hint only — not a join gate. Miss expands to the whole blob.
CATALOG_HINT = 30_000_000
JOB_LO, JOB_HI = 100, 50_000_000
SQUAD_COUNT_LO, SQUAD_COUNT_HI = 1, 80
# First-pass dup-pair bound only — expand; not a hard 200.
BODY_HIT_LIMIT = 200
RESERVE_SUFFIXES = (
    " II",
    " B",
    " U21",
    " U23",
    " Reserves",
    " Reserve",
    " Amateure",
)


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


def iter_hits(
    mm: mmap.mmap | bytes,
    needle: bytes,
    *,
    lo: int = 0,
    hi: int | None = None,
    batch: int = BODY_HIT_LIMIT,
) -> Iterator[int]:
    """Yield every needle offset. `batch` expands; it is not a hard cap."""
    start = lo
    end = hi if hi is not None else len(mm)
    limit = max(1, int(batch))
    while start < end:
        chunk = find_all(mm, needle, limit=limit, lo=start, hi=end)
        if not chunk:
            break
        yield from chunk
        if len(chunk) < limit:
            break
        start = chunk[-1] + 1
        limit *= 4


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


def jobs_majority_plausible(jobs: list[int]) -> bool:
    if not jobs:
        return False
    ok = sum(1 for jid in jobs if JOB_LO <= jid <= JOB_HI and jid)
    return ok >= max(1, (len(jobs) + 1) // 2)


def parse_count_jobs(
    mm: mmap.mmap | bytes, count_abs: int
) -> tuple[int, int, list[int]] | None:
    if count_abs + 2 > len(mm):
        return None
    cnt = struct.unpack_from("<H", mm, count_abs)[0]
    if not (SQUAD_COUNT_LO <= cnt <= SQUAD_COUNT_HI):
        return None
    jobs_abs = count_abs + 2
    if jobs_abs + 4 * cnt > len(mm):
        return None
    jobs = [
        struct.unpack_from("<I", mm, jobs_abs + 4 * i)[0] for i in range(cnt)
    ]
    if not jobs_majority_plausible(jobs):
        return None
    return cnt, jobs_abs, jobs


def match_team_body(
    mm: mmap.mmap | bytes, dup_abs: int, team_id: int
) -> int | None:
    """Object shape: teamId | 00×10 | mid | dup×2 | 0a. Returns tid_abs or None."""
    tid_abs = dup_abs - 18
    if tid_abs < 0:
        return None
    if struct.unpack_from("<I", mm, tid_abs)[0] != team_id:
        return None
    if bytes(mm[tid_abs + 4 : tid_abs + 14]) != bytes(10):
        return None
    if dup_abs + 8 >= len(mm) or mm[dup_abs + 8] != 0x0A:
        return None
    return tid_abs


def plausible_club_id(cid: int) -> bool:
    return 100 <= cid <= 50_000 and cid not in SENTINELS


def _reserve_suffix(name: str) -> str | None:
    for suf in RESERVE_SUFFIXES:
        if name.endswith(suf):
            return suf
    return None


def match_unit_core_score(parent_short: str, core: str) -> int:
    if not parent_short or not core:
        return 0
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


def match_reserve_name_score(parent_short: str, name: str) -> int:
    """Score a reserve catalog name against the managed parent short (II / B / U21 / …)."""
    suf = _reserve_suffix(name)
    if suf is None:
        return 0
    core = name[: -len(suf)].rstrip()
    return match_unit_core_score(parent_short, core)


def lp32_name_ending_at(
    mm: mmap.mmap | bytes,
    suffix_abs: int,
    suf: str,
) -> tuple[int, str] | None:
    """If an lp32 name ending with `suf` has that suffix at suffix_abs, return (utf8_abs, name)."""
    raw_suf = suf.encode("utf-8")
    for back in range(4, 80):
        lp_off = suffix_abs - back
        if lp_off < 0:
            continue
        s = read_lp32(mm, lp_off)
        if not s or not s.endswith(suf):
            continue
        n = len(s.encode("utf-8"))
        utf8_abs = lp_off + 4
        if utf8_abs + n == suffix_abs + len(raw_suf) and utf8_abs <= suffix_abs:
            return utf8_abs, s
    return None


def resolve_after_name(mm: mmap.mmap | bytes, name_abs: int, name_len: int) -> int | None:
    """Return absolute offset of status-byte layout after resolving nested lp names."""
    after = name_abs + name_len
    for _ in range(3):
        if after + 1 + len(AFTER_MARKER) > len(mm):
            return None
        if bytes(mm[after + 1 : after + 1 + len(AFTER_MARKER)]) == AFTER_MARKER:
            return after
        nested = read_lp32(mm, after)
        if not nested:
            return None
        after = after + 4 + len(nested.encode("utf-8"))
    return None


def _club_from_name_hit(
    mm: mmap.mmap | bytes,
    parent_short: str,
    name: str,
    name_abs: int,
) -> dict[str, Any] | None:
    raw_len = len(name.encode("utf-8"))
    after = resolve_after_name(mm, name_abs, raw_len)
    if after is None:
        return None
    cid = struct.unpack_from("<I", mm, after + CLUB_ID_REL)[0]
    if not plausible_club_id(cid):
        return None
    layout = bytes(mm[after : after + CLUB_ID_REL + 4])
    return {
        "parentShort": parent_short,
        "iiName": name,
        "catalogNameAbs": name_abs,
        "layoutAbs": after,
        "clubId": cid,
        "clubIdAbs": after + CLUB_ID_REL,
        "layoutHex": layout.hex(" "),
        "statusByte": layout[0],
    }


def _iter_exact_reserve_names(parent_short: str) -> list[str]:
    return [f"{parent_short}{suf}" for suf in RESERVE_SUFFIXES]


def _catalog_spans(
    mm: mmap.mmap | bytes, *, catalog_limit: int | None = None
) -> list[tuple[int, int]]:
    n = len(mm)
    hint = CATALOG_HINT if catalog_limit is None else catalog_limit
    if n > hint:
        return [(0, hint), (hint, n)]
    return [(0, n)]


def _iter_ii_club_hits(
    mm: mmap.mmap | bytes,
    parent_short: str,
    *,
    catalog_limit: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield reserve catalog rows. Callers skip rows whose job-list is missing."""
    if not parent_short:
        return
    spans = _catalog_spans(mm, catalog_limit=catalog_limit)
    seen: set[int] = set()

    for name in _iter_exact_reserve_names(parent_short):
        raw = name.encode("utf-8")
        for lo, hi in spans:
            for h in iter_hits(mm, raw, lo=lo, hi=hi, batch=40):
                if h < 4 or h in seen:
                    continue
                if struct.unpack_from("<I", mm, h - 4)[0] != len(raw):
                    continue
                hit = _club_from_name_hit(mm, parent_short, name, h)
                if hit:
                    seen.add(h)
                    yield hit

    scored: list[tuple[int, int, dict[str, Any]]] = []
    for suf in RESERVE_SUFFIXES:
        needle = suf.encode("utf-8")
        for lo, hi in spans:
            for j in iter_hits(mm, needle, lo=lo, hi=hi, batch=400):
                found = lp32_name_ending_at(mm, j, suf)
                if not found:
                    continue
                name_abs, name = found
                if name_abs in seen:
                    continue
                score = match_reserve_name_score(parent_short, name)
                if score < 70:
                    continue
                hit = _club_from_name_hit(mm, parent_short, name, name_abs)
                if hit:
                    seen.add(name_abs)
                    scored.append((score, len(name), hit))
    scored.sort(key=lambda t: (-t[0], t[1]))
    for _score, _nlen, hit in scored:
        yield hit


def discover_ii_club_id(
    mm: mmap.mmap | bytes,
    parent_short: str,
    *,
    catalog_limit: int | None = None,
) -> dict[str, Any] | None:
    """Discover this club's reserve unit catalog row (any reserve suffix)."""
    for hit in _iter_ii_club_hits(mm, parent_short, catalog_limit=catalog_limit):
        return hit
    return None


def discover_ii_team_id(mm: mmap.mmap | bytes, catalog_name_abs: int) -> dict[str, Any] | None:
    lo = max(0, catalog_name_abs - 256)
    window = bytes(mm[lo:catalog_name_abs])
    j = window.rfind(PRE_NAME)
    if j < 0:
        return None
    pre_abs = lo + j
    if pre_abs < 12:
        return None
    tid = struct.unpack_from("<I", mm, pre_abs - 12)[0]
    d1 = struct.unpack_from("<I", mm, pre_abs - 8)[0]
    d2 = struct.unpack_from("<I", mm, pre_abs - 4)[0]
    if d1 != d2 or d1 in SENTINELS or d1 < 100:
        return None
    if not (100 <= tid <= 50_000) or tid in SENTINELS:
        return None
    return {
        "teamId": tid,
        "dup": d1,
        "preNameAbs": pre_abs,
        "teamIdAbs": pre_abs - 12,
    }


def find_ii_job_list(
    mm: mmap.mmap | bytes,
    team_id: int,
    dup: int,
) -> dict[str, Any] | None:
    """Locate team body by tid+zeros+dup×2 (whole blob); parse subunit job-list."""
    pat = struct.pack("<I", dup) * 2
    for dup_abs in iter_hits(mm, pat, lo=0, hi=len(mm), batch=BODY_HIT_LIMIT):
        tid_abs = match_team_body(mm, dup_abs, team_id)
        if tid_abs is None:
            continue
        m = mm.find(MOTIF_LIST, dup_abs, min(len(mm), dup_abs + 96))
        if m < 0:
            continue
        parsed = parse_count_jobs(mm, m + len(MOTIF_LIST))
        if not parsed:
            continue
        cnt, jobs_abs, jobs = parsed
        has_hdr = tid_abs >= 3 and bytes(mm[tid_abs - 3 : tid_abs]) == b"\x64\xff\x24"
        return {
            "tidAbs": tid_abs,
            "dupAbs": dup_abs,
            "countAbs": jobs_abs - 2,
            "jobsAbs": jobs_abs,
            "count": cnt,
            "jobs": jobs,
            "has64ff24": has_hdr,
            "midField": struct.unpack_from("<I", mm, tid_abs + 14)[0],
        }
    return None


def resolve_ii_squad(mm: mmap.mmap | bytes, parent_short: str) -> dict[str, Any] | None:
    """Parent short → this club's reserve team object → subunit job-list."""
    last: dict[str, Any] | None = None
    for club in _iter_ii_club_hits(mm, parent_short):
        team = discover_ii_team_id(mm, club["catalogNameAbs"])
        if not team:
            last = {**club, "team": None, "list": None}
            continue
        lst = find_ii_job_list(mm, team["teamId"], team["dup"])
        hit = {**club, "team": team, "list": lst}
        if lst and lst.get("jobs"):
            return hit
        last = hit
    return last
