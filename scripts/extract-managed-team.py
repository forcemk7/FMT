#!/usr/bin/env python3
"""
Managed club identity from a career .fm save.

Locked path (continue + native FM26):
  1) Tag 00 95 0e 01|02 → manager lp32 → club short lp32 → club UniqueID u32
  2) Optional catalog: long/short name pair for the official club name

EARLY_SCAN / IDENTITY_DEADLINE are first-pass bounds, not a save's byte as law.
If the tag sits later, search continues. Miss = diagnostic (tags / offset /
bytes scanned), not a silent wrong club.

Stops as soon as identity (+ optional catalog name) is resolved — no squad-list
scan in this phase (First Team teamId / players come later).
"""

from __future__ import annotations

import json
import struct
import sys
import time
from pathlib import Path

import zstandard as zstd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHUNK = 2 * 1024 * 1024
ZSTD_MAGIC = bytes.fromhex("28b52ffd")
HUMAN_TAGS = (
    bytes.fromhex("00950e01"),  # native FM26
    bytes.fromhex("00950e02"),  # FM24→FM26 continue
)

EARLY_SCAN = 500_000
IDENTITY_DEADLINE = 2 * 1024 * 1024
# Give-up cap after expanding past the deadline — a bound, not a save offset.
IDENTITY_SCAN_MAX = 64 * 1024 * 1024
CATALOG_LO = 500_000
CATALOG_TARGET = 12 * 1024 * 1024
CALIB_DUMP = ROOT / "tmp" / "calib" / "early-last.bin"
CALIB_META = ROOT / "tmp" / "calib" / "early-last.json"


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


def resolve_save() -> Path:
    if len(sys.argv) >= 2:
        p = Path(sys.argv[1])
        if not p.is_file():
            raise SystemExit(f"Save not found: {p}")
        return p
    saves = sorted(
        Path(ROOT, "data", "saves").glob("*.fm"),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    if not saves:
        raise SystemExit("No .fm in data/saves")
    return saves[0]


def probe_zstd_offset(save: Path) -> tuple[int | None, dict]:
    head = save.read_bytes()[:64]
    info: dict = {
        "saveBytes": save.stat().st_size,
        "magicAscii": head[:4].decode("latin-1", errors="replace"),
    }
    if len(head) > 30 and head[26:30] == ZSTD_MAGIC:
        info["inferredLayout"] = "fm24_continue_style_zstd_at_26"
        return 26, info
    j = head.find(ZSTD_MAGIC)
    if j >= 0:
        info["inferredLayout"] = f"zstd_at_{j}"
        return j, info
    info["inferredLayout"] = "unknown"
    return None, info


def read_lp32(buf, off: int) -> str | None:
    if off < 0 or off + 4 > len(buf):
        return None
    n = struct.unpack_from("<I", buf, off)[0]
    if not (2 <= n <= 64) or off + 4 + n > len(buf):
        return None
    raw = bytes(buf[off + 4 : off + 4 + n])
    if any(b < 9 or 13 < b < 32 for b in raw):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        if all(32 <= b < 127 for b in raw):
            return raw.decode("ascii")
        return None


def _looks_comp_name(s: str) -> bool:
    low = s.lower()
    return any(
        k in low
        for k in (
            "liga",
            "league",
            "division",
            "premier",
            "serie",
            "bundes",
            "championship",
            "cup",
            "divisi",
            "wsl",
        )
    )


def _looks_person_name(s: str) -> bool:
    return 3 <= len(s) <= 48 and s[0].isalpha() and not _looks_comp_name(s)


def _looks_club_short(s: str) -> bool:
    return 3 <= len(s) <= 48 and s[0].isalpha() and not _looks_comp_name(s)


def discover_managed_club(buf, limit: int = EARLY_SCAN) -> dict | None:
    """
    00 95 0e 01|02 + manager + club short + club UniqueID (u32).
    Searches [0, limit). Callers expand limit if this returns None.
    """
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
                "identityAbs": off,
                "clubIdAbs": id_off,
                "tagHex": tag.hex(),
                "score": score,
                "method": "human_tag_club_uid",
            }
            if best is None or cand["score"] > best["score"]:
                best = cand
            start = j + 1
    return best


def identity_scan_diagnostics(buf, limit: int) -> dict:
    """Tag hit counts / offsets for a miss — not a guessed club."""
    hi = min(max(0, int(limit)), len(buf))
    tags: dict[str, dict] = {}
    last_tag_abs: int | None = None
    for tag in HUMAN_TAGS:
        first: int | None = None
        count = 0
        start = 0
        while start + len(tag) <= hi:
            j = buf.find(tag, start, hi)
            if j < 0:
                break
            count += 1
            if first is None:
                first = j
            last_tag_abs = j if last_tag_abs is None else max(last_tag_abs, j)
            start = j + 1
        tags[tag.hex()] = {"count": count, "firstAbs": first}
    return {
        "bytesScanned": hi,
        "tags": tags,
        "lastTagAbs": last_tag_abs,
        "tagHexes": [t.hex() for t in HUMAN_TAGS],
    }


def try_discover_managed_club(
    buf,
    *,
    limits: tuple[int, ...] | None = None,
) -> tuple[dict | None, dict]:
    """Expanding bounds. First bound that parses wins. Deadline is not fail."""
    n = len(buf)
    raw = limits if limits is not None else (EARLY_SCAN, IDENTITY_DEADLINE, n)
    seen: list[int] = []
    for x in raw:
        b = min(n, max(0, int(x)))
        if not seen or b > seen[-1]:
            seen.append(b)
    hit: dict | None = None
    bound = seen[-1] if seen else 0
    for bound in seen:
        hit = discover_managed_club(buf, bound)
        if hit:
            break
    scan_hi = bound if hit else (seen[-1] if seen else 0)
    diag = identity_scan_diagnostics(buf, scan_hi)
    diag["searchBound"] = bound
    diag["identityFound"] = hit is not None
    if hit:
        diag["tagHex"] = hit.get("tagHex")
        diag["identityAbs"] = hit.get("identityAbs")
    return hit, diag


def catalog_long_name(
    buf, club_short: str, *, scan_lo: int = CATALOG_LO, scan_hi: int | None = None
) -> tuple[str | None, dict]:
    """Best-effort official long name from catalog long/short pair."""
    raw = club_short.encode("utf-8")
    diag: dict = {"catalogShortHits": 0, "catalogPairHits": 0}
    start = max(0, scan_lo)
    end = min(len(buf), scan_hi if scan_hi is not None else CATALOG_TARGET)
    while start < end:
        j = buf.find(raw, start, end)
        if j < 0:
            break
        diag["catalogShortHits"] += 1
        if j >= 4 and struct.unpack_from("<I", buf, j - 4)[0] == len(raw):
            for back in range(5, 120):
                long_off = j - 4 - back
                long = read_lp32(buf, long_off)
                if not long or not long[0].isalpha():
                    continue
                if struct.unpack_from("<I", buf, long_off)[0] + 4 != back:
                    continue
                if long.startswith(("Player", "Staff", "http")):
                    continue
                if (
                    club_short not in long
                    and long.replace("FC ", "") != club_short
                    and long != club_short
                ):
                    continue
                # Prefer longer official names (FC X / X City).
                if len(long) >= len(club_short):
                    diag["catalogPairHits"] += 1
                    diag["catalogAbs"] = long_off
                    return long, diag
        start = j + 1
    return None, diag


def write_calib_dump(buf, meta: dict) -> None:
    try:
        CALIB_DUMP.parent.mkdir(parents=True, exist_ok=True)
        CALIB_DUMP.write_bytes(bytes(buf[: min(len(buf), IDENTITY_DEADLINE)]))
        CALIB_META.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def main() -> int:
    save = resolve_save()
    t0 = time.perf_counter()
    zstd_off, container = probe_zstd_offset(save)
    progress(
        t0,
        phase="start",
        message=f"Opening {save.name}",
        pct=0,
        **container,
        zstdOffset=zstd_off,
    )
    if zstd_off is None:
        return fail(t0, "No zstd stream found in .fm header.", **container)

    buf = bytearray()
    identity: dict | None = None
    ident_diag: dict = {}
    club_long: str | None = None
    cat_diag: dict = {}
    zstd_exc: str | None = None
    last_prog = 0
    scan_cap = max(CATALOG_TARGET, IDENTITY_SCAN_MAX)

    with save.open("rb") as f:
        f.seek(int(zstd_off))
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while len(buf) < scan_cap:
                try:
                    block = reader.read(CHUNK)
                except zstd.ZstdError as e:
                    zstd_exc = str(e)
                    if not buf:
                        return fail(
                            t0,
                            f"zstd decompress failed (empty output): {e}. "
                            "If this was an upload, the file may be truncated — retry the upload.",
                            **container,
                        )
                    break
                if not block:
                    break
                buf.extend(block)

                if len(buf) - last_prog >= CHUNK:
                    last_prog = len(buf)
                    progress(
                        t0,
                        phase="decompress",
                        message="Decompressing (club identity)",
                        pct=min(80, int(80 * len(buf) / scan_cap)),
                        outBytes=len(buf),
                    )

                if identity is None:
                    identity, ident_diag = try_discover_managed_club(
                        buf,
                        limits=(EARLY_SCAN, IDENTITY_DEADLINE, len(buf)),
                    )
                    if identity:
                        progress(
                            t0,
                            phase="resolve",
                            message=(
                                f"club={identity['clubNameShort']} "
                                f"id={identity['clubId']}"
                            ),
                            pct=50,
                            outBytes=len(buf),
                            searchBound=ident_diag.get("searchBound"),
                        )

                if identity and club_long is None and len(buf) >= max(CATALOG_LO, 2 << 20):
                    club_long, cat_diag = catalog_long_name(
                        buf, identity["clubNameShort"]
                    )
                    if club_long:
                        progress(
                            t0,
                            phase="resolve",
                            message=f"catalog={club_long}",
                            pct=90,
                            outBytes=len(buf),
                        )
                        break

                if identity and len(buf) >= CATALOG_TARGET:
                    break
                if identity is None and len(buf) >= IDENTITY_SCAN_MAX:
                    break
        finally:
            reader.close()

    if identity is None:
        if not ident_diag:
            ident_diag = identity_scan_diagnostics(buf, len(buf))
            ident_diag["searchBound"] = len(buf)
            ident_diag["identityFound"] = False
        write_calib_dump(buf, {"saveName": save.name, **container, **ident_diag})
        return fail(
            t0,
            "No managed-club identity (human tag → club UniqueID).",
            decompressedBytes=len(buf),
            calibDump=str(CALIB_DUMP.relative_to(ROOT)),
            **container,
            **ident_diag,
        )

    if club_long is None:
        club_long, cat_diag = catalog_long_name(buf, identity["clubNameShort"])

    club_short = identity["clubNameShort"]
    club_id = identity["clubId"]
    club_name = club_long or club_short

    result = {
        "savePath": str(save),
        "saveName": save.name,
        # Club Site UniqueID (primary).
        "clubId": club_id,
        # Alias kept for existing UI/store wiring.
        "teamId": club_id,
        "clubName": club_name,
        "clubNameShort": club_short,
        "players": [],
        "discovery": {
            "method": identity["method"],
            "tagHex": identity["tagHex"],
            "identityAbs": identity["identityAbs"],
            "clubIdAbs": identity["clubIdAbs"],
            "managerNameLen": len(identity["managerName"]),
            "earlyStop": True,
            "identityFound": True,
            "searchBound": ident_diag.get("searchBound"),
            "bytesScanned": ident_diag.get("bytesScanned"),
            **cat_diag,
            "zstdNote": zstd_exc,
        },
        "elapsedMs": int((time.perf_counter() - t0) * 1000),
        "decompressedBytes": len(buf),
        **container,
    }
    progress(t0, phase="done", message=f"clubId={club_id} · {club_name}", pct=100)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
