#!/usr/bin/env python3
"""
T118 — At-club Senior UniqueIDs → Squad (mentoring pool).

Native (00950e01) only, after identity:
  club UniqueID → `.dat` (`tad.`) → u32 count + person-internal ids
  → UniqueID via person `02 40` double
  → drop owned-out when person-intern sits in lookback of a loan-out template
  → resolve name via PERSON_NAME_MARK + name-table ids

Unit label is `senior` (at-club Senior / inbound). Not +488. No HA/CA. No II/U19.

Continue (00950e02): honest empty list.

Refused:
  - T114 +488 namelist as mentoring pool
  - T115 three-status UI / Bodø races
  - Hardcoding Santos UniqueIDs in extract law (gold = tests/fixtures)
"""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import struct
import sys
import tempfile
import time
from pathlib import Path

import zstandard as zstd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHUNK = 8 * 1024 * 1024
ZSTD_MAGIC = bytes.fromhex("28b52ffd")
TAG_NATIVE = "00950e01"
TAG_CONTINUE = "00950e02"

# Loan-out template (same motif as T086 / extract-first-team-fast).
LOAN_OUT_MOTIF_PREFIX = b"\x64\xff"
LOAN_OUT_PAD = b"\x00\x00\x00\x00\xff\xff\xff\xff\xff\x00\x00\x00\x00"
LOAN_KIND_LO, LOAN_KIND_HI = 0x20, 0x30
LOAN_LOOKBACK_LO, LOAN_LOOKBACK_HI = 8, 73
LOAN_TEMPLATE_LEN = 3 + 4 + 10 + 4 + 4 + 4 + 2
LOAN_CLUB_LO = 50
# Native host clubs can exceed the old 5e6 catalog ceiling (Moisés c1≈1.4e7).
LOAN_CLUB_HI = 50_000_000

# Native FM26 name table sits below the continue-career 100–160MB band.
NAME_TABLE_LO = 40 * 1024 * 1024
NAME_TABLE_HI = 90 * 1024 * 1024
PERSON_NAME_MARK = bytes.fromhex("01006c07")
PERSON_NAME_FIRST_OFF = 25
PERSON_NAME_SECOND_OFF = 30

_emt_spec = importlib.util.spec_from_file_location(
    "extract_managed_team", ROOT / "scripts" / "extract-managed-team.py"
)
_emt = importlib.util.module_from_spec(_emt_spec)
assert _emt_spec and _emt_spec.loader
_emt_spec.loader.exec_module(_emt)

_t115_spec = importlib.util.spec_from_file_location(
    "lock_santos_three_status", ROOT / "scripts" / "lock-santos-three-status.py"
)
_t115 = importlib.util.module_from_spec(_t115_spec)
assert _t115_spec and _t115_spec.loader
_t115_spec.loader.exec_module(_t115)

refuse_live_fm_games_save = _emt.refuse_live_fm_games_save
discover_managed_club = _emt.discover_managed_club
pick_game_date_near_identity = _emt.pick_game_date_near_identity
catalog_long_name = _emt.catalog_long_name
scan_person_doubles = _t115.scan_person_doubles
find_club_dat_intern_list = _t115.find_club_dat_intern_list

_NAME_ID_HITS: dict[int, dict[int, list[str]]] = {}


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


def probe_zstd_offset(save: Path) -> int | None:
    head = save.read_bytes()[:64]
    if len(head) > 30 and head[26:30] == ZSTD_MAGIC:
        return 26
    j = head.find(ZSTD_MAGIC)
    return j if j >= 0 else None


def decompress_to_temp(save: Path, t0: float) -> Path:
    zoff = probe_zstd_offset(save)
    if zoff is None:
        raise SystemExit("Unsupported .fm container — no zstd magic in header")
    fd, name = tempfile.mkstemp(prefix="fmt-senior-", suffix=".bin")
    os.close(fd)
    tmp = Path(name)
    out_bytes = 0
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zoff)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(CHUNK)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                out.write(block)
                out_bytes += len(block)
                if out_bytes == block.__len__() or out_bytes % (32 * 1024 * 1024) < CHUNK:
                    progress(
                        t0,
                        phase="decompress",
                        message="Decompressing save",
                        pct=min(70, 10 + out_bytes // (4 * 1024 * 1024)),
                        outBytes=out_bytes,
                    )
        finally:
            reader.close()
    return tmp


def _parse_loan_out_template(
    mm: mmap.mmap | bytes, motif_at: int, parent_club: int
) -> int | None:
    if motif_at + LOAN_TEMPLATE_LEN > len(mm):
        return None
    if motif_at < len(LOAN_OUT_PAD):
        return None
    if bytes(mm[motif_at - len(LOAN_OUT_PAD) : motif_at]) != LOAN_OUT_PAD:
        return None
    if bytes(mm[motif_at : motif_at + 2]) != LOAN_OUT_MOTIF_PREFIX:
        return None
    kind = mm[motif_at + 2]
    if not (LOAN_KIND_LO <= kind <= LOAN_KIND_HI):
        return None
    base = motif_at + 3
    if bytes(mm[base + 4 : base + 14]) != b"\x00" * 10:
        return None
    c1 = struct.unpack_from("<I", mm, base + 18)[0]
    c2 = struct.unpack_from("<I", mm, base + 22)[0]
    marker = struct.unpack_from("<H", mm, base + 26)[0]
    if (
        c1 != c2
        or c1 == parent_club
        or not (LOAN_CLUB_LO <= c1 <= LOAN_CLUB_HI)
        or marker != 0x000A
    ):
        return None
    return c1


def loaned_out_interns(
    mm: mmap.mmap | bytes, *, parent_club: int, intern_set: set[int]
) -> dict[int, int]:
    """person-intern → loanClubId when intern sits in loan-out lookback."""
    if not intern_set:
        return {}
    out: dict[int, int] = {}
    pos = 0
    while True:
        j = mm.find(LOAN_OUT_MOTIF_PREFIX, pos)
        if j < 0:
            break
        loan_club = _parse_loan_out_template(mm, j, parent_club)
        if loan_club is None:
            pos = j + 1
            continue
        for back in range(LOAN_LOOKBACK_LO, LOAN_LOOKBACK_HI + 1):
            start = j - back
            if start < 0:
                continue
            intern = struct.unpack_from("<I", mm, start)[0]
            if intern in intern_set and intern not in out:
                out[intern] = loan_club
                break
        pos = j + 1
    return out


def name_id_hits(buf: mmap.mmap | bytes, nid: int) -> list[str]:
    if nid <= 0 or nid >= 2_000_000:
        return []
    buf_key = id(buf)
    cache = _NAME_ID_HITS.get(buf_key)
    if cache is None:
        cache = {}
        _NAME_ID_HITS[buf_key] = cache
    cached = cache.get(nid)
    if cached is not None:
        return cached
    hi = min(NAME_TABLE_HI, len(buf))
    lo = min(NAME_TABLE_LO, hi)
    pat = struct.pack("<I", nid)
    hits: list[str] = []
    j = buf.find(pat, lo, hi)
    while j >= 0 and len(hits) < 8:
        if j + 8 <= len(buf):
            ln = struct.unpack_from("<I", buf, j + 4)[0]
            if 1 <= ln <= 48 and j + 8 + ln <= len(buf):
                raw = bytes(buf[j + 8 : j + 8 + ln])
                if raw and raw[:1].isalpha() and all(
                    b >= 0x20 or b == 0x09 for b in raw
                ):
                    try:
                        hits.append(raw.decode("utf-8"))
                    except UnicodeDecodeError:
                        pass
        j = buf.find(pat, j + 1, hi)
    cache[nid] = hits
    return hits


def lookup_name_id(buf: mmap.mmap | bytes, nid: int, *, surname: bool) -> str | None:
    hits = name_id_hits(buf, nid)
    if not hits:
        return None
    if surname:
        return hits[1] if len(hits) > 1 else hits[0]
    return hits[0]


def resolve_name_from_mark(
    buf: mmap.mmap | bytes, person_abs: int
) -> str | None:
    lo = max(0, person_abs - 2048)
    region = bytes(buf[lo:person_abs])
    marks: list[int] = []
    start = 0
    while True:
        rel = region.find(PERSON_NAME_MARK, start)
        if rel < 0:
            break
        marks.append(lo + rel)
        start = rel + 1
    for mark in sorted(marks, reverse=True):
        if mark + PERSON_NAME_SECOND_OFF + 4 > len(buf):
            continue
        fid = struct.unpack_from("<I", buf, mark + PERSON_NAME_FIRST_OFF)[0]
        sid = struct.unpack_from("<I", buf, mark + PERSON_NAME_SECOND_OFF)[0]
        if fid == 0 or sid == 0 or fid > 2_000_000 or sid > 2_000_000:
            continue
        first = lookup_name_id(buf, fid, surname=False)
        second = lookup_name_id(buf, sid, surname=True)
        if first and second:
            return f"{first} {second}"
        if second or first:
            return second or first
    return None


def players_from_club_dat(
    mm: mmap.mmap | bytes,
    *,
    club_id: int,
) -> tuple[list[dict], dict]:
    """Club `.dat` intern list → at-club Senior rows (UniqueID + name)."""
    persons = scan_person_doubles(mm)
    club_list = find_club_dat_intern_list(mm, club_id, persons)
    diag: dict = {
        "personDoubles": len(persons),
        "clubDatList": None,
        "loanedOutDropped": [],
    }
    if not club_list:
        return [], {**diag, "missReason": "club-dat-intern-list-miss"}

    intern_set = {int(row["intern"]) for row in club_list["players"]}
    outbound = loaned_out_interns(mm, parent_club=club_id, intern_set=intern_set)
    diag["clubDatList"] = {
        "tadAbs": club_list.get("tadAbs"),
        "countAbs": club_list.get("countAbs"),
        "count": club_list["count"],
    }

    players: list[dict] = []
    for row in club_list["players"]:
        intern = int(row["intern"])
        uid = int(row["uid"])
        if intern in outbound:
            diag["loanedOutDropped"].append(
                {"uid": uid, "intern": intern, "loanClubId": outbound[intern]}
            )
            continue
        name = resolve_name_from_mark(mm, int(row["personAbs"])) or f"uid:{uid}"
        players.append(
            {
                "jobId": uid,
                "uid": uid,
                "name": name,
                "kind": None,
                "ca": None,
                "pa": None,
                "dateOfBirth": None,
                "attributes": None,
                "attributeHistory": None,
                "loan": None,
                "_extract": {
                    "unit": "senior",
                    "source": "native-club-dat-senior-v1",
                    "uidResolved": True,
                    "intern": intern,
                },
            }
        )
    return players, diag


def extract_from_mmap(mm: mmap.mmap | bytes, *, save: Path, t0: float) -> dict:
    progress(t0, phase="identity", message="Discovering managed club…", pct=72)
    identity = discover_managed_club(mm, len(mm))
    if not identity:
        raise SystemExit("Managed club identity not found")

    club_id = int(identity["clubId"])
    club_short = identity["clubNameShort"]
    tag_hex = identity["tagHex"]
    club_id_abs = int(identity.get("clubIdAbs") or identity["identityAbs"])
    long_name, catalog_diag = catalog_long_name(mm, club_short)
    club_name = long_name or club_short
    date_pick = pick_game_date_near_identity(mm, identity)
    game_date = date_pick.get("gameDate") if date_pick else None
    layout = "native" if tag_hex == TAG_NATIVE else "continue"

    progress(
        t0,
        phase="identity",
        message=f"club={club_name} id={club_id}",
        pct=74,
        layout=layout,
        tagHex=tag_hex,
    )

    discovery: dict = {
        "method": "native-club-dat-senior-v1",
        "tagHex": tag_hex,
        "identityAbs": identity["identityAbs"],
        "clubIdAbs": club_id_abs,
        "clubId": club_id,
        "layout": layout,
        "unitLabel": "senior",
        "refused": [
            "T114 +488 namelist as mentoring pool",
            "T115 three-status UI",
            "II/U19 lists",
            "HA/CA",
            "continue club-dat assumption",
            "hardcoded Santos UniqueIDs in extract law",
        ],
        **catalog_diag,
    }

    players: list[dict] = []
    if layout == "native":
        progress(
            t0,
            phase="resolve",
            message="Native club .dat Senior UniqueIDs…",
            pct=80,
        )
        players, list_diag = players_from_club_dat(mm, club_id=club_id)
        discovery.update(list_diag)
        if players:
            discovery["playersResolved"] = len(players)
            discovery["unitStatus"] = {"senior": "club-dat-at-club"}
            progress(
                t0,
                phase="players",
                message=(
                    f"senior {len(players)} "
                    f"(dropped outbound {len(discovery.get('loanedOutDropped') or [])})"
                ),
                pct=95,
                playersDone=len(players),
            )
        else:
            discovery["missReason"] = list_diag.get(
                "missReason", "native-club-dat-senior-empty"
            )
            discovery["unitStatus"] = {"senior": "miss"}
            progress(
                t0,
                phase="resolve",
                message="Native club .dat Senior miss",
                pct=90,
                missReason=discovery["missReason"],
            )
    else:
        discovery["missReason"] = "continue-skip-native-club-dat"
        discovery["unitStatus"] = {"senior": "skipped-continue"}
        progress(
            t0,
            phase="resolve",
            message="Continue: skip native club .dat Senior",
            pct=90,
            missReason=discovery["missReason"],
        )

    return {
        "savePath": str(save),
        "saveName": save.name,
        "clubId": club_id,
        "teamId": club_id,
        "clubName": club_name,
        "clubNameShort": club_short,
        "gameDate": game_date,
        "tagHex": tag_hex,
        "players": players,
        "reserves": {
            "iiName": "Reserve",
            "clubId": 0,
            "teamId": None,
            "listAbs": None,
            "countHeader": 0,
            "players": [],
            "discovery": {"unitStatus": "out-of-scope-t118"},
        },
        "u19": {
            "u19Name": "U19",
            "clubId": 0,
            "teamId": None,
            "listAbs": None,
            "countHeader": 0,
            "players": [],
            "discovery": {"unitStatus": "out-of-scope-t118"},
        },
        "listAbs": (discovery.get("clubDatList") or {}).get("countAbs"),
        "countHeader": len(players) if players else discovery.get("clubDatList", {}).get("count"),
        "metaOnly": False,
        "discovery": discovery,
        "elapsedMs": int((time.perf_counter() - t0) * 1000),
    }


def main() -> int:
    if len(sys.argv) < 2:
        return fail(time.perf_counter(), "Usage: extract-squad-lists.py <save.fm>")
    save = Path(sys.argv[1])
    if not save.is_file():
        return fail(time.perf_counter(), f"Save not found: {save}")
    refuse_live_fm_games_save(save)
    t0 = time.perf_counter()
    progress(t0, phase="start", message=f"Opening {save.name}", pct=0)
    tmp: Path | None = None
    try:
        tmp = decompress_to_temp(save, t0)
        with tmp.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            result = extract_from_mmap(mm, save=save, t0=t0)
        progress(
            t0,
            phase="done",
            message=(
                f"{len(result['players'])} senior, "
                f"gameDate={result.get('gameDate')}, "
                f"miss={result.get('discovery', {}).get('missReason')}"
            ),
            pct=100,
        )
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    except SystemExit as e:
        msg = str(e) if e.args else "extract failed"
        return fail(t0, msg)
    finally:
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
