"""Managed First Team squad join (this club's team object → 7f02 job-list).

Catalog PRE_NAME → teamId/dup → team body → persist-tid 7f02 jobs.
Join is object shape, not a megabyte band or a 15–45 count gate.

Employment rule (T009): jobIds on this joined list are managed-club employees.
Manager-hit `pick_tid` ranking must not override when identity is known.
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
    BODY_HIT_LIMIT,
    SENTINELS,
    find_all,
    jobs_majority_plausible,
    match_team_body,
    parse_count_jobs,
    read_lp32,
)

PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")
LIST_SENTINEL = bytes.fromhex("7f02000000ffffffff")
# Catalog search hint only — not a join gate.
CATALOG_HINT = 20_000_000


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


def find_ft_job_list(
    mm: mmap.mmap | bytes,
    team_id: int,
    dup: int,
) -> dict[str, Any] | None:
    """Locate club team body anywhere in the blob; parse persist-tid 7f02 list."""
    pat = struct.pack("<I", dup) * 2
    for dup_abs in find_all(mm, pat, limit=BODY_HIT_LIMIT, lo=0, hi=len(mm)):
        tid_abs = match_team_body(mm, dup_abs, team_id)
        if tid_abs is None:
            continue
        hi = min(len(mm), tid_abs + 128)
        sent = mm.find(LIST_SENTINEL, tid_abs, hi)
        if sent < 4:
            continue
        persist_tid = struct.unpack_from("<I", mm, sent - 4)[0]
        if persist_tid in SENTINELS or persist_tid < 100:
            continue
        parsed = parse_count_jobs(mm, sent + len(LIST_SENTINEL))
        if not parsed:
            continue
        cnt, jobs_abs, jobs = parsed
        if not jobs_majority_plausible(jobs):
            continue
        has_hdr = tid_abs >= 3 and bytes(mm[tid_abs - 3 : tid_abs]) == b"\x64\xff\x24"
        return {
            "bodyTeamId": team_id,
            "bodyTidAbs": tid_abs,
            "dupAbs": dup_abs,
            "persistTid": persist_tid,
            "sentinelAbs": sent,
            "countAbs": jobs_abs - 2,
            "jobsAbs": jobs_abs,
            "count": cnt,
            "jobs": jobs,
            "has64ff24": has_hdr,
            "midField": struct.unpack_from("<I", mm, tid_abs + 14)[0],
        }
    return None


def resolve_ft_squad(mm: mmap.mmap | bytes, parent_short: str) -> dict[str, Any] | None:
    """Parent short → club-object teamId/dup → First Team 7f02 job-list."""
    if not parent_short:
        return None
    raw = parent_short.encode("utf-8")
    n = len(mm)
    spans: list[tuple[int, int]] = []
    if n > CATALOG_HINT:
        spans.append((0, CATALOG_HINT))
        spans.append((CATALOG_HINT, n))
    else:
        spans.append((0, n))
    for lo, hi in spans:
        for h in find_all(mm, raw, limit=80, lo=lo, hi=hi):
            if h < 4:
                continue
            if struct.unpack_from("<I", mm, h - 4)[0] != len(raw):
                continue
            # Identity block has the short name without PRE_NAME; require club object.
            team = discover_ft_team_id(mm, h)
            if not team:
                continue
            name = read_lp32(mm, h - 4)
            if not name:
                continue
            lst = find_ft_job_list(mm, team["teamId"], team["dup"])
            return {
                "parentShort": parent_short,
                "catalogNameAbs": h,
                "catalogName": name,
                "team": team,
                "list": lst,
            }
    return None


def _ft_miss_reason(ft_hit: dict[str, Any] | None) -> str:
    if not ft_hit:
        return "no-catalog"
    if not ft_hit.get("team"):
        return "no-team-object"
    if not (ft_hit.get("list") or {}).get("jobs"):
        return "no-job-list"
    return "no-job-list"


def select_managed_ft_jobs(
    club_short: str | None,
    ft_hit: dict[str, Any] | None,
    *,
    fallback_jobs: list[int] | None = None,
) -> dict[str, Any]:
    """
    T009 employment gate: only admit FT jobs from the managed-club join.

    When club_short is known, never return fallback/pick_tid jobs — empty list
    on join miss so foreign/non-employed bodies cannot win roster membership.
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
    if club_short:
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
