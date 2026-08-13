#!/usr/bin/env python3
"""
Fingerprint-hunt HA locations using Genie Scout definite values.

Reads data/fixtures/ha-genie-table.json (status=complete players).
Searches decompressed .fm for:
- contiguous u8 packs in several CM/GS/user orders (mental + match-hidden)
- x5-encoded packs
- int32 LE packs
- near double-UID and all UID hits
Reports shared relative layouts when ≥2 players agree.
"""

from __future__ import annotations

import json
import mmap
import os
import struct
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
TABLE = ROOT / "data" / "fixtures" / "ha-genie-table.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-genie-hunt.txt"
ZSTD_OFF = 26
NEAR_WIN = 4096  # bytes around UID

MENTAL_ORDERS = {
    "cm_staff": [
        "adaptability", "ambition", "determination", "loyalty",
        "pressure", "professionalism", "sportsmanship", "temperament",
    ],
    "cm_no_det": [
        "adaptability", "ambition", "loyalty",
        "pressure", "professionalism", "sportsmanship", "temperament",
    ],
    "classic_pers": [
        "ambition", "loyalty", "pressure", "professionalism",
        "sportsmanship", "temperament", "controversy",
    ],
    "classic_pers8": [
        "ambition", "loyalty", "pressure", "professionalism",
        "sportsmanship", "temperament", "controversy", "importantMatches",
    ],
    "gs_mental": [
        "adaptability", "ambition", "controversy", "loyalty",
        "pressure", "professionalism", "sportsmanship", "temperament",
    ],
    "user_ha": [
        "professionalism", "pressure", "ambition", "importantMatches",
        "sportsmanship", "temperament", "loyalty", "controversy",
    ],
    "genie_listed": [
        "adaptability", "ambition", "controversy", "loyalty",
        "pressure", "professionalism", "sportsmanship", "temperament",
    ],
}

MATCH_ORDERS = {
    "genie_match": [
        "consistency", "dirtiness", "importantMatches",
        "injuryProneness", "versatility",
    ],
}


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-genie-", suffix=".bin")
    os.close(fd)
    tmp = Path(name)
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(ZSTD_OFF)
        r = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = r.read(8 << 20)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                out.write(b)
        finally:
            r.close()
    return tmp


def find_all(mm, pat: bytes, limit=60) -> list[int]:
    hits = []
    j = mm.find(pat)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = mm.find(pat, j + 1)
    return hits


def values_for(player: dict, keys: list[str]) -> list[int] | None:
    mental = player.get("mental") or {}
    match = player.get("matchHidden") or {}
    # determination / leadership from top-level if present
    extra = {
        "determination": player.get("determination"),
        "leadership": player.get("leadership"),
        "importantMatches": match.get("importantMatches"),
    }
    out = []
    for k in keys:
        if k in mental:
            out.append(mental[k])
        elif k in match:
            out.append(match[k])
        elif k in extra and extra[k] is not None:
            out.append(extra[k])
        else:
            return None
    return out


def find_pack_u8(blob: bytes, vals: list[int]) -> list[int]:
    if not vals:
        return []
    needle = bytes(vals)
    hits = []
    start = 0
    while True:
        j = blob.find(needle, start)
        if j < 0:
            break
        hits.append(j)
        start = j + 1
    return hits


def find_pack_x5(blob: bytes, vals: list[int]) -> list[int]:
    return find_pack_u8(blob, [v * 5 for v in vals])


def find_pack_i32(blob: bytes, vals: list[int]) -> list[int]:
    needle = b"".join(struct.pack("<I", v) for v in vals)
    hits = []
    start = 0
    while True:
        j = blob.find(needle, start)
        if j < 0:
            break
        if j % 4 == 0 or True:  # allow unaligned
            hits.append(j)
        start = j + 1
    return hits


def find_interleaved_01(blob: bytes, vals: list[int]) -> list[int]:
    """V 01 V 01 ... pattern."""
    parts = []
    for v in vals:
        parts.extend([v, 0x01])
    needle = bytes(parts[:-1])  # drop trailing 01 requirement (may or may not exist)
    # try full with trailing 01 and without
    hits = []
    for n in (bytes(parts), bytes(parts[:-1])):
        start = 0
        while True:
            j = blob.find(n, start)
            if j < 0:
                break
            hits.append(j)
            start = j + 1
    return sorted(set(hits))


def main() -> int:
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    players = [p for p in table["players"] if p.get("status") == "complete"]
    lines = [f"complete_players={len(players)}"]
    for p in players:
        m = p["mental"]
        lines.append(
            f"  {p['name']}: Tem={m['temperament']} Pro={m['professionalism']} "
            f"Pre={m['pressure']} Spo={m['sportsmanship']} Loy={m['loyalty']}"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)

    print("decompressing…", flush=True)
    tmp = decompress(SAVE)
    # shared layout: order -> enc -> rel_to_double -> [players]
    shared = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                lines.append(f"save_bytes={mm.size()}")
                for p in players:
                    uid = p["uid"]
                    name = p["name"]
                    dpat = struct.pack("<II", uid, uid)
                    doubles = find_all(mm, dpat, limit=20)
                    singles = find_all(mm, struct.pack("<I", uid), limit=40)
                    lines.append(f"\n=== {name} uid={uid} doubles={len(doubles)} singles={len(singles)} ===")

                    # Prefer person-like doubles: those with 01 01 nearby after header
                    ranked_doubles = []
                    for d in doubles:
                        blob = bytes(mm[d : d + 256])
                        score = 0
                        if b"\x01\x01\x01" in blob[8:64]:
                            score += 5
                        if blob[8] in (0x01, 0x02):
                            score += 1
                        ranked_doubles.append((score, d))
                    ranked_doubles.sort(reverse=True)

                    loci = []
                    if ranked_doubles:
                        loci.append(("double", ranked_doubles[0][1]))
                        if len(ranked_doubles) > 1 and ranked_doubles[1][0] >= 5:
                            loci.append(("double2", ranked_doubles[1][1]))
                    for s in singles[:12]:
                        loci.append(("uid", s))

                    found_any = False
                    for kind, abs_off in loci:
                        lo = max(0, abs_off - 256)
                        hi = min(mm.size(), abs_off + NEAR_WIN)
                        blob = bytes(mm[lo:hi])
                        base = abs_off  # rel = pack_abs - uid_abs

                        for oname, keys in {**MENTAL_ORDERS, **MATCH_ORDERS}.items():
                            vals = values_for(p, keys)
                            if not vals:
                                continue
                            for enc, finder in (
                                ("u8", find_pack_u8),
                                ("x5", find_pack_x5),
                                ("i32", find_pack_i32),
                                ("v01", find_interleaved_01),
                            ):
                                if enc == "v01" and oname.startswith("genie_match"):
                                    continue
                                hits = finder(blob, vals)
                                for h in hits:
                                    pack_abs = lo + h
                                    rel = pack_abs - abs_off
                                    found_any = True
                                    lines.append(
                                        f"  HIT {kind}@{abs_off} {oname}/{enc} "
                                        f"rel={rel:+d} abs={pack_abs} vals={vals}"
                                    )
                                    if kind.startswith("double"):
                                        shared[oname][enc][rel].append(name)

                    if not found_any:
                        # weaker: search unique 4-tuples (Pro,Tem,Spo,Loy) near best double
                        if ranked_doubles:
                            abs_off = ranked_doubles[0][1]
                            blob = bytes(mm[max(0, abs_off - 256) : abs_off + NEAR_WIN])
                            m = p["mental"]
                            for combo_name, combo in (
                                ("ProTemSpoLoy", [m["professionalism"], m["temperament"],
                                                  m["sportsmanship"], m["loyalty"]]),
                                ("TemPro", [m["temperament"], m["professionalism"]]),
                                ("ProTem", [m["professionalism"], m["temperament"]]),
                                ("LoyPreProSpoTem", [
                                    m["loyalty"], m["pressure"], m["professionalism"],
                                    m["sportsmanship"], m["temperament"],
                                ]),
                                ("gs_order_bytes", [
                                    m["adaptability"], m["ambition"], m["controversy"],
                                    m["loyalty"], m["pressure"], m["professionalism"],
                                    m["sportsmanship"], m["temperament"],
                                ]),
                            ):
                                for enc, finder in (("u8", find_pack_u8), ("x5", find_pack_x5),
                                                      ("i32", find_pack_i32)):
                                    for h in finder(blob, combo)[:5]:
                                        rel = (max(0, abs_off - 256) + h) - abs_off
                                        lines.append(
                                            f"  PARTIAL {combo_name}/{enc} rel={rel:+d} {combo}"
                                        )
                                        shared[combo_name][enc][rel].append(name)
                        lines.append("  (no full-order pack near UID windows)")

                lines.append("\n=== SHARED layouts (≥2 players, same order/enc/rel) ===")
                warm = []
                for oname, encs in shared.items():
                    for enc, rels in encs.items():
                        for rel, names in sorted(rels.items(), key=lambda t: -len(t[1])):
                            uniq = sorted(set(names))
                            if len(uniq) >= 2:
                                lines.append(
                                    f"  {oname}/{enc} rel={rel:+d} n={len(uniq)} {uniq}"
                                )
                                warm.append((len(uniq), oname, enc, rel, uniq))
                warm.sort(reverse=True)
                lines.append("\n=== VERDICT ===")
                if warm and warm[0][0] >= 3:
                    lines.append(
                        f"WARM: best {warm[0][1]}/{warm[0][2]} rel={warm[0][3]:+d} "
                        f"players={warm[0][0]} {warm[0][4]}"
                    )
                elif warm:
                    lines.append(f"TEPID: best n={warm[0][0]} {warm[0][1]}/{warm[0][2]} rel={warm[0][3]:+d}")
                else:
                    lines.append("COLD: no shared full Genie pack near UID/doubles.")

                # Global needle for most unique player fingerprints (Tello Con=2 Loy=19)
                lines.append("\n=== global unique needles (Tello mental gs_order u8/x5) ===")
                tello = next(p for p in players if p["name"] == "Ferney Tello")
                keys = MENTAL_ORDERS["gs_mental"]
                vals = values_for(tello, keys)
                assert vals
                for enc, needle in (
                    ("u8", bytes(vals)),
                    ("x5", bytes(v * 5 for v in vals)),
                    ("i32", b"".join(struct.pack("<I", v) for v in vals)),
                ):
                    hits = find_all(mm, needle, limit=20)
                    lines.append(f"Tello {enc} {list(vals) if enc!='x5' else [v*5 for v in vals]}: hits={len(hits)} {hits[:8]}")
                    for h in hits[:3]:
                        # nearby UID?
                        win = bytes(mm[max(0, h - 64) : h + 64])
                        uid_pat = struct.pack("<I", tello["uid"])
                        lines.append(f"  @{h} uid_nearby={uid_pat in win} hex={win[32:48].hex(' ')}")

            finally:
                mm.close()
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(x in line for x in (
            "===", "HIT ", "SHARED", "VERDICT", "WARM", "COLD", "TEPID",
            "global", "Tello ", "PARTIAL", "no full", "complete_players",
        )):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
