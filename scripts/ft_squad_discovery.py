"""Managed First Team squad join (this club's team object → 7f02 job-list).

Primary key: identity club UniqueID on the club object. UTF-8 parent_short
catalog search is fallback. Catalog PRE_NAME → teamId/dup → persist-tid 7f02 jobs.

Join is object shape, not a megabyte band or a 15–45 count gate.
`ffffffff` tail, +128 window, and 10-zero body are first-pass heuristics that
expand (loose `7f02` / `010302` when the strict sentinel misses).

Employment rule (T009): jobIds on this joined list are managed-club employees.
Manager-hit `pick_tid` ranking must not override when identity is known.
"""

from __future__ import annotations

import mmap
import sys
import struct
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ii_squad_discovery import (  # noqa: E402
    BODY_HIT_LIMIT,
    CLUB_ID_REL,
    SENTINELS,
    iter_hits,
    jobs_majority_plausible,
    parse_count_jobs,
    read_lp32,
    resolve_after_name,
)

PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")
LIST_SENTINEL = bytes.fromhex("7f02000000ffffffff")
LIST_SENTINEL_LOOSE = bytes.fromhex("7f02000000")
TAG_010302 = bytes.fromhex("010302")
# Catalog search hint only — not a join gate.
CATALOG_HINT = 20_000_000
# First-pass list window; expand when the strict sentinel is missing.
LIST_WINDOWS = (128, 512, 2048, 32_768)
# How far UniqueID may sit after PRE_NAME on the club object.
CLUB_ID_LOOKBACK = 400


def discover_ft_team_id(mm: mmap.mmap | bytes, catalog_name_abs: int) -> dict[str, Any] | None:
    """PRE_NAME before catalog club name → teamId + dup (FT club object)."""
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


def match_ft_team_body(
    mm: mmap.mmap | bytes,
    dup_abs: int,
    team_id: int,
    *,
    require_zeros: bool = True,
) -> int | None:
    """teamId | 10 bytes | mid | dup×2 | 0a. Zero pad is a heuristic that expands."""
    tid_abs = dup_abs - 18
    if tid_abs < 0:
        return None
    if struct.unpack_from("<I", mm, tid_abs)[0] != team_id:
        return None
    if require_zeros and bytes(mm[tid_abs + 4 : tid_abs + 14]) != bytes(10):
        return None
    if dup_abs + 8 >= len(mm) or mm[dup_abs + 8] != 0x0A:
        return None
    return tid_abs


def _parse_ft_list_at_loose(mm: mmap.mmap | bytes, sent: int) -> dict[str, Any] | None:
    """Parse persist-tid + jobs at a loose `7f02000000` (ff / 010302 / zeros / direct)."""
    if sent < 4 or sent + len(LIST_SENTINEL_LOOSE) > len(mm):
        return None
    if bytes(mm[sent : sent + len(LIST_SENTINEL_LOOSE)]) != LIST_SENTINEL_LOOSE:
        return None
    persist_tid = struct.unpack_from("<I", mm, sent - 4)[0]
    if persist_tid in SENTINELS or persist_tid < 100:
        return None
    after = sent + len(LIST_SENTINEL_LOOSE)
    count_offs: list[int] = []
    if after + 4 <= len(mm) and bytes(mm[after : after + 4]) == b"\xff\xff\xff\xff":
        count_offs.append(after + 4)
    if after + 3 <= len(mm) and bytes(mm[after : after + 3]) == TAG_010302:
        count_offs.append(after + 4)
    if after + 4 <= len(mm) and bytes(mm[after : after + 4]) == b"\x00\x00\x00\x00":
        count_offs.append(after + 4)
    count_offs.append(after)
    seen: set[int] = set()
    for c_off in count_offs:
        if c_off in seen:
            continue
        seen.add(c_off)
        parsed = parse_count_jobs(mm, c_off)
        if not parsed:
            continue
        cnt, jobs_abs, jobs = parsed
        if not jobs_majority_plausible(jobs):
            continue
        return {
            "persistTid": persist_tid,
            "sentinelAbs": sent,
            "countAbs": jobs_abs - 2,
            "jobsAbs": jobs_abs,
            "count": cnt,
            "jobs": jobs,
        }
    return None


def _parse_ft_list_at_tag(mm: mmap.mmap | bytes, tag_abs: int) -> dict[str, Any] | None:
    """`010302` after loose 7f02, or persist-tid | 010302 | pad | count when 7f02 is absent."""
    if tag_abs + 3 > len(mm) or bytes(mm[tag_abs : tag_abs + 3]) != TAG_010302:
        return None
    if tag_abs >= 5 and bytes(mm[tag_abs - 5 : tag_abs]) == LIST_SENTINEL_LOOSE:
        return _parse_ft_list_at_loose(mm, tag_abs - 5)
    if tag_abs < 4:
        return None
    persist_tid = struct.unpack_from("<I", mm, tag_abs - 4)[0]
    if persist_tid in SENTINELS or persist_tid < 100:
        return None
    parsed = parse_count_jobs(mm, tag_abs + 4)
    if not parsed:
        return None
    cnt, jobs_abs, jobs = parsed
    if not jobs_majority_plausible(jobs):
        return None
    return {
        "persistTid": persist_tid,
        "sentinelAbs": tag_abs,
        "countAbs": jobs_abs - 2,
        "jobsAbs": jobs_abs,
        "count": cnt,
        "jobs": jobs,
    }


def _job_list_near_tid(mm: mmap.mmap | bytes, tid_abs: int) -> dict[str, Any] | None:
    """Strict `7f02…ffffffff` first; window and loose/010302 expand on miss."""
    n = len(mm)
    for win in LIST_WINDOWS:
        hi = min(n, tid_abs + win)
        sent = mm.find(LIST_SENTINEL, tid_abs, hi)
        if sent >= 4:
            parsed = _parse_ft_list_at_loose(mm, sent)
            if parsed:
                return parsed
        start = tid_abs
        while start < hi:
            sent = mm.find(LIST_SENTINEL_LOOSE, start, hi)
            if sent < 0:
                break
            parsed = _parse_ft_list_at_loose(mm, sent)
            if parsed:
                return parsed
            start = sent + 1
        start = tid_abs
        while start < hi:
            tag = mm.find(TAG_010302, start, hi)
            if tag < 0:
                break
            parsed = _parse_ft_list_at_tag(mm, tag)
            if parsed:
                return parsed
            start = tag + 1
    return None


def find_ft_job_list(
    mm: mmap.mmap | bytes,
    team_id: int,
    dup: int,
) -> dict[str, Any] | None:
    """Locate club team body anywhere in the blob; parse persist-tid 7f02 list."""
    pat = struct.pack("<I", dup) * 2
    for require_zeros in (True, False):
        for dup_abs in iter_hits(mm, pat, lo=0, hi=len(mm), batch=BODY_HIT_LIMIT):
            tid_abs = match_ft_team_body(
                mm, dup_abs, team_id, require_zeros=require_zeros
            )
            if tid_abs is None:
                continue
            parsed = _job_list_near_tid(mm, tid_abs)
            if not parsed:
                continue
            has_hdr = tid_abs >= 3 and bytes(mm[tid_abs - 3 : tid_abs]) == b"\x64\xff\x24"
            return {
                **parsed,
                "bodyTeamId": team_id,
                "bodyTidAbs": tid_abs,
                "dupAbs": dup_abs,
                "has64ff24": has_hdr,
                "midField": struct.unpack_from("<I", mm, tid_abs + 14)[0],
            }
    return None


def _catalog_spans(n: int) -> list[tuple[int, int]]:
    if n > CATALOG_HINT:
        return [(0, CATALOG_HINT), (CATALOG_HINT, n)]
    return [(0, n)]


def _club_id_slots(mm: mmap.mmap | bytes, name_abs: int, name: str) -> list[int]:
    """Structural UniqueID slots on a PRE_NAME club object (immediate / after-name)."""
    raw_len = len(name.encode("utf-8"))
    slots: list[int] = []
    immediate = name_abs + raw_len
    if immediate + 4 <= len(mm):
        slots.append(immediate)
    after = resolve_after_name(mm, name_abs, raw_len)
    if after is not None:
        slot = after + CLUB_ID_REL
        if slot + 4 <= len(mm):
            slots.append(slot)
    return slots


def _club_id_on_object(mm: mmap.mmap | bytes, name_abs: int, name: str) -> int | None:
    for slot in _club_id_slots(mm, name_abs, name):
        cid = struct.unpack_from("<I", mm, slot)[0]
        if cid not in SENTINELS and cid != 0:
            return cid
    return None


def _name_at_pre(mm: mmap.mmap | bytes, pre_abs: int) -> tuple[int, str] | None:
    name_lp = pre_abs + len(PRE_NAME)
    name = read_lp32(mm, name_lp)
    if not name:
        return None
    return name_lp + 4, name


def _iter_ft_by_club_id(
    mm: mmap.mmap | bytes, club_id: int
) -> Iterator[dict[str, Any]]:
    packed = struct.pack("<I", int(club_id))
    seen_pre: set[int] = set()
    for cid_abs in iter_hits(mm, packed, lo=0, hi=len(mm), batch=80):
        lo = max(0, cid_abs - CLUB_ID_LOOKBACK)
        window = bytes(mm[lo:cid_abs])
        j = window.rfind(PRE_NAME)
        if j < 0:
            continue
        pre_abs = lo + j
        if pre_abs in seen_pre:
            continue
        named = _name_at_pre(mm, pre_abs)
        if not named:
            continue
        name_abs, name = named
        if cid_abs not in _club_id_slots(mm, name_abs, name):
            continue
        team = discover_ft_team_id(mm, name_abs)
        if not team:
            continue
        seen_pre.add(pre_abs)
        yield {
            "parentShort": name,
            "clubId": int(club_id),
            "catalogNameAbs": name_abs,
            "catalogName": name,
            "team": team,
        }


def _iter_ft_by_short_name(
    mm: mmap.mmap | bytes, parent_short: str
) -> Iterator[dict[str, Any]]:
    raw = parent_short.encode("utf-8")
    n = len(mm)
    for lo, hi in _catalog_spans(n):
        for h in iter_hits(mm, raw, lo=lo, hi=hi, batch=80):
            if h < 4:
                continue
            if struct.unpack_from("<I", mm, h - 4)[0] != len(raw):
                continue
            team = discover_ft_team_id(mm, h)
            if not team:
                continue
            name = read_lp32(mm, h - 4)
            if not name:
                continue
            yield {
                "parentShort": parent_short,
                "clubId": _club_id_on_object(mm, h, name),
                "catalogNameAbs": h,
                "catalogName": name,
                "team": team,
            }


def _empty_ft_hit(
    parent_short: str | None,
    club_id: int | None,
    *,
    catalog_hits: int = 0,
    team_objects: int = 0,
) -> dict[str, Any]:
    return {
        "parentShort": parent_short,
        "clubId": club_id,
        "catalogNameAbs": None,
        "catalogName": None,
        "team": None,
        "list": None,
        "catalogHits": catalog_hits,
        "teamObjects": team_objects,
        "jobsFound": 0,
    }


def resolve_ft_squad(
    mm: mmap.mmap | bytes,
    parent_short: str | None,
    club_id: int | None = None,
) -> dict[str, Any] | None:
    """Identity clubId (primary) or parent short (fallback) → FT 7f02 job-list."""
    catalog_hits = 0
    team_objects = 0
    last: dict[str, Any] | None = None
    seen_pre: set[int] = set()

    def consider(row: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal catalog_hits, team_objects, last
        team = row.get("team")
        pre = (team or {}).get("preNameAbs")
        if pre is not None:
            if pre in seen_pre:
                return None
            seen_pre.add(pre)
        catalog_hits += 1
        if team:
            team_objects += 1
        lst = None
        if team:
            lst = find_ft_job_list(mm, team["teamId"], team["dup"])
        jobs = list((lst or {}).get("jobs") or [])
        hit = {
            **row,
            "list": lst,
            "catalogHits": catalog_hits,
            "teamObjects": team_objects,
            "jobsFound": len(jobs),
        }
        if jobs:
            return hit
        last = hit
        return None

    cid = int(club_id) if club_id not in (None, 0) else None
    if cid is not None and cid not in SENTINELS:
        for row in _iter_ft_by_club_id(mm, cid):
            won = consider(row)
            if won:
                return won
    if parent_short:
        for row in _iter_ft_by_short_name(mm, parent_short):
            won = consider(row)
            if won:
                return won
    if last:
        last["catalogHits"] = catalog_hits
        last["teamObjects"] = team_objects
        last["jobsFound"] = 0
        return last
    if cid is not None or parent_short:
        return _empty_ft_hit(parent_short, cid)
    return None


def _ft_miss_reason(ft_hit: dict[str, Any] | None) -> str:
    if not ft_hit or not ft_hit.get("catalogHits"):
        if not ft_hit or not ft_hit.get("team"):
            return "no-catalog"
    if not ft_hit.get("team"):
        return "no-team-object"
    if not (ft_hit.get("list") or {}).get("jobs"):
        return "no-job-list"
    return "no-job-list"


def _identity_known(club_short: str | None, club_id: int | None) -> bool:
    if club_short:
        return True
    if club_id in (None, 0):
        return False
    return int(club_id) not in SENTINELS


def ft_join_progress_fields(
    club_id: int | None,
    ft_hit: dict[str, Any] | None,
    selected: dict[str, Any],
    *,
    layout: str | None = None,
) -> dict[str, Any]:
    """PROGRESS keys for the resolve line — jobsFound is 0 vs N."""
    jobs = list(selected.get("jobs") or [])
    fields: dict[str, Any] = {
        "clubId": club_id,
        "missReason": selected.get("missReason"),
        "catalogHits": int((ft_hit or {}).get("catalogHits") or 0),
        "teamObjects": int((ft_hit or {}).get("teamObjects") or 0),
        "jobsFound": len(jobs),
    }
    if layout in ("continue", "native"):
        fields["layout"] = layout
    return fields


def select_managed_ft_jobs(
    club_short: str | None,
    ft_hit: dict[str, Any] | None,
    *,
    fallback_jobs: list[int] | None = None,
    club_id: int | None = None,
) -> dict[str, Any]:
    """
    T009 employment gate: only admit FT jobs from the managed-club join.

    When identity is known (club short or UniqueID), never return
    fallback/pick_tid jobs — empty list on join miss so foreign/non-employed
    bodies cannot win roster membership.
    """
    ft_list = (ft_hit or {}).get("list") if ft_hit else None
    if ft_list and ft_list.get("jobs"):
        return {
            "method": "ft-club-squad-join-v1",
            "jobs": list(ft_list["jobs"]),
            "persistTid": ft_list.get("persistTid"),
            "listAbs": ft_list.get("jobsAbs"),
            "count": ft_list.get("count"),
            "missReason": None,
        }
    if _identity_known(club_short, club_id):
        return {
            "method": "ft-club-squad-join-miss",
            "jobs": [],
            "persistTid": None,
            "listAbs": None,
            "count": 0,
            "missReason": _ft_miss_reason(ft_hit),
        }
    jobs = list(fallback_jobs or [])
    return {
        "method": "max_manager_staff_link_among_squad_lists",
        "jobs": jobs,
        "persistTid": None,
        "listAbs": None,
        "count": len(jobs),
        "missReason": None,
    }
