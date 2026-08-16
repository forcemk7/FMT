#!/usr/bin/env python3
"""
T111 — Senior Squad via object path (native FM26 first).

Required shape:
  managed club UniqueID
    → squad object(s) attached to that club (structural — not ~±N namelist)
    → pick Senior Squad object
    → player UniqueIDs
    → display names

This ticket does **not** revive:
  - T110 identity-neighborhood namelist (~+520 / clubIdAbs+488)
  - T108 extract-first-team-fast fitted MVP

Continue (00950e02): try club-object PRE_NAME → teamId → 7f02 job-list when present.
Native (00950e01): same object join; if no squad object → honest miss + dump
(not a fake FT count).
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
DUMP_DIR = ROOT / "tmp" / "identity"
SENIOR_LABELS = (
    "Senior Squad",
    "First Team Squad",
    "First Team",
    "Senior",
)

_emt_spec = importlib.util.spec_from_file_location(
    "extract_managed_team", ROOT / "scripts" / "extract-managed-team.py"
)
_emt = importlib.util.module_from_spec(_emt_spec)
assert _emt_spec and _emt_spec.loader
_emt_spec.loader.exec_module(_emt)

_ft_spec = importlib.util.spec_from_file_location(
    "ft_squad_discovery", ROOT / "scripts" / "ft_squad_discovery.py"
)
_ft = importlib.util.module_from_spec(_ft_spec)
assert _ft_spec and _ft_spec.loader
_ft_spec.loader.exec_module(_ft)

refuse_live_fm_games_save = _emt.refuse_live_fm_games_save
discover_managed_club = _emt.discover_managed_club
pick_game_date_near_identity = _emt.pick_game_date_near_identity
catalog_long_name = _emt.catalog_long_name
resolve_ft_squad = _ft.resolve_ft_squad


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


def read_lp32(mm: mmap.mmap | bytes, off: int) -> str | None:
    if off + 4 > len(mm):
        return None
    n = struct.unpack_from("<I", mm, off)[0]
    if not (1 <= n <= 80) or off + 4 + n > len(mm):
        return None
    raw = bytes(mm[off + 4 : off + 4 + n])
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return s if s.isprintable() else None


def resolve_name_for_uid(mm: mmap.mmap | bytes, uid: int) -> str | None:
    """Person-double uid|uid then nearby lp32 display name."""
    pair = struct.pack("<II", int(uid), int(uid))
    start = 0
    for _ in range(24):
        j = mm.find(pair, start)
        if j < 0:
            break
        for off in range(max(0, j - 220), j):
            name = read_lp32(mm, off)
            if not name or not any(c.isalpha() for c in name):
                continue
            if " " in name or len(name) >= 5:
                return name
        start = j + 1
    return None


def job_to_uid(mm: mmap.mmap | bytes, job_id: int, *, limit: int = 20) -> int | None:
    """Employment motif: XX 02 <jobId> 02 <UniqueID>."""
    needle = struct.pack("<I", int(job_id))
    start = 0
    hits = 0
    while hits < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        hits += 1
        if j >= 1 and j + 9 <= len(mm) and mm[j - 1] == 0x02 and mm[j + 4] == 0x02:
            uid = struct.unpack_from("<I", mm, j + 5)[0]
            if 5_000 <= uid <= 2_300_000_000:
                return int(uid)
        start = j + 1
    return None


def scan_native_senior_label(mm: mmap.mmap | bytes, club_id: int) -> dict:
    """Look for native squad label strings near this club UniqueID (diagnostic only)."""
    cid = struct.pack("<I", int(club_id))
    out: dict = {"labels": [], "clubIdNearLabel": []}
    for lab in SENIOR_LABELS:
        raw = lab.encode("utf-8")
        start = 0
        found = 0
        while found < 8:
            j = mm.find(raw, start)
            if j < 0:
                break
            lp32 = j >= 4 and struct.unpack_from("<I", mm, j - 4)[0] == len(raw)
            out["labels"].append({"label": lab, "abs": j, "lp32": bool(lp32)})
            lo = max(0, j - 2048)
            if cid in bytes(mm[lo : j + 64]):
                out["clubIdNearLabel"].append({"label": lab, "abs": j})
            found += 1
            start = j + 1
    return out


def players_from_job_list(
    mm: mmap.mmap | bytes, jobs: list[int], *, squad_label: str
) -> list[dict]:
    players: list[dict] = []
    for i, job in enumerate(jobs):
        uid = job_to_uid(mm, int(job))
        name = resolve_name_for_uid(mm, uid) if uid else None
        if not name or not uid:
            continue
        players.append(
            {
                "jobId": int(job),
                "uid": int(uid),
                "name": name,
                "kind": None,
                "ca": None,
                "pa": None,
                "dateOfBirth": None,
                "attributes": None,
                "attributeHistory": None,
                "loan": None,
                "_extract": {
                    "unit": "Senior",
                    "squadLabel": squad_label,
                    "source": "club-squad-object-v1",
                    "uidResolved": True,
                },
            }
        )
    # Dedupe by uid, keep first
    seen: set[int] = set()
    uniq: list[dict] = []
    for p in players:
        u = int(p["uid"])
        if u in seen:
            continue
        seen.add(u)
        uniq.append(p)
    return uniq


def pick_squad_label(mm: mmap.mmap | bytes, label_scan: dict) -> str:
    """Prefer an in-save label when lp32-attached; else Senior."""
    for row in label_scan.get("labels") or []:
        if row.get("lp32") and row.get("label") in ("Senior Squad", "First Team Squad", "Senior"):
            return str(row["label"])
    return "Senior"


def write_miss_dump(save: Path, discovery: dict) -> str | None:
    try:
        DUMP_DIR.mkdir(parents=True, exist_ok=True)
        path = DUMP_DIR / f"t111-senior-miss-{save.stem}.json"
        path.write_text(json.dumps(discovery, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)
    except OSError:
        return None


def extract_from_mmap(mm: mmap.mmap | bytes, *, save: Path, t0: float) -> dict:
    progress(t0, phase="identity", message="Discovering managed club…", pct=72)
    identity = discover_managed_club(mm, len(mm))
    if not identity:
        raise SystemExit("Managed club identity not found")

    club_id = int(identity["clubId"])
    club_short = identity["clubNameShort"]
    tag_hex = identity["tagHex"]
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

    object_path = [
        "managed club UniqueID (identity)",
        "club object attachment (PRE_NAME → teamId/dup when present)",
        "squad job-list (7f02 / 010302 on team body)",
        "jobId → employment → player UniqueID → name",
    ]

    discovery: dict = {
        "method": "senior-squad-object-v1",
        "objectPath": object_path,
        "tagHex": tag_hex,
        "identityAbs": identity["identityAbs"],
        "clubIdAbs": identity.get("clubIdAbs"),
        "clubId": club_id,
        "layout": layout,
        "refused": [
            "T110 identity-neighborhood namelist",
            "T108 extract-first-team-fast revival",
            "invented FT=25 / fitted counts",
        ],
        **catalog_diag,
    }

    progress(t0, phase="resolve", message="Senior Squad object join…", pct=80)
    label_scan = scan_native_senior_label(mm, club_id)
    discovery["labelScan"] = {
        "labelHitCount": len(label_scan.get("labels") or []),
        "clubIdNearLabelCount": len(label_scan.get("clubIdNearLabel") or []),
        "sample": (label_scan.get("labels") or [])[:8],
    }
    squad_label = pick_squad_label(mm, label_scan)
    discovery["squadLabel"] = squad_label

    ft_hit = resolve_ft_squad(mm, club_short, club_id)
    discovery["clubObjectJoin"] = {
        "catalogHits": None if not ft_hit else ft_hit.get("catalogHits"),
        "teamObjects": None if not ft_hit else ft_hit.get("teamObjects"),
        "jobsFound": None if not ft_hit else ft_hit.get("jobsFound"),
        "teamId": None if not ft_hit else (ft_hit.get("team") or {}).get("teamId"),
        "listCount": None
        if not ft_hit or not ft_hit.get("list")
        else ft_hit["list"].get("count"),
        "persistTid": None
        if not ft_hit or not ft_hit.get("list")
        else ft_hit["list"].get("persistTid"),
    }

    players: list[dict] = []
    team_id = club_id
    if ft_hit and ft_hit.get("list") and ft_hit["list"].get("jobs"):
        jobs = list(ft_hit["list"]["jobs"])
        players = players_from_job_list(mm, jobs, squad_label=squad_label)
        team_id = int((ft_hit.get("team") or {}).get("teamId") or club_id)
        discovery["unitStatus"] = {
            "Senior": "club-object-job-list" if players else "jobs-unresolved",
            "Reserve": "out-of-scope",
            "U19": "out-of-scope",
        }
        discovery["jobsOnList"] = len(jobs)
        discovery["playersResolved"] = len(players)
        if not players:
            discovery["missReason"] = "senior-jobs-name-uid-unresolved"
    else:
        discovery["missReason"] = (
            "senior-squad-object-miss"
            if layout == "native"
            else "continue-senior-squad-object-miss"
        )
        discovery["unitStatus"] = {
            "Senior": "miss",
            "Reserve": "out-of-scope",
            "U19": "out-of-scope",
        }

    if not players:
        dump_path = write_miss_dump(save, discovery)
        if dump_path:
            discovery["missDump"] = dump_path
        progress(
            t0,
            phase="resolve",
            message=f"Senior miss: {discovery.get('missReason')}",
            pct=90,
            missReason=discovery.get("missReason"),
        )
    else:
        progress(
            t0,
            phase="players",
            message=f"Senior {len(players)} ({squad_label})",
            pct=95,
            playersDone=len(players),
        )

    return {
        "savePath": str(save),
        "saveName": save.name,
        "clubId": club_id,
        "teamId": team_id,
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
            "discovery": {"unitStatus": "out-of-scope-t111"},
        },
        "u19": {
            "u19Name": "U19",
            "clubId": 0,
            "teamId": None,
            "listAbs": None,
            "countHeader": 0,
            "players": [],
            "discovery": {"unitStatus": "out-of-scope-t111"},
        },
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
                f"{len(result['players'])} Senior, "
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
