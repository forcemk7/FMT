"""Find attr fingerprint hits that share a geometry vs UniqueID / personIndex / double-UID.

Uses distinctive consecutive attr packs (x1 and x5). A real locus should put
the SAME relative offset (approx) for all three fixture players.
"""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/attr-locus.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}

DOUBLE = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}
IDX = {
    "Dennis Seimen": 1790,
    "Patrick Bandeira": 1198,
    "Robert Müller": 1233,
}
INTERNAL = {
    "Dennis Seimen": 0x0001BB6D,
    "Patrick Bandeira": 0x0005191C,
    "Robert Müller": 0x00059603,
}

# Distinctive fingerprints: (label, scale, attr_path list)
# Prefer rare / high-contrast sequences
FPS: dict[str, list[tuple[str, int, list[int]]]] = {}


def flat_attrs(p: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for group, attrs in p["attributes"].items():
        for k, v in attrs.items():
            out[f"{group}.{k}"] = int(v)
    out["det"] = int(p["det"])
    out["lea"] = int(p["lea"])
    return out


def build_fps() -> None:
    for name, p in PLAYERS.items():
        a = flat_attrs(p)
        specs: list[tuple[str, list[str]]] = []
        if "goalkeeping.aerialReach" in a:
            specs += [
                ("gk_ar_coa_com", ["goalkeeping.aerialReach", "goalkeeping.commandOfArea", "goalkeeping.communication"]),
                ("gk_ecc_ft_han", ["goalkeeping.eccentricity", "goalkeeping.firstTouch", "goalkeeping.handling"]),
                ("gk_punch_ref_rush", ["goalkeeping.punchingTendency", "goalkeeping.reflexes", "goalkeeping.rushingOutTendency"]),
                ("men_flair_lea_otb", ["mental.flair", "mental.leadership", "mental.offTheBall"]),
                ("phy_acc_agi_bal", ["physical.acceleration", "physical.agility", "physical.balance"]),
            ]
        else:
            specs += [
                ("tech_cro_dri_fin", ["technical.crossing", "technical.dribbling", "technical.finishing"]),
                ("tech_head_ls_mark", ["technical.heading", "technical.longShots", "technical.marking"]),
                ("tech_pass_tack_tech", ["technical.passing", "technical.tackling", "technical.technique"]),
                ("men_conc_dec_det", ["mental.concentration", "mental.decisions", "mental.determination"]),
                ("phy_bal_jr_nf", ["physical.balance", "physical.jumpingReach", "physical.naturalFitness"]),
                ("phy_pace_sta_str", ["physical.pace", "physical.stamina", "physical.strength"]),
            ]
        specs += [
            ("det_lea", ["det", "lea"]),
            ("men_agg_ant_bra", ["mental.aggression", "mental.anticipation", "mental.bravery"]),
        ]
        entry = []
        for label, keys in specs:
            vals = [a[k] for k in keys]
            for scale in (1, 5):
                packed = bytes(v * scale for v in vals)
                entry.append((f"{label}|x{scale}", scale, list(vals), packed))
        FPS[name] = entry  # type: ignore[assignment]


def extract(abs_target: int, length: int, before: int = 0) -> bytes:
    start = abs_target - before
    end = abs_target + length
    abs_base = 0
    carry = b""
    buf = bytearray()
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                chunk_start = abs_base - len(carry)
                if chunk_start < end and abs_base + len(block) > start:
                    already = len(buf)
                    want = start + already
                    lo = max(0, start - chunk_start, want - chunk_start)
                    hi = min(len(data), end - chunk_start)
                    if lo < hi:
                        buf.extend(data[lo:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= before + length:
                    break
        finally:
            reader.close()
    return bytes(buf)


def main() -> None:
    build_fps()
    lines: list[str] = []

    # --- Hot zone dump: Bandeira x5 bal_jr_nf near double-UID ---
    lines.append("======== hot zone: Band double-UID neighborhood ========")
    band_dbl = DOUBLE["Patrick Bandeira"]
    zone = extract(band_dbl, 512, before=12000)
    a = flat_attrs(PLAYERS["Patrick Bandeira"])
    needle = bytes(
        [
            a["physical.balance"] * 5,
            a["physical.jumpingReach"] * 5,
            a["physical.naturalFitness"] * 5,
        ]
    )
    lines.append(f"needle bal/jr/nf x5 = {list(needle)} ({needle.hex()})")
    pos = 0
    hits = []
    while True:
        j = zone.find(needle, pos)
        if j < 0:
            break
        abs_hit = band_dbl - 12000 + j
        hits.append(abs_hit)
        rel = abs_hit - band_dbl
        ctx = zone[max(0, j - 16) : j + 48]
        lines.append(f"  @{abs_hit} rel_dbl={rel:+d} ctx={ctx.hex(' ')}")
        pos = j + 1
    lines.append(f"  hit_count={len(hits)}")

    # Also dump Seimen/Müller for same x5 pack near their doubles
    for name in ("Dennis Seimen", "Robert Müller"):
        dbl = DOUBLE[name]
        aa = flat_attrs(PLAYERS[name])
        n = bytes(
            [
                aa["physical.balance"] * 5,
                aa["physical.jumpingReach"] * 5,
                aa["physical.naturalFitness"] * 5,
            ]
        )
        z = extract(dbl, 512, before=12000)
        lines.append(f"\n{name} bal/jr/nf x5={list(n)} near dbl:")
        pos = 0
        c = 0
        while c < 8:
            j = z.find(n, pos)
            if j < 0:
                break
            abs_hit = dbl - 12000 + j
            lines.append(f"  @{abs_hit} rel_dbl={abs_hit - dbl:+d}")
            pos = j + 1
            c += 1
        if c == 0:
            lines.append("  (none in -12k..+512)")

    # --- Single-pass: fingerprint hits + distance to UID/idx/iid/double ---
    lines.append("\n======== single-pass FP -> UID/idx geometry ========")

    # Prepare needles per player
    needles: dict[bytes, list[tuple[str, str, int, list[int]]]] = defaultdict(list)
    # map packed bytes -> list of (player, label, scale, vals)
    for name, entries in FPS.items():
        for label, scale, vals, packed in entries:  # type: ignore[misc]
            needles[packed].append((name, label, scale, vals))

    # Collect: player -> label -> list of abs hits (cap)
    hits_by: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    # Also store abs of all UID hits for distance calc
    uid_abs: dict[str, list[int]] = defaultdict(list)
    idx_pat = {n: struct.pack("<I", IDX[n]) for n in IDX}
    iid_pat = {n: struct.pack("<I", INTERNAL[n]) for n in INTERNAL}
    uid_pat = {n: struct.pack("<I", PLAYERS[n]["uid"]) for n in PLAYERS}

    abs_base = 0
    carry = b""
    OVERLAP = 64
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                chunk_start = abs_base - len(carry)

                for name, pat in uid_pat.items():
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        abs_hit = chunk_start + j
                        if abs_hit >= abs_base and len(uid_abs[name]) < 250:
                            uid_abs[name].append(abs_hit)
                        start = j + 1

                for packed, owners in needles.items():
                    start = 0
                    while True:
                        j = data.find(packed, start)
                        if j < 0:
                            break
                        abs_hit = chunk_start + j
                        if abs_hit >= abs_base:
                            for name, label, scale, vals in owners:
                                if len(hits_by[name][label]) < 40:
                                    hits_by[name][label].append(abs_hit)
                        start = j + 1

                abs_base += len(block)
                carry = data[-OVERLAP:]
        finally:
            reader.close()

    def nearest(abs_hit: int, anchors: list[int]) -> tuple[int, int] | None:
        if not anchors:
            return None
        best = min(anchors, key=lambda a: abs(a - abs_hit))
        return best, abs_hit - best

    # Per-label: compare geometry across players that share the label family
    # Build label families without player-specific prefix issues — use last part
    all_labels = sorted({lab for n in hits_by for lab in hits_by[n]})
    lines.append(f"UID hit counts: { {n: len(uid_abs[n]) for n in uid_abs} }")

    for label in all_labels:
        # players that have this label
        owners = [n for n in PLAYERS if label in hits_by[n]]
        if len(owners) < 2:
            continue
        lines.append(f"\n### {label} owners={owners}")
        geo_buckets: dict[int, list[str]] = defaultdict(list)
        for name in owners:
            hs = hits_by[name][label]
            # score each hit by proximity to double-UID and any UID
            scored = []
            for h in hs:
                d_dbl = h - DOUBLE[name]
                near_uid = nearest(h, uid_abs[name])
                scored.append((abs(d_dbl), d_dbl, h, near_uid))
            scored.sort()
            lines.append(f"  {name}: n={len(hs)} closest_to_dbl:")
            for _, d_dbl, h, near_uid in scored[:6]:
                uid_s = (
                    f"uid@{near_uid[0]} rel={near_uid[1]:+d}"
                    if near_uid
                    else "uid=?"
                )
                lines.append(f"    fp@{h} dbl_rel={d_dbl:+d} {uid_s}")
                # bucket dbl_rel to 256-byte bins for cross-player agreement
                geo_buckets[d_dbl // 256].append(name)
            # also check personIndex near best hit
            best_h = scored[0][2] if scored else None
            if best_h is not None:
                win = extract(best_h, 128, before=128)
                ip = idx_pat[name]
                iid = iid_pat[name]
                lines.append(
                    f"    best: idx_in_win={win.find(ip)} iid_in_win={win.find(iid)} "
                    f"uid_in_win={win.find(uid_pat[name])}"
                )
                lines.append(f"    best ctx: {win[128-16:128+32].hex(' ')}")

        # cross-player same dbl_rel bin?
        shared = {b: v for b, v in geo_buckets.items() if len(set(v)) >= 2}
        if shared:
            lines.append(f"  SHARED dbl_rel bins (256B): { {k: list(set(v)) for k,v in shared.items()} }")

    # --- Cross-check: same absolute region containing all three ×5 det_lea? unlikely ---
    # Dump double-UID body as possible (attr ^ mask) check using Seimen rare low attrs
    lines.append("\n======== double-UID body decode probes ========")
    for name, dbl in DOUBLE.items():
        body = extract(dbl, 200)[54:120]
        a = flat_attrs(PLAYERS[name])
        vals = list(a.values())
        # how many body bytes equal some attr or attr*5
        raw_hits = sum(1 for b in body if b in vals)
        x5_vals = {v * 5 for v in vals if v * 5 <= 255}
        x5_hits = sum(1 for b in body if b in x5_vals)
        lines.append(f"{name}: body[54:120] raw_attr_byte_hits={raw_hits}/{len(body)} x5_hits={x5_hits}")
        lines.append(f"  body: {list(body[:40])}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
