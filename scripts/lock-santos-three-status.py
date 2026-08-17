#!/usr/bin/env python3
"""
T115 — Santos three-status lock (native gameDate8 only).

Structural path:
  identity club UniqueID
    → club `.dat` object (`tad.` blob that contains that UniqueID)
    → u32 count + person-internal ids
    → person record `02 40` … internal … UniqueID||UniqueID

That club list is FM Senior **32** (28 owned-at-club + 3 inbound + Moisés).
The other **10** owned-out UniqueIDs exist as person doubles in the save but
are not referenced from this club object. Three-status split is not locked.

Gold UniqueIDs live in tests/fixtures — not extract-*.py law.
Do not ship UI. Do not treat +488 as Senior.
"""

from __future__ import annotations

import importlib.util
import json
import mmap
import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
ZSTD_MAGIC = bytes.fromhex("28b52ffd")
CHUNK = 8 * 1024 * 1024
TAD_MARK = b"tad."
PERSON_02_40 = bytes.fromhex("0240")
CLUB_LIST_COUNT_LO, CLUB_LIST_COUNT_HI = 8, 80
TAD_LOOKBACK = 80_000
TAD_SPAN = 80_000

_emt_spec = importlib.util.spec_from_file_location(
    "extract_managed_team", ROOT / "scripts" / "extract-managed-team.py"
)
_emt = importlib.util.module_from_spec(_emt_spec)
assert _emt_spec and _emt_spec.loader
_emt_spec.loader.exec_module(_emt)

refuse_live_fm_games_save = _emt.refuse_live_fm_games_save
discover_managed_club = _emt.discover_managed_club


def load_gold(path: Path | None = None) -> dict:
    p = path or (ROOT / "tests" / "fixtures" / "t115-santos-gold.json")
    return json.loads(p.read_text(encoding="utf-8"))


def decompress_to_temp(save: Path) -> Path:
    head = save.read_bytes()[:64]
    zoff = 26 if len(head) > 30 and head[26:30] == ZSTD_MAGIC else head.find(ZSTD_MAGIC)
    if zoff < 0:
        raise SystemExit("Unsupported .fm container — no zstd magic in header")
    fd, name = tempfile.mkstemp(prefix="fmt-t115-", suffix=".bin")
    os.close(fd)
    tmp = Path(name)
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
        finally:
            reader.close()
    return tmp


def scan_person_doubles(mm: mmap.mmap | bytes) -> dict[int, dict]:
    """
    intern → {uid, personAbs, internAbs}.
    Layout: 02 40 | kind | sub | 00×3 | intern u32 | uid u32 | uid u32.
    """
    out: dict[int, dict] = {}
    n = len(mm)
    start = 0
    while True:
        j = mm.find(PERSON_02_40, start)
        if j < 0:
            break
        base = j + 2
        if base + 17 > n:
            break
        kind, sub = mm[base], mm[base + 1]
        if kind not in (0x10, 0x18) or sub not in (0x04, 0x05):
            start = j + 1
            continue
        if bytes(mm[base + 2 : base + 5]) != b"\x00\x00\x00":
            start = j + 1
            continue
        intern = struct.unpack_from("<I", mm, base + 5)[0]
        u1 = struct.unpack_from("<I", mm, base + 9)[0]
        u2 = struct.unpack_from("<I", mm, base + 13)[0]
        if intern == 0 or u1 == 0 or u1 != u2:
            start = j + 1
            continue
        if intern not in out:
            out[intern] = {
                "uid": u1,
                "personAbs": j,
                "internAbs": base + 5,
            }
        start = j + 1
    return out


def resolve_uid(persons: dict[int, dict], intern: int) -> int | None:
    rec = persons.get(intern)
    return int(rec["uid"]) if rec else None


def parse_intern_list(
    mm: mmap.mmap | bytes, count_at: int, persons: dict[int, dict]
) -> dict | None:
    if count_at < 0 or count_at + 4 > len(mm):
        return None
    count = struct.unpack_from("<I", mm, count_at)[0]
    if not (CLUB_LIST_COUNT_LO <= count <= CLUB_LIST_COUNT_HI):
        return None
    jobs_at = count_at + 4
    if jobs_at + 4 * count > len(mm):
        return None
    intern_ids = [
        struct.unpack_from("<I", mm, jobs_at + 4 * k)[0] for k in range(count)
    ]
    mapped = []
    for intern in intern_ids:
        uid = resolve_uid(persons, intern)
        if uid is None:
            return None
        mapped.append({"intern": intern, "uid": uid, "personAbs": persons[intern]["personAbs"]})
    return {
        "countAbs": count_at,
        "count": count,
        "interns": intern_ids,
        "players": mapped,
    }


def find_club_dat_intern_list(
    mm: mmap.mmap | bytes,
    club_id: int,
    persons: dict[int, dict],
) -> dict | None:
    """Club UniqueID hit → previous tad. → count-prefixed person-internal list."""
    packed = struct.pack("<I", int(club_id))
    intern_set = set(persons)
    tad_starts: set[int] = set()
    start = 0
    while True:
        hit = mm.find(packed, start)
        if hit < 0:
            break
        lo = max(0, hit - TAD_LOOKBACK)
        rel = bytes(mm[lo:hit]).rfind(TAD_MARK)
        if rel >= 0:
            tad_starts.add((lo + rel, hit))
        start = hit + 1
    best: dict | None = None
    seen_tad: set[int] = set()
    for tad_at, club_hit in sorted(tad_starts):
        if tad_at in seen_tad:
            continue
        seen_tad.add(tad_at)
        span_hi = min(len(mm), tad_at + TAD_SPAN)
        p = tad_at
        while p + 8 <= span_hi:
            c = struct.unpack_from("<I", mm, p)[0]
            if CLUB_LIST_COUNT_LO <= c <= CLUB_LIST_COUNT_HI and p + 4 + 4 * c <= span_hi:
                first = struct.unpack_from("<I", mm, p + 4)[0]
                if first in intern_set:
                    parsed = parse_intern_list(mm, p, persons)
                    if parsed and parsed["count"] >= 8:
                        parsed["tadAbs"] = tad_at
                        parsed["clubIdAbsInDat"] = club_hit
                        if best is None or parsed["count"] > best["count"]:
                            best = parsed
                        p += 4 + 4 * parsed["count"]
                        continue
            p += 1
    return best


def classify_against_gold(list_uids: set[int], gold: dict) -> dict:
    """Record list membership vs gold. Not a shipped three-status recipe."""
    by_status = {k: set(int(x) for x in gold[k].keys()) for k in (
        "owned_at_club",
        "owned_out_on_loan",
        "inbound_loan",
    )}
    names = {}
    for table in gold.values():
        if isinstance(table, dict):
            for uid, name in table.items():
                try:
                    names[int(uid)] = name
                except (TypeError, ValueError):
                    pass
    in_list = {
        "owned_at_club": sorted(by_status["owned_at_club"] & list_uids),
        "owned_out_on_loan": sorted(by_status["owned_out_on_loan"] & list_uids),
        "inbound_loan": sorted(by_status["inbound_loan"] & list_uids),
    }
    missing_from_list = {
        "owned_at_club": sorted(by_status["owned_at_club"] - list_uids),
        "owned_out_on_loan": sorted(by_status["owned_out_on_loan"] - list_uids),
        "inbound_loan": sorted(by_status["inbound_loan"] - list_uids),
    }
    return {
        "inClubSeniorList": in_list,
        "missingFromClubSeniorList": missing_from_list,
        "names": names,
    }


def lock_from_mmap(mm: mmap.mmap | bytes, *, gold: dict | None = None) -> dict:
    gold = gold or load_gold()
    identity = discover_managed_club(mm, min(len(mm), 64 * 1024 * 1024))
    if not identity:
        raise SystemExit("Managed club identity not found")
    club_id = int(identity["clubId"])
    persons = scan_person_doubles(mm)
    uid_to_person = {int(p["uid"]): {**p, "intern": intern} for intern, p in persons.items()}
    gold_uids = set()
    gold_names = {}
    for key in ("owned_at_club", "owned_out_on_loan", "inbound_loan"):
        for uid_s, name in gold[key].items():
            uid = int(uid_s)
            gold_uids.add(uid)
            gold_names[uid] = name

    found_gold = []
    missing_gold = []
    for uid in sorted(gold_uids):
        rec = uid_to_person.get(uid)
        if rec:
            found_gold.append(
                {
                    "uid": uid,
                    "name": gold_names[uid],
                    "intern": rec["intern"],
                    "personAbs": rec["personAbs"],
                }
            )
        else:
            missing_gold.append({"uid": uid, "name": gold_names[uid]})

    club_list = find_club_dat_intern_list(mm, club_id, persons)
    list_uids = set()
    list_rows = []
    if club_list:
        for row in club_list["players"]:
            uid = int(row["uid"])
            list_uids.add(uid)
            list_rows.append(
                {
                    "uid": uid,
                    "intern": row["intern"],
                    "name": gold_names.get(uid, ""),
                    "personAbs": row["personAbs"],
                    "inGold": uid in gold_uids,
                }
            )
    vs_gold = classify_against_gold(list_uids, gold) if gold_uids else None
    return {
        "clubId": club_id,
        "clubIdAbs": identity.get("clubIdAbs"),
        "clubNameShort": identity.get("clubNameShort"),
        "tagHex": identity.get("tagHex"),
        "personDoubles": len(persons),
        "goldFound": found_gold,
        "goldMissingPersonDouble": missing_gold,
        "clubSeniorList": {
            "tadAbs": club_list.get("tadAbs") if club_list else None,
            "countAbs": club_list.get("countAbs") if club_list else None,
            "count": club_list.get("count") if club_list else 0,
            "clubIdAbsInDat": club_list.get("clubIdAbsInDat") if club_list else None,
            "players": list_rows,
        },
        "vsGold": vs_gold,
        "blocked": {
            "reason": (
                "club .dat intern list is FM Senior 32 (28 white + 3 inbound + Moisés); "
                "10 owned-out UniqueIDs are not referenced from that object; "
                "no structural three-status discriminator"
            ),
            "ownedOutMissingFromClubList": (
                vs_gold["missingFromClubSeniorList"]["owned_out_on_loan"]
                if vs_gold
                else []
            ),
        },
    }


def write_dump(result: dict, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# T115 — Santos three-status lock (gameDate8 native)",
        "",
        f"club {result.get('clubNameShort')} UniqueID {result.get('clubId')} "
        f"tag {result.get('tagHex')} clubIdAbs {result.get('clubIdAbs')}",
        f"person doubles scanned: {result.get('personDoubles')}",
        f"gold UniqueIDs with person double: {len(result.get('goldFound') or [])} / "
        f"{len(result.get('goldFound') or []) + len(result.get('goldMissingPersonDouble') or [])}",
        "",
        "## Club `.dat` senior intern list",
        "",
    ]
    cl = result.get("clubSeniorList") or {}
    lines.append(
        f"tadAbs={cl.get('tadAbs')} countAbs={cl.get('countAbs')} "
        f"count={cl.get('count')} clubIdInDat={cl.get('clubIdAbsInDat')}"
    )
    lines.append("")
    lines.append("| intern | UniqueID | name | personAbs |")
    lines.append("|--------|----------|------|-----------|")
    for row in cl.get("players") or []:
        lines.append(
            f"| {row['intern']} | {row['uid']} | {row.get('name') or '—'} | {row['personAbs']} |"
        )
    vg = result.get("vsGold") or {}
    lines += [
        "",
        "## vs gold",
        "",
        f"owned_at_club in list: {len((vg.get('inClubSeniorList') or {}).get('owned_at_club') or [])}",
        f"inbound_loan in list: {len((vg.get('inClubSeniorList') or {}).get('inbound_loan') or [])}",
        f"owned_out_on_loan in list: {(vg.get('inClubSeniorList') or {}).get('owned_out_on_loan')}",
        f"owned_out_on_loan missing from list: {(vg.get('missingFromClubSeniorList') or {}).get('owned_out_on_loan')}",
        "",
        "## Gold person doubles (all 42 by UniqueID)",
        "",
        "| UniqueID | name | intern | personAbs |",
        "|----------|------|--------|-----------|",
    ]
    for row in result.get("goldFound") or []:
        lines.append(
            f"| {row['uid']} | {row['name']} | {row['intern']} | {row['personAbs']} |"
        )
    if result.get("goldMissingPersonDouble"):
        lines.append("")
        lines.append("## Gold UniqueIDs with no person double")
        for row in result["goldMissingPersonDouble"]:
            lines.append(f"- {row['uid']} {row['name']}")
    blk = result.get("blocked") or {}
    lines += ["", "## Blocked", "", blk.get("reason") or ""]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def working_copy(src: Path) -> Path:
    refuse_live_fm_games_save(src)
    work_dir = ROOT / "tmp" / "t115-work"
    work_dir.mkdir(parents=True, exist_ok=True)
    dest = work_dir / src.name
    shutil.copy2(src, dest)
    refuse_live_fm_games_save(dest)
    return dest


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "saves" / "gameDate8.fm"
    if not src.is_file():
        print(json.dumps({"error": f"Save not found: {src}"}), flush=True)
        return 2
    work = working_copy(src)
    tmp: Path | None = None
    try:
        tmp = decompress_to_temp(work)
        with tmp.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            result = lock_from_mmap(mm)
        dump = ROOT / "tmp" / "identity" / "t115-santos-three-status.txt"
        write_dump(result, dump)
        print(json.dumps({k: result[k] for k in result if k != "goldFound"}, default=str)[:2000])
        print(f"dump {dump}", flush=True)
        return 0
    finally:
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            work.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
