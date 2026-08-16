#!/usr/bin/env python3
"""
T110 — First-principles squad lists (native FM26 first).

Recipe (native tag 00950e01):
  1) Managed-club identity (extract-managed-team)
  2) Shortly after identityAbs: u32 count → count × lp32 names
  3) Canonical FT rows = non-abbreviated names + abbreviated surnames not
     already covered (full then "J. Smith" tail is the common native shape)
  4) II / U19: not in this neighborhood yet → empty units + diagnostic
  5) No HA / CA / loans

Continue (00950e02): identity only + honest `continue-squad-lists-not-yet`
(no T108-style fitted job lists).
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
# Bounded window after identity — not a fitted save offset.
NAME_LIST_WINDOW = 4096
COUNT_LO, COUNT_HI = 12, 60

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
    fd, name = tempfile.mkstemp(prefix="fmt-squad-", suffix=".bin")
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


def read_lp32(mm: mmap.mmap | bytes, off: int) -> tuple[str | None, int]:
    if off + 4 > len(mm):
        return None, off
    n = struct.unpack_from("<I", mm, off)[0]
    if not (1 <= n <= 80) or off + 4 + n > len(mm):
        return None, off
    raw = bytes(mm[off + 4 : off + 4 + n])
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, off
    if not s.isprintable():
        return None, off
    return s, off + 4 + n


def parse_n_names(
    mm: mmap.mmap | bytes, start: int, count: int
) -> tuple[list[dict] | None, int]:
    names: list[dict] = []
    off = start
    for _ in range(count):
        s, nxt = read_lp32(mm, off)
        if s is None:
            return None, off
        names.append({"name": s, "abs": off})
        off = nxt
    return names, off


def name_quality_ok(name: str) -> bool:
    if not name or not any(c.isalpha() for c in name):
        return False
    ok = sum(c.isalpha() or c.isspace() or c in "-'." for c in name)
    return ok >= len(name) * 0.6


def is_abbreviated_name(name: str) -> bool:
    """Native lists often end with 'J. Smith' / 'V. van Dijk' forms."""
    parts = name.split()
    if not parts:
        return True
    first = parts[0]
    return len(first) <= 2 and first.endswith(".")


def find_native_identity_namelist(
    mm: mmap.mmap | bytes, identity_abs: int
) -> dict | None:
    """u32 count then lp32 names in a short window after identity."""
    lo = identity_abs
    hi = min(len(mm), identity_abs + NAME_LIST_WINDOW)
    best: dict | None = None
    best_key: tuple | None = None
    for off in range(lo, hi - 8):
        cnt = struct.unpack_from("<I", mm, off)[0]
        if not (COUNT_LO <= cnt <= COUNT_HI):
            continue
        parsed, end = parse_n_names(mm, off + 4, cnt)
        if not parsed:
            continue
        good = sum(1 for item in parsed if name_quality_ok(item["name"]))
        if good < cnt * 0.75:
            continue
        full_head = sum(
            1
            for item in parsed[: max(1, cnt // 2)]
            if not is_abbreviated_name(item["name"]) and name_quality_ok(item["name"])
        )
        # Prefer lists with several real names early; then closer to +520.
        key = (full_head, -abs(off - (identity_abs + 520)), cnt)
        if best is None or best_key is None or key > best_key:
            best_key = key
            best = {
                "countAbs": off,
                "namesAbs": off + 4,
                "endAbs": end,
                "count": cnt,
                "delta": off - identity_abs,
                "names": parsed,
            }
    return best


def canonical_ft_names(raw_names: list[str]) -> list[str]:
    """
    Prefer full names; keep abbreviated rows only when surname not already
    covered (Salah / Robertson often appear only in the abbr tail).
    """
    full = [n for n in raw_names if not is_abbreviated_name(n)]
    covered = {n.split()[-1].casefold() for n in full if n.strip()}
    out = list(full)
    for n in raw_names:
        if not is_abbreviated_name(n):
            continue
        sur = n.split()[-1].casefold() if n.split() else ""
        if sur and sur not in covered:
            out.append(n)
            covered.add(sur)
    # Drop empties / pure junk
    return [n for n in out if name_quality_ok(n)]


def uid_near_lp32_name(mm: mmap.mmap | bytes, name: str) -> int | None:
    """Best-effort person double near an lp32 name hit (optional)."""
    raw = name.encode("utf-8")
    needle = struct.pack("<I", len(raw)) + raw
    start = 0
    hits = 0
    while hits < 24:
        j = mm.find(needle, start)
        if j < 0:
            break
        hits += 1
        for lo, hi in (
            (max(0, j - 96), j),
            (j + len(needle), min(len(mm), j + len(needle) + 96)),
        ):
            off = lo
            while off + 8 <= hi:
                u1 = struct.unpack_from("<I", mm, off)[0]
                u2 = struct.unpack_from("<I", mm, off + 4)[0]
                if u1 == u2 and 1_500_000_000 <= u1 <= 2_200_000_000:
                    return int(u1)
                off += 1
        start = j + 1
    return None


def empty_unit(name: str) -> dict:
    return {
        "name": name,
        "clubId": None,
        "teamId": None,
        "listAbs": None,
        "countHeader": 0,
        "players": [],
        "discovery": {
            "method": "native-identity-namelist-v1",
            "unitStatus": "not-in-identity-neighborhood",
        },
    }


def build_player(name: str, uid: int | None, *, job_id: int) -> dict:
    return {
        "jobId": job_id,
        "uid": int(uid or 0),
        "name": name,
        "kind": None,
        "ca": None,
        "pa": None,
        "dateOfBirth": None,
        "attributes": None,
        "attributeHistory": None,
        "loan": None,
        "_extract": {
            "unit": "FT",
            "source": "native-identity-namelist-v1",
            "uidResolved": bool(uid),
        },
    }


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

    progress(
        t0,
        phase="identity",
        message=f"club={club_name} id={club_id}",
        pct=74,
        layout="native" if tag_hex == TAG_NATIVE else "continue",
        tagHex=tag_hex,
    )

    discovery: dict = {
        "method": "native-identity-namelist-v1",
        "tagHex": tag_hex,
        "identityAbs": identity["identityAbs"],
        "clubId": club_id,
        "layout": "native" if tag_hex == TAG_NATIVE else "continue",
        **catalog_diag,
    }

    players: list[dict] = []
    reserves = empty_unit("II")
    u19 = empty_unit("U19")

    if tag_hex != TAG_NATIVE:
        discovery["missReason"] = "continue-squad-lists-not-yet"
        discovery["unitStatus"] = {
            "FT": "continue-not-yet",
            "II": "continue-not-yet",
            "U19": "continue-not-yet",
        }
        progress(
            t0,
            phase="resolve",
            message="Continue layout: squad lists not yet (native-first lock)",
            pct=90,
            missReason=discovery["missReason"],
        )
    else:
        progress(t0, phase="resolve", message="Native identity namelist…", pct=78)
        lst = find_native_identity_namelist(mm, int(identity["identityAbs"]))
        if not lst:
            discovery["missReason"] = "native-identity-namelist-miss"
            discovery["unitStatus"] = {
                "FT": "miss",
                "II": "not-in-identity-neighborhood",
                "U19": "not-in-identity-neighborhood",
            }
            progress(
                t0,
                phase="resolve",
                message="Native namelist miss",
                pct=90,
                missReason=discovery["missReason"],
            )
        else:
            raw = [item["name"] for item in lst["names"]]
            canon = canonical_ft_names(raw)
            discovery.update(
                {
                    "countAbs": lst["countAbs"],
                    "namesAbs": lst["namesAbs"],
                    "listDelta": lst["delta"],
                    "rawCount": lst["count"],
                    "ftCanonical": len(canon),
                    "unitStatus": {
                        "FT": "identity-namelist",
                        "II": "not-in-identity-neighborhood",
                        "U19": "not-in-identity-neighborhood",
                    },
                }
            )
            for i, name in enumerate(canon):
                uid = uid_near_lp32_name(mm, name)
                players.append(build_player(name, uid, job_id=i + 1))
            progress(
                t0,
                phase="players",
                message=f"FT namelist {len(players)} (raw {lst['count']})",
                pct=95,
                playersDone=len(players),
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
        "reserves": reserves,
        "u19": u19,
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
                f"{len(result['players'])} FT names, "
                f"II/U19 pending, gameDate={result.get('gameDate')}"
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
            tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
