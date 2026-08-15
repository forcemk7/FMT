#!/usr/bin/env python3
"""Extract players who list the managed club as a favoured club.

Record shape (locked via Assan Ouédraogo ground truth):
  4e <affinity:u8> 01 03 02 <clubId u32le>
Affinity 100 (0x64) is the common "favourite team" strength in FMRTE terms.

CA/PA (locked, see data/fixtures/capa-layout-locked.json):
  Near person double-UID: <ptr>×2 | 02 | x y z | CA | PA  (ptr hi-byte 0x77);
  take nearest core within 48KB lookback.

Stream decompress to a temp bin (fav scan + CAPA enrich via mmap).
"""

from __future__ import annotations

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

CHUNK = 8 * 1024 * 1024
EARLY_IDENTITY = 2 * 1024 * 1024
UID_LO, UID_HI = 2_000_000_000, 2_004_000_000
FAV_TYPE = 0x4E
FAV_AFFINITY = 100
# 4e 64 01 03 02 <clubId>
CLUB_REF = bytes.fromhex("010302")

# Locked CAPA core (see data/fixtures/capa-layout-locked.json):
#   <ptr:u32>×2 | 02 | x:u16 y:u16 z:u16 | CA:u16 | PA:u16
# Join: nearest core with ptr high-byte 0x77 before a person double-UID.
CAPA_LOOKBACK = 48_000
CAPA_PTR_HI = 0x77

HUMAN_TAGS = (
    bytes.fromhex("00950e01"),
    bytes.fromhex("00950e02"),
)


def progress(t0: float, **fields) -> None:
    fields.setdefault("elapsedMs", int((time.perf_counter() - t0) * 1000))
    print(f"PROGRESS {json.dumps(fields, ensure_ascii=False)}", file=sys.stderr, flush=True)


def fail(msg: str, code: int = 1, **extra) -> int:
    print(json.dumps({"error": msg, **extra}, ensure_ascii=False), flush=True)
    return code


def read_lp32(buf: bytes, off: int) -> str | None:
    if off + 4 > len(buf):
        return None
    n = struct.unpack_from("<I", buf, off)[0]
    if n < 2 or n > 64 or off + 4 + n > len(buf):
        return None
    raw = buf[off + 4 : off + 4 + n]
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            s = raw.decode("latin-1")
        except Exception:
            return None
    if not s or not s[0].isalpha():
        return None
    return s


def _looks_person_name(s: str) -> bool:
    return 3 <= len(s) <= 48 and s[0].isalpha()


def _looks_club_short(s: str) -> bool:
    return 3 <= len(s) <= 48 and s[0].isalpha()


def discover_managed_club(buf: bytes, limit: int = EARLY_IDENTITY) -> dict | None:
    hi = min(limit, len(buf))
    best: dict | None = None
    for tag in HUMAN_TAGS:
        start = 0
        while start + 12 < hi:
            j = buf.find(tag, start, hi)
            if j < 0:
                break
            off = j + len(tag)
            person = read_lp32(buf, off)
            if not person or not _looks_person_name(person):
                start = j + 1
                continue
            n1 = struct.unpack_from("<I", buf, off)[0]
            o2 = off + 4 + n1
            club = read_lp32(buf, o2)
            if not club or not _looks_club_short(club):
                start = j + 1
                continue
            n2 = struct.unpack_from("<I", buf, o2)[0]
            id_off = o2 + 4 + n2
            if id_off + 4 > len(buf):
                start = j + 1
                continue
            club_id = struct.unpack_from("<I", buf, id_off)[0]
            if club_id in (0, 0xFFFFFFFF) or club_id > 3_000_000_000:
                start = j + 1
                continue
            score = 0
            if " " in person:
                score += 2
            if person.lower().startswith(("mr ", "mrs ", "ms ", "dr ")):
                score += 2
            if 1 <= club_id <= 100_000:
                score += 1
            cand = {
                "managerName": person,
                "clubNameShort": club,
                "clubId": club_id,
                "score": score,
            }
            if best is None or cand["score"] > best["score"]:
                best = cand
            start = j + 1
    return best


def anchor_person(window: bytes, fav_rel: int) -> tuple[int | None, str | None]:
    """Prefer a typed UID that is followed by a full name (person owner of the relations block)."""
    lo = max(0, fav_rel - 720)
    chunk = window[lo:fav_rel]
    best_uid: int | None = None
    best_name: str | None = None
    best_score = -1
    for i in range(0, max(0, len(chunk) - 8)):
        if chunk[i] != 0x02:
            continue
        uid = struct.unpack_from("<I", chunk, i + 1)[0]
        if not (UID_LO <= uid <= UID_HI):
            continue
        name = None
        for off in range(i + 5, min(len(chunk) - 4, i + 120)):
            nm = read_lp32(chunk, off)
            if nm and " " in nm and len(nm) <= 48:
                name = nm
                break
        # Prefer farther-back owner candidates with a full name.
        score = 0
        if name:
            score += 8
            score += min(3, name.count(" "))
        else:
            # still accept bare typed UIDs so hits aren't dropped
            score += 1
        dist = len(chunk) - i
        score += max(0, 4 - dist // 100)
        if score > best_score:
            best_score = score
            best_uid = uid
            best_name = name
    return best_uid, best_name


def refuse_live_fm_games_save(path: Path) -> None:
    parts = [p.lower() for p in Path(path).resolve().parts]
    if (
        "sports interactive" in parts
        and "games" in parts
        and Path(path).suffix.lower() == ".fm"
    ):
        raise SystemExit(
            fail("Refusing Sports Interactive/games/*.fm — copy the Career Save into data/saves")
        )


def resolve_save() -> Path:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        p = Path(args[0])
        if not p.is_file():
            raise SystemExit(fail(f"Save not found: {p}"))
        refuse_live_fm_games_save(p)
        return p
    saves = sorted((Path(__file__).resolve().parents[1] / "data" / "saves").glob("*.fm"))
    if not saves:
        raise SystemExit(fail("No .fm save given and none in data/saves"))
    refuse_live_fm_games_save(saves[0])
    return saves[0]


def _person_doubles(mm: mmap.mmap, uid: int, *, limit: int = 40) -> list[int]:
    nb = struct.pack("<I", uid)
    out: list[int] = []
    start = 0
    while len(out) < limit:
        j = mm.find(nb, start)
        if j < 0:
            break
        if j < 800_000_000 and mm.find(nb, j + 4, min(len(mm), j + 48)) > 0:
            out.append(j)
        start = j + 1
    return out


def _nearest_capa_core(mm: mmap.mmap, dab: int) -> tuple[int, int, int] | None:
    """Return (CA, PA, gap) for nearest hi=0x77 twin-ptr core before dab."""
    lo = max(0, dab - CAPA_LOOKBACK)
    best_at = -1
    best: tuple[int, int] | None = None
    for off in range(lo, dab - 19):
        p1 = struct.unpack_from("<I", mm, off)[0]
        if ((p1 >> 24) & 0xFF) != CAPA_PTR_HI:
            continue
        p2 = struct.unpack_from("<I", mm, off + 4)[0]
        if p1 != p2 or mm[off + 8] != 0x02:
            continue
        ca = struct.unpack_from("<H", mm, off + 15)[0]
        pa = struct.unpack_from("<H", mm, off + 17)[0]
        if not (1 <= ca <= 200 and 1 <= pa <= 200):
            continue
        if off > best_at:
            best_at = off
            best = (ca, pa)
    if best is None:
        return None
    return best[0], best[1], dab - best_at


def enrich_capa(mm: mmap.mmap, players: list[dict], t0: float) -> None:
    """Attach ca/pa onto player dicts (mutates in place)."""
    n = len(players)
    for i, p in enumerate(players):
        uid = int(p["uid"])
        best: tuple[int, int, int] | None = None  # ca, pa, gap
        for dab in _person_doubles(mm, uid):
            hit = _nearest_capa_core(mm, dab)
            if hit is None:
                continue
            if best is None or hit[2] < best[2]:
                best = hit
        if best is not None:
            p["ca"] = best[0]
            p["pa"] = best[1]
        else:
            p["ca"] = None
            p["pa"] = None
        if n and (i % 5 == 0 or i + 1 == n):
            progress(
                t0,
                phase="capa",
                message=f"Ability {i + 1}/{n}",
                pct=min(99, 90 + int(9 * (i + 1) / n)),
            )


def main() -> int:
    t0 = time.perf_counter()
    save = resolve_save()
    progress(t0, phase="start", message=f"Opening {save.name}", pct=0)

    early = bytearray()
    identity: dict | None = None
    club_id: int | None = None
    needle: bytes | None = None
    by_uid: dict[int, dict] = {}
    raw_hits = 0
    abs_base = 0
    identity_error: str | None = None

    fd, tmp_name = tempfile.mkstemp(prefix="fmt-fav-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)

    try:
        with save.open("rb") as f, tmp.open("wb") as out:
            head = f.read(26)
            if len(head) < 26 or head[2:6] != b"fmf." or head[25] != 3:
                return fail("Unsupported .fm container", saveName=save.name)

            # Career saves often trail the primary zstd frame with padding/noise.
            # Treat any post-progress ZstdError as EOF; never let close() abort success.
            reader = zstd.ZstdDecompressor().stream_reader(f)
            carry = b""
            overlap = 600
            last_pct = -1
            est = max(save.stat().st_size * 3, 1)

            try:
                while True:
                    try:
                        block = reader.read(CHUNK)
                    except zstd.ZstdError as e:
                        # Trailing frame noise after a successful body — treat as EOF.
                        if abs_base == 0 and not early:
                            return fail(
                                f"zstd decompress failed: {e}",
                                saveName=save.name,
                            )
                        break
                    if not block:
                        break

                    out.write(block)

                    if identity is None:
                        need = EARLY_IDENTITY - len(early)
                        if need > 0:
                            early.extend(block[:need])
                        if len(early) >= EARLY_IDENTITY:
                            identity = discover_managed_club(bytes(early), EARLY_IDENTITY)
                            if not identity:
                                identity_error = "Could not discover managed club identity"
                                break
                            club_id = int(identity["clubId"])
                            needle = (
                                bytes([FAV_TYPE, FAV_AFFINITY])
                                + CLUB_REF
                                + struct.pack("<I", club_id)
                            )
                            progress(
                                t0,
                                phase="identity",
                                message=f"{identity['clubNameShort']} (id={club_id})",
                                pct=8,
                                clubId=club_id,
                            )
                            early = bytearray()

                    data = carry + block
                    search_end = len(data) - (0 if abs_base == 0 else overlap)
                    if needle and search_end > 0:
                        start = max(0, len(carry) - overlap - 3) if abs_base else 0
                        while True:
                            j = data.find(
                                needle, start, max(start, search_end) + len(needle)
                            )
                            if j < 0 or j >= search_end:
                                break
                            abs_hit = abs_base - len(carry) + j
                            lo = max(0, j - 720)
                            hi = min(len(data), j + 16)
                            win = data[lo:hi]
                            uid, name = anchor_person(win, j - lo)
                            raw_hits += 1
                            if uid is not None:
                                prev = by_uid.get(uid)
                                if prev is None or (name and not prev.get("name")):
                                    rec = {
                                        "uid": uid,
                                        "name": name,
                                        "affinity": FAV_AFFINITY,
                                        "abs": abs_hit,
                                    }
                                    by_uid[uid] = rec
                            start = j + 1

                    abs_base += len(block)
                    carry = data[-overlap:]
                    pct = int(min(88, 8 + abs_base * 80 / est))
                    if pct != last_pct and pct % 5 == 0:
                        last_pct = pct
                        progress(
                            t0,
                            phase="scan",
                            message=f"Favourites found: {len(by_uid)} (raw={raw_hits})",
                            pct=pct,
                            outBytes=abs_base,
                        )
            finally:
                try:
                    reader.close()
                except zstd.ZstdError:
                    pass

        if identity_error:
            return fail(identity_error, saveName=save.name)

        if identity is None or club_id is None:
            if early:
                identity = discover_managed_club(bytes(early), len(early))
                if identity:
                    club_id = int(identity["clubId"])
            if identity is None or club_id is None:
                return fail("Managed club identity not found", saveName=save.name)

        manager = (identity.get("managerName") or "").strip().lower()
        players = []
        for rec in sorted(by_uid.values(), key=lambda r: (r.get("name") or "", r["uid"])):
            nm = rec.get("name")
            if nm and nm.strip().lower() == manager:
                continue  # manager self-link noise
            players.append(
                {
                    "uid": rec["uid"],
                    "name": nm,
                    "affinity": rec["affinity"],
                    "ca": None,
                    "pa": None,
                }
            )

        progress(t0, phase="capa", message="Reading CA/PA…", pct=90)
        with tmp.open("rb") as bf:
            mm = mmap.mmap(bf.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                enrich_capa(mm, players, t0)
            finally:
                mm.close()

        with_capa = sum(1 for p in players if p.get("ca") is not None)
        out = {
            "savePath": str(save),
            "saveName": save.name,
            "clubId": club_id,
            "clubNameShort": identity.get("clubNameShort"),
            "clubName": identity.get("clubNameShort"),
            "managerName": identity.get("managerName"),
            "query": "favoured_club",
            "affinity": FAV_AFFINITY,
            "motif": "4e64010302+clubId",
            "players": players,
            "hitCount": raw_hits,
            "anchoredCount": len(by_uid),
            "capaResolved": with_capa,
            "elapsedMs": int((time.perf_counter() - t0) * 1000),
            "decompressedBytes": abs_base,
        }
        progress(
            t0,
            phase="done",
            message=f"{len(players)} favourites · {with_capa} with CA/PA",
            pct=100,
        )
        print(json.dumps(out, ensure_ascii=False), flush=True)
        return 0
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
