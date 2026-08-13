#!/usr/bin/env python3
"""Lock: discover affiliate II clubId from parent short name alone.

Recipe (probe-verified on fmt-probe-wmr70v8a.bin):
  1. parent short name S (e.g. 'Schalke 04' from managed club ~920)
  2. find early catalog row: lp32 + f'{S} II' (exact length prefix)
  3. if the bytes after the name are another lp32 ending in ' II', skip it
     (long/short name-pair residue — e.g. BVB, VfB Stuttgart)
  4. require after-name layout:
       <status:u8> 00 00 | ff×4 | 00 00 01 00 | pad… | <clubId:u32le at +23>
  5. reject sentinels / out-of-range: 0,1,255,256,65535,65536,0xffffffff
     and require 100 <= clubId <= 50000

Schalke 04 → expected clubId 13217 (verification output only — not discovery input).

Optional: confirm Ermin Maric job 237871 sits in the known II subunit job-list
header region (does not feed discovery).
"""

from __future__ import annotations

import argparse
import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "squad-ii-clubid-lock.txt"

PREFERRED_BIN = Path.home() / "AppData" / "Local" / "Temp" / "fmt-probe-wmr70v8a.bin"

# Managed parent — allowed discovery input
PARENT_SHORT = "Schalke 04"
PARENT_CLUB_ID = 920

# Verification only (not discovery inputs)
EXPECTED_SCHALKE_II = 13217
ERMIN_JOB = 237871
II_LIST_ABS = 57023793  # jobs start; header count u16 immediately before

SENTINELS = frozenset({0, 1, 255, 256, 65535, 65536, 0xFFFFFFFF})
# bytes[1:11] after short name (status byte at [0] varies 01/02/…)
AFTER_MARKER = bytes.fromhex("0000ffffffff00000100")  # len 10
CLUB_ID_REL = 23

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
            # Prefer one that still contains the catalog string
            return p
    raise SystemExit("no fmt-*.bin probe found in Temp")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 40) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
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


def plausible_club_id(cid: int) -> bool:
    return 100 <= cid <= 50_000 and cid not in SENTINELS


def resolve_after_name(mm: mmap.mmap, name_abs: int, name_len: int) -> int | None:
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
    mm: mmap.mmap,
    parent_short: str,
    *,
    catalog_limit: int = 30_000_000,
) -> dict | None:
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


def find_ii_job_list_with_job(
    mm: mmap.mmap,
    job_id: int,
    list_abs_hint: int | None = None,
) -> dict | None:
    """Optional: confirm subunit job-list header + packed jobs containing job_id."""
    jb = struct.pack("<I", job_id)
    # Prefer known probe locus; else scan for motif near any job hit
    candidates: list[int] = []
    if list_abs_hint is not None:
        candidates.append(list_abs_hint)
    for joff in find_all(mm, jb, limit=40):
        # look back ≤40 for 00 ff×4 <count:u16> with count in [12,50]
        for back in range(2, 40):
            o = joff - back
            if o < 5:
                continue
            if bytes(mm[o - 5 : o]) != b"\x00\xff\xff\xff\xff":
                continue
            cnt = struct.unpack_from("<H", mm, o)[0]
            if not (12 <= cnt <= 50):
                continue
            jobs_off = o + 2
            if jobs_off + 4 * cnt > len(mm):
                continue
            jobs = [
                struct.unpack_from("<I", mm, jobs_off + 4 * i)[0] for i in range(cnt)
            ]
            if job_id not in jobs:
                continue
            return {
                "countAbs": o,
                "jobsAbs": jobs_off,
                "count": cnt,
                "jobIndex": jobs.index(job_id),
                "jobsSample": jobs[:6],
            }
    # hint path: parse hint directly
    for hint in candidates:
        # count u16 two bytes before jobs
        cnt = struct.unpack_from("<H", mm, hint - 2)[0]
        if 12 <= cnt <= 50:
            jobs = [
                struct.unpack_from("<I", mm, hint + 4 * i)[0] for i in range(cnt)
            ]
            if job_id in jobs:
                return {
                    "countAbs": hint - 2,
                    "jobsAbs": hint,
                    "count": cnt,
                    "jobIndex": jobs.index(job_id),
                    "jobsSample": jobs[:6],
                }
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bin", type=Path, default=None, help="probe bin path")
    ap.add_argument(
        "--parent-short",
        default=PARENT_SHORT,
        help="managed club short name (discovery input)",
    )
    args = ap.parse_args()

    bin_path = pick_bin(args.bin)
    t0 = time.perf_counter()
    lines: list[str] = [
        f"# II clubId lock · {bin_path.name}",
        f"parentShort={args.parent_short!r} parentClubId={PARENT_CLUB_ID}",
        "",
        "## RECIPE",
        "1. Start from parent short name S",
        "2. Catalog search: lp32 + f'{S} II' (early file, exact length)",
        "3. Skip nested lp32 '* II' name if present (name-pair residue)",
        "4. Require after-name: <status> 00 00 | ff×4 | 00 00 01 00 | …",
        f"5. clubId = u32le at after_name+{CLUB_ID_REL}",
        "6. Reject sentinels (65535/65536/256/…) and ids outside 100..50000",
        "",
    ]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            hit = discover_ii_club_id(mm, args.parent_short)
            lines.append("## parent → II")
            if not hit:
                lines.append(f"  FAIL: no II catalog row for {args.parent_short!r}")
            else:
                lines.append(
                    f"  {hit['parentShort']} → {hit['iiName']!r} "
                    f"catalog@{hit['catalogNameAbs']} clubId={hit['clubId']}"
                )
                lines.append(f"  layoutAbs={hit['layoutAbs']} clubIdAbs={hit['clubIdAbs']}")
                lines.append(f"  layout: {hit['layoutHex']}")
                lines.append(
                    "  annotated: "
                    f"status={hit['statusByte']:02x} | 00 00 ff×4 00 00 01 00 | "
                    f"pad → u32le@{CLUB_ID_REL}={hit['clubId']} (0x{hit['clubId']:x})"
                )
                if args.parent_short == PARENT_SHORT:
                    ok = hit["clubId"] == EXPECTED_SCHALKE_II
                    lines.append(
                        f"  verify expected {EXPECTED_SCHALKE_II}: "
                        f"{'PASS' if ok else 'FAIL'}"
                    )

            lines.append("")
            lines.append("## cross-club +23 recipe (unique plausible ids)")
            for p in CROSS_PARENTS:
                r = discover_ii_club_id(mm, p)
                if r is None:
                    lines.append(f"  {p}: NONE")
                else:
                    lines.append(
                        f"  {p}: clubId={r['clubId']} "
                        f"catalog@{r['catalogNameAbs']} "
                        f"(nested_skip={r['catalogNameAbs'] != r['layoutAbs'] - len(r['iiName'].encode())})"
                    )

            lines.append("")
            lines.append("## optional: II job-list + Ermin calibration")
            jl = find_ii_job_list_with_job(mm, ERMIN_JOB, II_LIST_ABS)
            if jl:
                lines.append(
                    f"  job-list jobs@{jl['jobsAbs']} count={jl['count']} "
                    f"Ermin@{jl['jobIndex']} sample={jl['jobsSample']}"
                )
                lines.append(
                    "  note: clubId is NOT required as input to find this list; "
                    "spatial co-location of clubId↔list is weak on this probe "
                    "(~0.7MB apart). Next step: clubId → club/team object → "
                    "subunit header motif."
                )
            else:
                lines.append("  Ermin job-list not found on this bin")

            # club-ref motif sample for discovered id
            if hit:
                nb = struct.pack("<I", hit["clubId"])
                tag_64 = b"\x64\xff\x00" + nb
                th = find_all(mm, tag_64, limit=10)
                lines.append("")
                lines.append(
                    f"## club-ref sample: 64 ff 00 + clubId → hits={len(th)} {th[:5]}"
                )
                tag_010302 = b"\x01\x03\x02" + nb
                th2 = find_all(mm, tag_010302, limit=10)
                lines.append(f"  010302+clubId hits={len(th2)} (often 0 for II affiliates)")

        finally:
            mm.close()

    lines.append(f"\nelapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    return 0 if hit and (
        args.parent_short != PARENT_SHORT or hit["clubId"] == EXPECTED_SCHALKE_II
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
