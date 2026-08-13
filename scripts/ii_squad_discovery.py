"""Locked II/reserves squad discovery (parent short → clubId → teamId → job-list).

See data/fixtures/ii-clubid-discovery-locked.json and
data/fixtures/ii-squad-join-locked.json for the probe-verified recipe.
"""

from __future__ import annotations

import mmap
import struct
from typing import Any

SENTINELS = frozenset({0, 1, 255, 256, 65535, 65536, 0xFFFFFFFF})
AFTER_MARKER = bytes.fromhex("0000ffffffff00000100")
CLUB_ID_REL = 23
PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")
MOTIF_LIST = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"
CATALOG_LIMIT = 30_000_000


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
    if not (2 <= n <= 64) or off + 4 + n > len(mm):
        return None
    raw = bytes(mm[off + 4 : off + 4 + n])
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not s or not s[0].isalpha():
        return None
    return s


def plausible_club_id(cid: int) -> bool:
    return 100 <= cid <= 50_000 and cid not in SENTINELS


def resolve_after_name(mm: mmap.mmap | bytes, name_abs: int, name_len: int) -> int | None:
    """Return absolute offset of status-byte layout after resolving nested lp names."""
    after = name_abs + name_len
    for _ in range(3):
        if after + 1 + len(AFTER_MARKER) > len(mm):
            return None
        if bytes(mm[after + 1 : after + 1 + len(AFTER_MARKER)]) == AFTER_MARKER:
            return after
        nested = read_lp32(mm, after)
        if not nested or not nested.endswith(" II"):
            return None
        after = after + 4 + len(nested.encode("utf-8"))
    return None


def discover_ii_club_id(
    mm: mmap.mmap | bytes,
    parent_short: str,
    *,
    catalog_limit: int = CATALOG_LIMIT,
) -> dict[str, Any] | None:
    """Discover II affiliate clubId from parent short name alone."""
    ii_name = f"{parent_short} II"
    raw = ii_name.encode("utf-8")
    for h in find_all(mm, raw, limit=40):
        if h > catalog_limit or h < 4:
            continue
        if struct.unpack_from("<I", mm, h - 4)[0] != len(raw):
            continue
        after = resolve_after_name(mm, h, len(raw))
        if after is None:
            continue
        cid = struct.unpack_from("<I", mm, after + CLUB_ID_REL)[0]
        if not plausible_club_id(cid):
            continue
        layout = bytes(mm[after : after + CLUB_ID_REL + 4])
        return {
            "parentShort": parent_short,
            "iiName": ii_name,
            "catalogNameAbs": h,
            "layoutAbs": after,
            "clubId": cid,
            "clubIdAbs": after + CLUB_ID_REL,
            "layoutHex": layout.hex(" "),
            "statusByte": layout[0],
        }
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
    if d1 != d2 or d1 < 1000:
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
    """Locate mid-file team body by tid+zeros+dup×2; parse subunit job-list."""
    pat = struct.pack("<I", dup) * 2
    for dup_abs in find_all(mm, pat, limit=40, lo=40_000_000, hi=100_000_000):
        tid_abs = dup_abs - 18
        if tid_abs < 0:
            continue
        if struct.unpack_from("<I", mm, tid_abs)[0] != team_id:
            continue
        if bytes(mm[tid_abs + 4 : tid_abs + 14]) != bytes(10):
            continue
        if mm[dup_abs + 8] != 0x0A:
            continue
        m = mm.find(MOTIF_LIST, dup_abs, min(len(mm), dup_abs + 96))
        if m < 0:
            continue
        count_abs = m + len(MOTIF_LIST)
        cnt = struct.unpack_from("<H", mm, count_abs)[0]
        if not (3 <= cnt <= 50):
            continue
        jobs_abs = count_abs + 2
        if jobs_abs + 4 * cnt > len(mm):
            continue
        jobs = [
            struct.unpack_from("<I", mm, jobs_abs + 4 * i)[0] for i in range(cnt)
        ]
        ok = sum(1 for jid in jobs if 50_000 <= jid <= 2_000_000)
        if ok < max(3, (cnt + 1) // 2):
            continue
        has_hdr = tid_abs >= 3 and bytes(mm[tid_abs - 3 : tid_abs]) == b"\x64\xff\x24"
        return {
            "tidAbs": tid_abs,
            "dupAbs": dup_abs,
            "countAbs": count_abs,
            "jobsAbs": jobs_abs,
            "count": cnt,
            "jobs": jobs,
            "has64ff24": has_hdr,
            "midField": struct.unpack_from("<I", mm, tid_abs + 14)[0],
        }
    return None


def resolve_ii_squad(mm: mmap.mmap | bytes, parent_short: str) -> dict[str, Any] | None:
    """Parent short → II catalog clubId → teamId → subunit job-list."""
    club = discover_ii_club_id(mm, parent_short)
    if not club:
        return None
    team = discover_ii_team_id(mm, club["catalogNameAbs"])
    if not team:
        return {**club, "team": None, "list": None}
    lst = find_ii_job_list(mm, team["teamId"], team["dup"])
    return {**club, "team": team, "list": lst}
