#!/usr/bin/env python3
"""Lock: parent short → II clubId → teamId → subunit job-list.

Builds on ii-clubid-discovery-v1 (same catalog row). Join key is catalog
teamId+dup → mid-file team body → subunit header (NOT 64 ff 00 + clubId).

Recipe (probe-verified on fmt-probe-wmr70v8a.bin):
  1. Discover II clubId: lp32 + f'{S} II' → after_name+23 (existing lock)
  2. Same short-name hit: rfind pre-name motif
       00 91 00 00 00 | ff×4 | 91 00 00 00 | 91 00 00 00
     within the 256 bytes before the short name
  3. Immediately before motif: <teamId:u32> <dup:u32> <dup:u32> (dups equal)
  4. Mid-file team body: <teamId> | 00×10 | <u32> | <dup>×2 | 0a …
     (64 ff 24 prefix optional — absent for some packed rows)
  5. Within +96 of dup pair: ff×4|00|ff×4 | count:u16∈[3,50] | jobs
  6. Majority of jobs in 50000..2000000

Schalke 04 verification (not discovery inputs):
  clubId=13217, teamId=6912, list@57023793 n=23, Ermin job 237871 @ index 3
"""

from __future__ import annotations

import argparse
import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "squad-ii-joblist-lock.txt"

PREFERRED_BIN = Path.home() / "AppData" / "Local" / "Temp" / "fmt-probe-wmr70v8a.bin"

PARENT_SHORT = "Schalke 04"

# Verification only
EXPECTED_SCHALKE_II_CLUB = 13217
EXPECTED_SCHALKE_TEAM = 6912
EXPECTED_LIST_COUNT_ABS = 57023793
ERMIN_JOB = 237871

SENTINELS = frozenset({0, 1, 255, 256, 65535, 65536, 0xFFFFFFFF})
AFTER_MARKER = bytes.fromhex("0000ffffffff00000100")
CLUB_ID_REL = 23
PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")
MOTIF_LIST = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"

CROSS_PARENTS = [
    "Schalke 04",
    "Kaiserslautern",
    "Hansa Rostock",
    "Karlsruhe",
    "Borussia Dortmund",
    "Werder Bremen",
    "Hoffenheim",
    "VfB Stuttgart",
]


def pick_bin(explicit: Path | None = None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise SystemExit(f"bin not found: {explicit}")
        return explicit
    if PREFERRED_BIN.is_file() and PREFERRED_BIN.stat().st_size > 1_500_000_000:
        return PREFERRED_BIN
    for p in sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
        key=lambda q: q.stat().st_mtime,
        reverse=True,
    ):
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no fmt-*.bin probe found in Temp")


def find_all(
    mm: mmap.mmap,
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


def read_lp32(mm: mmap.mmap, off: int) -> str | None:
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


def resolve_after_name(mm: mmap.mmap, name_abs: int, name_len: int) -> int | None:
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


def discover_ii_club_id(mm: mmap.mmap, parent_short: str) -> dict | None:
    ii_name = f"{parent_short} II"
    raw = ii_name.encode("utf-8")
    for h in find_all(mm, raw, limit=40):
        if not (4 <= h <= 30_000_000):
            continue
        if struct.unpack_from("<I", mm, h - 4)[0] != len(raw):
            continue
        after = resolve_after_name(mm, h, len(raw))
        if after is None:
            continue
        cid = struct.unpack_from("<I", mm, after + CLUB_ID_REL)[0]
        if not (100 <= cid <= 50_000 and cid not in SENTINELS):
            continue
        return {
            "parentShort": parent_short,
            "iiName": ii_name,
            "catalogNameAbs": h,
            "layoutAbs": after,
            "clubId": cid,
            "clubIdAbs": after + CLUB_ID_REL,
        }
    return None


def discover_ii_team_id(mm: mmap.mmap, catalog_name_abs: int) -> dict | None:
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


def find_ii_job_list(mm: mmap.mmap, team_id: int, dup: int) -> dict | None:
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


def resolve_ii_squad(mm: mmap.mmap, parent_short: str) -> dict | None:
    club = discover_ii_club_id(mm, parent_short)
    if not club:
        return None
    team = discover_ii_team_id(mm, club["catalogNameAbs"])
    if not team:
        return {**club, "team": None, "list": None}
    lst = find_ii_job_list(mm, team["teamId"], team["dup"])
    return {**club, "team": team, "list": lst}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bin", type=Path, default=None)
    ap.add_argument("--parent-short", default=PARENT_SHORT)
    args = ap.parse_args()

    bin_path = pick_bin(args.bin)
    t0 = time.perf_counter()
    lines: list[str] = [
        f"# II clubId -> teamId -> job-list lock · {bin_path.name}",
        f"parentShort={args.parent_short!r}",
        "",
        "## RECIPE",
        "1. clubId via catalog lp32 + f'{S} II' -> after_name+23",
        "2. Same row: pre-name motif 00 91 00 00 00|ffx4|91|91 -> teamId+dup+dup",
        "3. Mid-file body: teamId | 00x10 | u32 | dupx2 | 0a ...",
        "4. Motif ffx4|00|ffx4 + count:u16 in [3,50] + jobs (64 ff 24 optional)",
        "",
    ]
    print(f"mmap {bin_path.name}...", flush=True)

    hit: dict | None = None
    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hit = resolve_ii_squad(mm, args.parent_short)
            lines.append("## parent -> II clubId -> teamId -> job-list")
            if not hit:
                lines.append(f"  FAIL: no II catalog row for {args.parent_short!r}")
            else:
                lines.append(
                    f"  {hit['parentShort']} -> {hit['iiName']!r} "
                    f"clubId={hit['clubId']} catalog@{hit['catalogNameAbs']}"
                )
                team = hit.get("team")
                lst = hit.get("list")
                if not team:
                    lines.append("  FAIL: teamId not found before catalog name")
                else:
                    lines.append(
                        f"  teamId={team['teamId']} dup={team['dup']} "
                        f"teamIdAbs={team['teamIdAbs']}"
                    )
                if not lst:
                    lines.append("  FAIL: subunit job-list not found for team body")
                else:
                    lines.append(
                        f"  list count@{lst['countAbs']} jobs@{lst['jobsAbs']} "
                        f"n={lst['count']} has64ff24={lst['has64ff24']}"
                    )
                    lines.append(f"  jobsSample={lst['jobs'][:8]}")
                    if args.parent_short == PARENT_SHORT:
                        checks = [
                            ("clubId", hit["clubId"] == EXPECTED_SCHALKE_II_CLUB),
                            (
                                "teamId",
                                bool(team) and team["teamId"] == EXPECTED_SCHALKE_TEAM,
                            ),
                            (
                                "listAbs",
                                bool(lst)
                                and lst["countAbs"] == EXPECTED_LIST_COUNT_ABS,
                            ),
                            (
                                "Ermin",
                                bool(lst) and ERMIN_JOB in lst["jobs"],
                            ),
                        ]
                        for label, ok in checks:
                            lines.append(
                                f"  verify {label}: {'PASS' if ok else 'FAIL'}"
                            )
                        if lst and ERMIN_JOB in lst["jobs"]:
                            lines.append(
                                f"  Ermin job {ERMIN_JOB} @ index "
                                f"{lst['jobs'].index(ERMIN_JOB)}"
                            )

            lines.append("")
            lines.append("## cross-club join")
            n_ok = 0
            for parent in CROSS_PARENTS:
                r = resolve_ii_squad(mm, parent)
                if not r or not r.get("team") or not r.get("list"):
                    lines.append(f"  {parent}: FAIL")
                    continue
                n_ok += 1
                lines.append(
                    f"  {parent}: clubId={r['clubId']} teamId={r['team']['teamId']} "
                    f"list@{r['list']['countAbs']} n={r['list']['count']} "
                    f"hdr64ff24={r['list']['has64ff24']}"
                )
            lines.append(f"  joined={n_ok}/{len(CROSS_PARENTS)}")

            lines.append("")
            lines.append("## anti-pattern: 64 ff 00 + clubId is NOT the list join")
            if hit:
                tag = b"\x64\xff\x00" + struct.pack("<I", hit["clubId"])
                th = find_all(mm, tag, limit=5)
                lines.append(f"  64ff00+clubId hits={th}")
                if th and hit.get("list"):
                    lines.append(
                        f"  delta list->64ff00 = {th[0] - hit['list']['countAbs']:+d} "
                        "(large gap; do not proximity-join)"
                    )
        finally:
            mm.close()

    lines.append(f"\nelapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))

    if not hit or not hit.get("list"):
        return 1
    if args.parent_short == PARENT_SHORT:
        team = hit["team"]
        lst = hit["list"]
        if (
            hit["clubId"] != EXPECTED_SCHALKE_II_CLUB
            or not team
            or team["teamId"] != EXPECTED_SCHALKE_TEAM
            or lst["countAbs"] != EXPECTED_LIST_COUNT_ABS
            or ERMIN_JOB not in lst["jobs"]
        ):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
