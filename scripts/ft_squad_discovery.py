"""Managed First Team squad join (parent short → teamId/dup → 7f02 job-list).

Mirrors the II catalog PRE_NAME → mid-file team-body join, but the FT body
owns a persist-tid 7f02ffffffff job-list (not the subunit ff|00|ff header).

Employment rule (T009): jobIds on this joined list are managed-club employees.
Manager-hit `pick_tid` ranking must not override when identity is known — that
path admits foreign/non-employed bodies under the managed clubName.

See data/fixtures/ft-club-squad-join-locked.json.
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

from ii_squad_discovery import SENTINELS, find_all, read_lp32  # noqa: E402

PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")
LIST_SENTINEL = bytes.fromhex("7f02000000ffffffff")
CATALOG_LIMIT = 20_000_000
BODY_LO = 40_000_000
BODY_HI = 100_000_000
JOB_LO, JOB_HI = 100, 50_000_000
FT_COUNT_LO, FT_COUNT_HI = 15, 45


def discover_ft_team_id(mm: mmap.mmap | bytes, catalog_name_abs: int) -> dict[str, Any] | None:
    """PRE_NAME before catalog club name → subunit teamId + dup (FT club object)."""
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
    """Locate mid-file club team body; parse persist-tid 7f02 First Team job-list."""
    pat = struct.pack("<I", dup) * 2
    for dup_abs in find_all(mm, pat, limit=40, lo=BODY_LO, hi=BODY_HI):
        tid_abs = dup_abs - 18
        if tid_abs < 0:
            continue
        if struct.unpack_from("<I", mm, tid_abs)[0] != team_id:
            continue
        if bytes(mm[tid_abs + 4 : tid_abs + 14]) != bytes(10):
            continue
        if mm[dup_abs + 8] != 0x0A:
            continue
        hi = min(len(mm), tid_abs + 128)
        sent = mm.find(LIST_SENTINEL, tid_abs, hi)
        if sent < 4:
            continue
        persist_tid = struct.unpack_from("<I", mm, sent - 4)[0]
        if persist_tid in SENTINELS or persist_tid < 1000:
            continue
        count_abs = sent + len(LIST_SENTINEL)
        if count_abs + 2 > len(mm):
            continue
        cnt = struct.unpack_from("<H", mm, count_abs)[0]
        if not (FT_COUNT_LO <= cnt <= FT_COUNT_HI):
            continue
        jobs_abs = count_abs + 2
        if jobs_abs + 4 * cnt > len(mm):
            continue
        jobs = [
            struct.unpack_from("<I", mm, jobs_abs + 4 * i)[0] for i in range(cnt)
        ]
        ok = sum(1 for jid in jobs if JOB_LO <= jid <= JOB_HI and jid)
        if ok < max(8, (cnt + 1) // 2):
            continue
        has_hdr = tid_abs >= 3 and bytes(mm[tid_abs - 3 : tid_abs]) == b"\x64\xff\x24"
        return {
            "bodyTeamId": team_id,
            "bodyTidAbs": tid_abs,
            "dupAbs": dup_abs,
            "persistTid": persist_tid,
            "sentinelAbs": sent,
            "countAbs": count_abs,
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
    for h in find_all(mm, raw, limit=40, hi=CATALOG_LIMIT):
        if h < 4:
            continue
        if struct.unpack_from("<I", mm, h - 4)[0] != len(raw):
            continue
        # Identity block has the short name without PRE_NAME; require club object.
        team = discover_ft_team_id(mm, h)
        if not team:
            continue
        # Prefer the short-name row that sits after a long name (catalog club site).
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
        }
    if club_short:
        return {
            "method": "ft-club-squad-join-miss",
            "jobs": [],
            "persistTid": None,
            "listAbs": None,
            "count": 0,
        }
    jobs = list(fallback_jobs or [])
    return {
        "method": "max_manager_staff_link_among_squad_lists",
        "jobs": jobs,
        "persistTid": None,
        "listAbs": None,
        "count": len(jobs),
    }
