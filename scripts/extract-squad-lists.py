#!/usr/bin/env python3
"""
T114 — Native MVP: clubIdAbs+488 namelist → Squad.

Native (00950e01) only, after identity:
  club UniqueID abs → +488 → u32 count → count × (lp32 UTF-8 name)

Unit label is `list` — not Senior / FT / II / U19. Do not claim squad type.

Continue (00950e02): honest empty list (no +488 assumption).

Refused:
  - T108 extract-first-team-fast revival
  - T110 fitted FT=25
  - T111 Senior object-path claim
  - HA / CA
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
# Fixed gap after identity club UniqueID → namelist count (T113 lock, five Careers).
CLUB_ID_NAMELIST_REL = 488
# Structural bounds only — not a fitted squad size.
NAME_COUNT_LO, NAME_COUNT_HI = 1, 500
NAME_LEN_LO, NAME_LEN_HI = 1, 80

_emt_spec = importlib.util.spec_from_file_location(
    "extract_managed_team", ROOT / "scripts" / "extract-managed-team.py"
)
_emt = importlib.util.module_from_spec(_emt_spec)
assert _emt_spec and _emt_spec.loader
_emt_spec.loader.exec_module(_emt)

refuse_live_fm_games_save = _emt.refuse_live_fm_games_save
discover_managed_club = _emt.discover_managed_club
pick_game_date_near_identity = _emt.pick_game_date_near_identity
catalog_long_name = _emt.catalog_long_name


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
    fd, name = tempfile.mkstemp(prefix="fmt-list-", suffix=".bin")
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


def read_lp32_name(mm: mmap.mmap | bytes, off: int) -> tuple[str, int] | None:
    """Return (name, bytes_consumed) for one length-prefixed UTF-8 name."""
    if off + 4 > len(mm):
        return None
    n = struct.unpack_from("<I", mm, off)[0]
    if not (NAME_LEN_LO <= n <= NAME_LEN_HI) or off + 4 + n > len(mm):
        return None
    raw = bytes(mm[off + 4 : off + 4 + n])
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not s or not s.isprintable() or not any(c.isalpha() for c in s):
        return None
    return s, 4 + n


def parse_club_id_plus488_namelist(
    mm: mmap.mmap | bytes, club_id_abs: int
) -> dict | None:
    """
    Native layout: clubIdAbs + 488 → u32 count → count × lp32 names.
    Returns None on structural miss (wrong count / truncated / bad names).
    """
    count_off = int(club_id_abs) + CLUB_ID_NAMELIST_REL
    if count_off < 0 or count_off + 4 > len(mm):
        return None
    count = struct.unpack_from("<I", mm, count_off)[0]
    if not (NAME_COUNT_LO <= count <= NAME_COUNT_HI):
        return None
    off = count_off + 4
    names: list[str] = []
    for _ in range(count):
        parsed = read_lp32_name(mm, off)
        if not parsed:
            return None
        name, consumed = parsed
        names.append(name)
        off += consumed
    return {
        "listAbs": count_off,
        "countHeader": count,
        "names": names,
        "endAbs": off,
    }


def players_from_names(names: list[str]) -> list[dict]:
    """Name rows only — synthetic jobId/uid for table merge; not real UniqueIDs."""
    players: list[dict] = []
    for i, name in enumerate(names):
        synth = i + 1
        players.append(
            {
                "jobId": synth,
                "uid": synth,
                "name": name,
                "kind": None,
                "ca": None,
                "pa": None,
                "dateOfBirth": None,
                "attributes": None,
                "attributeHistory": None,
                "loan": None,
                "_extract": {
                    "unit": "list",
                    "source": "native-clubid-plus488-v1",
                    "uidResolved": False,
                },
            }
        )
    return players


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
        "method": "native-clubid-plus488-v1",
        "tagHex": tag_hex,
        "identityAbs": identity["identityAbs"],
        "clubIdAbs": club_id_abs,
        "clubId": club_id,
        "layout": layout,
        "namelistRel": CLUB_ID_NAMELIST_REL,
        "unitLabel": "list",
        "refused": [
            "Senior / FT / II / U19 squad-type claim",
            "T108 extract-first-team-fast revival",
            "T110 fitted FT=25",
            "T111 Senior object-path claim",
            "HA/CA",
            "continue +488 assumption",
        ],
        **catalog_diag,
    }

    players: list[dict] = []
    if layout == "native":
        progress(
            t0,
            phase="resolve",
            message=f"Native namelist at clubIdAbs+{CLUB_ID_NAMELIST_REL}…",
            pct=80,
        )
        hit = parse_club_id_plus488_namelist(mm, club_id_abs)
        if hit:
            players = players_from_names(hit["names"])
            discovery["listAbs"] = hit["listAbs"]
            discovery["countHeader"] = hit["countHeader"]
            discovery["playersResolved"] = len(players)
            discovery["unitStatus"] = {"list": "clubIdAbs+488"}
            progress(
                t0,
                phase="players",
                message=f"list {len(players)} (count={hit['countHeader']})",
                pct=95,
                playersDone=len(players),
            )
        else:
            discovery["missReason"] = "native-clubid-plus488-miss"
            discovery["unitStatus"] = {"list": "miss"}
            progress(
                t0,
                phase="resolve",
                message="Native +488 namelist miss",
                pct=90,
                missReason=discovery["missReason"],
            )
    else:
        discovery["missReason"] = "continue-skip-native-plus488"
        discovery["unitStatus"] = {"list": "skipped-continue"}
        progress(
            t0,
            phase="resolve",
            message="Continue: skip +488 namelist",
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
            "discovery": {"unitStatus": "out-of-scope-t114"},
        },
        "u19": {
            "u19Name": "U19",
            "clubId": 0,
            "teamId": None,
            "listAbs": None,
            "countHeader": 0,
            "players": [],
            "discovery": {"unitStatus": "out-of-scope-t114"},
        },
        "listAbs": discovery.get("listAbs"),
        "countHeader": discovery.get("countHeader"),
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
                f"{len(result['players'])} list, "
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
