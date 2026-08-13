#!/usr/bin/env python3
"""
Trio-first HA bridge:
  Kizza Tem==15, Paco Pro==20, Tassinari Tem 3-6 / Con 15-20 / Spo 1-7
Then validate with Seimen (Pro 18-19, Con 1-5) and Yoan (Pre 17-19).

Decode two after-double families separately, then search shared card-/dbl-
relative offsets excluding 69B CA-card collisions.
"""

from __future__ import annotations

import json
import mmap
import os
import struct
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "FC Schalke 04 - Bastian König - FM24Career.fm"
CAL = ROOT / "data" / "fixtures" / "ha-calibration-5.json"
OUT = ROOT / "tmp" / "fm-spike" / "ha-trio-bridge.txt"
ZSTD_OFF = 26
ATTR_LOOKBACK = 24_000
PERSON_HEAD = 512 * 1024 * 1024
SCAN = 4096  # window size around loci

MENTAL = [
    "aggression", "anticipation", "bravery", "vision", "decisions",
    "determination", "flair", "leadership", "offTheBall", "positioning",
    "teamwork", "workRate", "composure", "concentration",
]

TRIO = ["Sam Kizza", "Paco Suárez", "Marco Tassinari"]
VALIDATORS = ["Dennis Seimen", "Yoan Robert"]


def d5(b: int) -> int:
    return int(round(b / 5))


def is_attrish(buf: bytes, i: int) -> bool:
    if i + 69 > len(buf):
        return False
    if buf[i + 34] or buf[i + 35] or buf[i + 43] != 0x01:
        return False
    return sum(1 for x in buf[i : i + 22] if 25 <= x <= 105) >= 12


def score_attr_window(window: bytes):
    by_u16: dict[int, list[tuple[int, bytes]]] = defaultdict(list)
    start = 0
    while True:
        z = window.find(b"\x00\x00", start)
        if z < 0 or z + 35 > len(window):
            break
        i = z - 34
        if i >= 0 and z == i + 34 and is_attrish(window, i):
            rec = window[i : i + 69]
            u16 = struct.unpack_from("<H", rec, 36)[0]
            by_u16[u16].append((i, rec))
            start = z + 69
        else:
            start = z + 1
    if not by_u16:
        return None
    best_u16 = max(
        by_u16.keys(),
        key=lambda u: (len(by_u16[u]), max(r[1][23] for r in by_u16[u]), max(r[0] for r in by_u16[u])),
    )
    cards = by_u16[best_u16]
    cards.sort(key=lambda t: (t[1][23], t[0]))
    return cards[-1]


def find_ca(mm, uid: int, det, lea):
    pat = struct.pack("<II", uid, uid)
    hits = []
    j = mm.find(pat, 0, PERSON_HEAD)
    while j >= 0 and len(hits) < 16:
        hits.append(j)
        j = mm.find(pat, j + 1, PERSON_HEAD)
    fallback = []
    for dab in hits:
        lo = max(0, dab - ATTR_LOOKBACK)
        hit = score_attr_window(bytes(mm[lo:dab]))
        if not hit:
            continue
        off, rec = hit
        ment = {k: d5(rec[i]) for i, k in enumerate(MENTAL)}
        if det is not None and ment["determination"] != det:
            fallback.append((lo + off, dab, ment, rec))
            continue
        if lea is not None and ment["leadership"] != lea:
            fallback.append((lo + off, dab, ment, rec))
            continue
        if det is None and not (14 <= ment["determination"] <= 20):
            fallback.append((lo + off, dab, ment, rec))
            continue
        return lo + off, dab, ment, rec
    return fallback[0] if fallback else None


def decompress(save: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="fmt-trio-", suffix=".bin")
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


def in_band(v: int, band) -> bool:
    return band[0] <= v <= band[1]


def parse_family(after: bytes) -> dict:
    """Classify post-double person-tail and extract sparse V|01 values."""
    # Prefer pattern at +39ish
    out = {"family": "unknown", "sparse": [], "pack_at": None, "len_byte": None}
    # Family A: 00* 01 01 01 V 01 ...
    for base in range(32, 48):
        if after[base : base + 3] == b"\x01\x01\x01":
            # if previous bytes are zeros-ish
            pre = after[base - 4 : base]
            if pre.count(0) >= 3 or after[base - 1] == 0:
                sparse = []
                i = base + 3
                while i + 1 < len(after) and len(sparse) < 12:
                    v, n = after[i], after[i + 1]
                    if 2 <= v <= 20 and n == 1:
                        sparse.append((i, v))
                        i += 2
                        continue
                    if v == 1:
                        i += 1
                        continue
                    break
                out["family"] = "A_sparse"
                out["sparse"] = sparse
                out["pack_at"] = i
                out["header_at"] = base
                return out
    # Family B: 00* XX 01 01 01... where XX often 0x14
    for base in range(32, 48):
        if after[base] == 0x14 and after[base + 1 : base + 4] == b"\x01\x01\x01":
            i = base + 1
            while i < len(after) and after[i] == 1:
                i += 1
            out["family"] = "B_len14"
            out["len_byte"] = after[base]
            out["sparse"] = []
            out["pack_at"] = i
            out["header_at"] = base
            return out
    return out


def band_of(players, name, attr):
    return next(p["bands"][attr] for p in players if p["name"] == name)


def locks_of(players, name):
    return next(p.get("locks") or {} for p in players if p["name"] == name)


def score_attr_at(vals: dict[str, int], players, names, attr) -> bool:
    for name in names:
        v = vals[name]
        if not (1 <= v <= 20):
            return False
        if not in_band(v, band_of(players, name, attr)):
            return False
        locks = locks_of(players, name)
        if attr in locks and v != locks[attr]:
            return False
    return True


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cal = json.loads(CAL.read_text(encoding="utf-8"))
    players = cal["players"]
    by_name = {p["name"]: p for p in players}
    lines: list[str] = []
    t0 = time.perf_counter()
    print("decompress…", flush=True)
    tmp = decompress(SAVE)

    loci = {}
    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in players:
                found = find_ca(mm, p["uid"], p.get("determination"), p.get("leadership"))
                if not found:
                    lines.append(f"MISS {p['name']}")
                    continue
                card, dbl, ment, rec = found
                after = bytes(mm[dbl : dbl + SCAN])
                before = bytes(mm[max(0, dbl - SCAN) : dbl])
                # gap card→double clipped
                gap_lo = min(card + 69, dbl)
                gap_hi = max(card + 69, dbl)
                gap = bytes(mm[gap_lo:gap_hi]) if gap_hi - gap_lo <= 20000 else b""
                fam = parse_family(after)
                loci[p["name"]] = {
                    "card": card,
                    "dbl": dbl,
                    "ment": ment,
                    "rec": rec,
                    "after": after,
                    "before": before,
                    "gap": gap,
                    "fam": fam,
                }
                lines.append(
                    f"{p['name']}: card={card} dbl={dbl} Det={ment['determination']} "
                    f"Lea={ment['leadership']} family={fam['family']} "
                    f"sparse={fam['sparse']} pack_at={fam['pack_at']}"
                )
                if fam["pack_at"] is not None:
                    pack = after[fam["pack_at"] : fam["pack_at"] + 32]
                    lines.append(
                        f"  pack: {' '.join(f'{b:02x}' for b in pack)} | "
                        f"raw={[b for b in pack[:16]]} d5={[d5(b) for b in pack[:16]]}"
                    )

            # --- Family decode notes ---
            lines.append("\n=== family A sparse interpretation ===")
            for name in ("Sam Kizza", "Paco Suárez"):
                if name not in loci:
                    continue
                sparse = loci[name]["fam"]["sparse"]
                lines.append(f"{name}: values={[v for _, v in sparse]}")
                # Hypothesis: slot0=Pro (Paco 20, Kizza 16), slot1=Tem (Kizza 15)
                if sparse:
                    lines.append(
                        f"  hyp Pro=slot0->{sparse[0][1] if sparse else None}; "
                        f"Tem=slot1->{sparse[1][1] if len(sparse)>1 else None}"
                    )

            lines.append("\n=== family B pack scan for Tassinari Tem/Con/Spo ===")
            if "Marco Tassinari" in loci:
                t = loci["Marco Tassinari"]
                pack_at = t["fam"]["pack_at"] or 54
                pack = t["after"][pack_at : pack_at + 64]
                tem_hits = [i for i, b in enumerate(pack) if 3 <= b <= 6]
                con_hits = [i for i, b in enumerate(pack) if 15 <= b <= 20]
                spo_hits = [i for i, b in enumerate(pack) if 1 <= b <= 7]
                lines.append(f"pack_at={pack_at}")
                lines.append(f"Tem3-6 idxs={tem_hits}")
                lines.append(f"Con15-20 idxs={con_hits}")
                lines.append(f"Spo1-7 idxs={spo_hits[:20]}")
                # For each Tem candidate, check same abs offset from dbl for Kizza/Paco
                lines.append("Tem candidate cross-check at same +off from dbl:")
                for i in tem_hits:
                    off = pack_at + i
                    vals = {n: loci[n]["after"][off] for n in TRIO if n in loci}
                    ok = score_attr_at(vals, players, [n for n in TRIO if n in loci], "temperament")
                    lines.append(f"  +{off}: {vals} trio_tem_ok={ok}")

                lines.append("Con candidate cross-check:")
                for i in con_hits:
                    off = pack_at + i
                    vals = {n: loci[n]["after"][off] for n in TRIO if n in loci}
                    ok = score_attr_at(vals, players, [n for n in TRIO if n in loci], "controversy")
                    lines.append(f"  +{off}: {vals} trio_con_ok={ok}")

            # --- Shared relative search on TRIO only (raw + d5), regions ---
            lines.append("\n=== trio shared offsets (raw) ===")
            attrs = [
                "professionalism",
                "temperament",
                "pressure",
                "controversy",
                "sportsmanship",
                "loyalty",
                "ambition",
            ]
            for region_name, getter in (
                ("after", lambda loc: loc["after"]),
                ("before", lambda loc: loc["before"]),
            ):
                lines.append(f"-- region={region_name} --")
                # before is stored as ending at dbl, so offset 0 is dbl-SCAN
                # for ranking we want dbl-relative: after uses +off from dbl;
                # before uses -SCAN+off ... report as dbl-relative.
                for enc_name, enc in (("raw", lambda b: int(b)), ("d5", d5)):
                    for attr in attrs:
                        hits = []
                        blob_len = SCAN
                        for off in range(blob_len):
                            vals = {}
                            ok = True
                            for name in TRIO:
                                loc = loci[name]
                                blob = getter(loc)
                                if region_name == "after":
                                    v = enc(blob[off])
                                    rel = off
                                else:
                                    v = enc(blob[off])
                                    rel = off - SCAN  # negative = before dbl
                                vals[name] = v
                                if not (1 <= v <= 20) or not in_band(
                                    v, band_of(players, name, attr)
                                ):
                                    ok = False
                                    break
                                locks = locks_of(players, name)
                                if attr in locks and v != locks[attr]:
                                    ok = False
                                    break
                            if ok:
                                # exclude CA-card absolute collisions: if abs pos falls in any card 69B
                                abs_positions = []
                                for name in TRIO:
                                    dbl = loci[name]["dbl"]
                                    abs_positions.append(
                                        dbl + (off if region_name == "after" else off - SCAN)
                                    )
                                in_card = False
                                for name, ap in zip(TRIO, abs_positions):
                                    c = loci[name]["card"]
                                    if c <= ap < c + 69:
                                        in_card = True
                                        break
                                if in_card:
                                    continue
                                hits.append((rel if region_name == "after" else off - SCAN, vals))
                        lines.append(f"{enc_name} {attr}: {len(hits)}")
                        for rel, vals in hits[:12]:
                            pretty = ", ".join(
                                f"{n.split()[0]}={vals[n]}" for n in TRIO
                            )
                            lines.append(f"  rel={rel}: {pretty}")

            # --- Joint Pro+Tem for trio (distinct offs) ---
            lines.append("\n=== trio joint Pro+Tem (raw after) ===")
            pro_offs = []
            tem_offs = []
            for off in range(SCAN):
                pvals = {n: loci[n]["after"][off] for n in TRIO}
                tvals = {n: loci[n]["after"][off] for n in TRIO}
                if score_attr_at(pvals, players, TRIO, "professionalism"):
                    # skip if inside CA card abs
                    if not any(
                        loci[n]["card"] <= loci[n]["dbl"] + off < loci[n]["card"] + 69
                        for n in TRIO
                    ):
                        pro_offs.append(off)
                if score_attr_at(tvals, players, TRIO, "temperament"):
                    if not any(
                        loci[n]["card"] <= loci[n]["dbl"] + off < loci[n]["card"] + 69
                        for n in TRIO
                    ):
                        tem_offs.append(off)
            lines.append(f"Pro offs={pro_offs[:30]} (n={len(pro_offs)})")
            lines.append(f"Tem offs={tem_offs[:30]} (n={len(tem_offs)})")
            combos = 0
            for po in pro_offs:
                for to in tem_offs:
                    if po == to:
                        continue
                    combos += 1
                    if combos <= 25:
                        pv = {n: loci[n]["after"][po] for n in TRIO}
                        tv = {n: loci[n]["after"][to] for n in TRIO}
                        lines.append(f"  Pro+{po}={pv} Tem+{to}={tv}")
            lines.append(f"combo_count={combos}")

            # --- Validate top joint with Seimen/Yoan if any Pro+Tem ---
            lines.append("\n=== validator check on Pro/Tem offs ===")
            for po in pro_offs[:20]:
                vals = {n: loci[n]["after"][po] for n in loci}
                ok5 = score_attr_at(vals, players, list(loci), "professionalism")
                lines.append(f"Pro+{po} all5={ok5} vals={{{', '.join(f'{k.split()[0]}={v}' for k,v in vals.items())}}}")
            for to in tem_offs[:20]:
                vals = {n: loci[n]["after"][to] for n in loci}
                ok5 = score_attr_at(vals, players, list(loci), "temperament")
                lines.append(f"Tem+{to} all5={ok5} vals={{{', '.join(f'{k.split()[0]}={v}' for k,v in vals.items())}}}")

            # --- Pointer chase: u32s near family header that might link HA block ---
            lines.append("\n=== u32 near after-double header (possible HA pointers) ===")
            for name, loc in loci.items():
                after = loc["after"]
                hdr = loc["fam"].get("header_at", 39)
                window = after[max(0, hdr - 32) : hdr + 64]
                base = loc["dbl"] + max(0, hdr - 32)
                interesting = []
                for i in range(0, len(window) - 3, 4):
                    v = struct.unpack_from("<I", window, i)[0]
                    if 1000 < v < PERSON_HEAD and v != by_name[name]["uid"]:
                        interesting.append((base + i, v))
                lines.append(f"{name}: hdr={hdr} u32s={interesting[:12]}")

            # Try: for each player, search whole after[0:512] for Pro lock byte patterns as u16
            lines.append("\n=== u16 LE search for distinctive locks near dbl ===")
            # Kizza Tem=15 as u16 15 or 15*5=75
            for label, needle in (("Tem15", 15), ("Tem75", 75), ("Pro20", 20), ("Pro100", 100)):
                lines.append(f"-- needle {label}={needle} --")
                for name in TRIO:
                    after = loci[name]["after"]
                    pat = struct.pack("<H", needle)
                    hits = []
                    start = 0
                    while True:
                        j = after.find(pat, start)
                        if j < 0 or len(hits) >= 8:
                            break
                        hits.append(j)
                        start = j + 1
                    lines.append(f"  {name}: {hits}")

        finally:
            mm.close()

    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass

    lines.append(f"\nelapsedMs={int((time.perf_counter()-t0)*1000)}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    for line in lines:
        if any(
            x in line
            for x in (
                "family=",
                "sparse=",
                "hyp ",
                "Tem ",
                "Con ",
                "Pro offs",
                "Tem offs",
                "combo",
                "all5=",
                "pack_at",
                "idxs=",
                "raw professionalism",
                "raw temperament",
                "d5 professionalism",
                "d5 temperament",
                "MISS",
                "trio_tem",
                "trio_con",
            )
        ):
            print(line.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
