"""Single-pass: *1/*5/*10 packed attrs + UID/05 8c 0c dumps for all fixture players."""

from __future__ import annotations

import json
import struct
from collections import Counter
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/scale-blocks.txt")

MARKER = bytes.fromhex("058c0c")

MENTAL = [
    "aggression",
    "anticipation",
    "bravery",
    "composure",
    "concentration",
    "decisions",
    "determination",
    "flair",
    "leadership",
    "offTheBall",
    "positioning",
    "teamwork",
    "vision",
    "workRate",
]
PHYS = [
    "acceleration",
    "agility",
    "balance",
    "jumpingReach",
    "naturalFitness",
    "pace",
    "stamina",
    "strength",
]
TECH = [
    "crossing",
    "dribbling",
    "finishing",
    "firstTouch",
    "heading",
    "longShots",
    "marking",
    "passing",
    "tackling",
    "technique",
]


def gv(p: dict, group: str, keys: list[str]) -> list[int]:
    return [p["attributes"][group][k] for k in keys]


def best_cover(blob: bytes, needed: list[int], win: int) -> list[int]:
    need = Counter(needed)
    total = sum(need.values())
    hits = []
    for i in range(0, max(1, len(blob) - win + 1)):
        have = Counter(blob[i : i + win])
        if sum(min(have[v], c) for v, c in need.items()) == total:
            hits.append(i)
    return hits


def stride_hits(blob: bytes, vals: list[int], stride: int) -> list[int]:
    span = (len(vals) - 1) * stride + 1
    out = []
    for start in range(0, len(blob) - span + 1):
        if all(blob[start + i * stride] == vals[i] for i in range(len(vals))):
            out.append(start)
    return out


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    # Build pattern set: name -> list of (label, bytes, limit)
    patterns: list[tuple[str, str, bytes, int]] = []
    # Also track UIDs / doubles / fingerprints per player
    player_meta = []
    for p in PLAYERS:
        name = p["name"]
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        meta = {
            "name": name,
            "p": p,
            "uid": uid,
            "double": uid + uid,
            "uid_marker_rows": [],
            "double_rows": [],
        }
        player_meta.append(meta)

        groups: dict[str, list[int]] = {}
        if "mental" in p["attributes"]:
            groups["mental"] = gv(p, "mental", MENTAL)
        if "physical" in p["attributes"]:
            groups["phys"] = gv(p, "physical", PHYS)
        if "technical" in p["attributes"] and "crossing" in p["attributes"]["technical"]:
            groups["tech"] = gv(p, "technical", TECH)
        if "goalkeeping" in p["attributes"]:
            groups["gk"] = list(p["attributes"]["goalkeeping"].values())

        for scale in (1, 5, 10):
            for gname, vals in groups.items():
                scaled = [v * scale for v in vals]
                if any(v > 255 for v in scaled):
                    continue
                patterns.append((name, f"{gname}|x{scale}", bytes(scaled), 5))
                patterns.append((name, f"{gname}|x{scale}|rev", bytes(scaled[::-1]), 5))

        # fingerprints
        a = p["attributes"]
        fps: list[tuple[str, list[int]]] = []
        if "mental" in a:
            m = a["mental"]
            fps += [
                ("det_lea", [m["determination"], m["leadership"]]),
                (
                    "conc_dec_det",
                    [m["concentration"], m["decisions"], m["determination"]],
                ),
                ("flair_lea_otb", [m["flair"], m["leadership"], m["offTheBall"]]),
            ]
        if "physical" in a:
            ph = a["physical"]
            fps += [
                (
                    "bal_jr_nf",
                    [ph["balance"], ph["jumpingReach"], ph["naturalFitness"]],
                ),
                (
                    "nf_pace_sta",
                    [ph["naturalFitness"], ph["pace"], ph["stamina"]],
                ),
            ]
        if "technical" in a and "marking" in a["technical"]:
            t = a["technical"]
            fps += [
                ("head_ls_mark", [t["heading"], t["longShots"], t["marking"]]),
                (
                    "pass_tack_tech",
                    [t["passing"], t["tackling"], t["technique"]],
                ),
            ]
        if "setPieces" in a:
            s = a["setPieces"]
            fps.append(
                (
                    "set4",
                    [
                        s["corners"],
                        s["freeKickTaking"],
                        s["longThrows"],
                        s["penaltyTaking"],
                    ],
                )
            )
        if "goalkeeping" in a:
            g = a["goalkeeping"]
            fps += [
                (
                    "gk_ecc_ft_han",
                    [g["eccentricity"], g["firstTouch"], g["handling"]],
                ),
                ("otb_flair", [a["mental"]["offTheBall"], a["mental"]["flair"]]),
            ]
        for scale in (1, 5):
            for label, vals in fps:
                scaled = [v * scale for v in vals]
                if any(v > 255 for v in scaled):
                    continue
                patterns.append((name, f"fp|{label}|x{scale}", bytes(scaled), 8))

    # results: (name,label) -> [abs]
    hits: dict[tuple[str, str], list[int]] = {(n, l): [] for n, l, _, _ in patterns}
    # dedupe nearby duplicate from carry
    last_hit: dict[tuple[str, str], int] = {}

    abs_base = 0
    carry = b""
    overlap = 512

    print(f"single-pass over {SAVE.name}; patterns={len(patterns)}")
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

                # pattern search
                for name, label, pat, limit in patterns:
                    key = (name, label)
                    if len(hits[key]) >= limit:
                        continue
                    start = 0
                    while len(hits[key]) < limit:
                        i = data.find(pat, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        if last_hit.get(key) == abs_off:
                            start = i + 1
                            continue
                        last_hit[key] = abs_off
                        hits[key].append(abs_off)
                        start = i + 1

                # UID / double-UID / marker windows
                for meta in player_meta:
                    uid = meta["uid"]
                    if len(meta["uid_marker_rows"]) < 8:
                        start = 0
                        while len(meta["uid_marker_rows"]) < 8:
                            i = data.find(uid, start)
                            if i < 0:
                                break
                            abs_off = abs_base - len(carry) + i
                            win = data[i : i + 96]
                            j = win.find(MARKER)
                            if j >= 0:
                                ws = max(0, i - 16)
                                we = min(len(data), i + 220)
                                blob = data[ws:we]
                                marks = []
                                pos = 0
                                while True:
                                    k = blob.find(MARKER, pos)
                                    if k < 0:
                                        break
                                    marks.append(k)
                                    pos = k + 1
                                # avoid near-dup
                                if not meta["uid_marker_rows"] or meta[
                                    "uid_marker_rows"
                                ][-1]["uid_abs"] != abs_off:
                                    meta["uid_marker_rows"].append(
                                        {
                                            "uid_abs": abs_off,
                                            "marker_rel": j,
                                            "marks": marks,
                                            "blob": blob,
                                        }
                                    )
                            start = i + 1

                    dbl = meta["double"]
                    if len(meta["double_rows"]) < 6:
                        start = 0
                        while len(meta["double_rows"]) < 6:
                            i = data.find(dbl, start)
                            if i < 0:
                                break
                            abs_off = abs_base - len(carry) + i
                            blob = data[i : i + 256]
                            j = blob.find(MARKER)
                            if not meta["double_rows"] or meta["double_rows"][-1][
                                "abs"
                            ] != abs_off:
                                meta["double_rows"].append(
                                    {
                                        "abs": abs_off,
                                        "marker_rel": j if j >= 0 else None,
                                        "blob": blob,
                                    }
                                )
                            start = i + 1

                abs_base += len(block)
                carry = data[-overlap:]
        finally:
            reader.close()

    # ---- report packed ----
    lines.append("==== global packed consecutive (screen / rev) ====")
    for meta in player_meta:
        name = meta["name"]
        lines.append(f"\n## {name}")
        keys = sorted(
            k for k in hits if k[0] == name and not k[1].startswith("fp|")
        )
        for key in keys:
            label = key[1]
            h = hits[key]
            if h or "|x1" in label:  # always show *1 even if empty
                lines.append(f"  {label}: n={len(h)} {h[:5]}")
        lines.append("  fingerprints:")
        for key in sorted(
            k for k in hits if k[0] == name and k[1].startswith("fp|")
        ):
            h = hits[key]
            lines.append(f"    {key[1]}: n={len(h)} first={h[:4]}")

    # ---- UID+marker ----
    lines.append("\n\n==== UID neighborhoods containing 05 8c 0c ====")
    for meta in player_meta:
        name = meta["name"]
        p = meta["p"]
        rows = meta["uid_marker_rows"]
        lines.append(f"\n## {name} uid-marker windows={len(rows)}")
        for r in rows:
            blob = r["blob"]
            lines.append(
                f"  uid@abs={r['uid_abs']} marker_rel=+{r['marker_rel']} marks={r['marks']}"
            )
            lines.append(f"    hex: {blob[:160].hex(' ')}")
            for mi in r["marks"][:2]:
                post = list(blob[mi + 3 : mi + 3 + 80])
                lines.append(f"    post-marker@{mi} u8: {post}")
                region = blob[mi:]
                if "mental" in p["attributes"]:
                    mental = gv(p, "mental", MENTAL)
                    phys = gv(p, "physical", PHYS)
                    for scale, lab in ((1, "raw"), (5, "x5")):
                        mcov = best_cover(region, [v * scale for v in mental], 64)
                        pcov = best_cover(region, [v * scale for v in phys], 48)
                        lines.append(
                            f"      mental {lab} full-cover offs={mcov[:8]} "
                            f"(n={len(mcov)})"
                        )
                        lines.append(
                            f"      phys {lab} full-cover offs={pcov[:8]} "
                            f"(n={len(pcov)})"
                        )
                # stride
                if "mental" in p["attributes"]:
                    mental = gv(p, "mental", MENTAL)
                    for scale in (1, 5):
                        vals = [v * scale for v in mental]
                        for stride in (1, 2, 3, 4):
                            sh = stride_hits(region, vals, stride)
                            if sh:
                                lines.append(
                                    f"      mental x{scale} stride={stride} "
                                    f"starts={sh[:8]}"
                                )
                    phys = gv(p, "physical", PHYS)
                    for scale in (1, 5):
                        vals = [v * scale for v in phys]
                        for stride in (1, 2, 3, 4):
                            sh = stride_hits(region, vals, stride)
                            if sh:
                                lines.append(
                                    f"      phys x{scale} stride={stride} "
                                    f"starts={sh[:8]}"
                                )

        # distinctive positions in first blob
        if rows:
            blob = rows[0]["blob"]
            lines.append("  distinctive in first blob:")
            if name.startswith("Patrick"):
                dist = [("conc18", 18), ("pen5", 5), ("conc*5", 90), ("mark*5", 85)]
            elif name.startswith("Robert"):
                dist = [("dec18", 18), ("nf9", 9), ("dec*5", 90), ("nf*5", 45)]
            else:
                dist = [("otb1", 1), ("flair8", 8), ("fk3", 3), ("flair*5", 40)]
            for lab, val in dist:
                pos = [i for i, b in enumerate(blob) if b == val]
                lines.append(f"    {lab}={val} @ {pos[:24]}")

    # ---- double UID ----
    lines.append("\n\n==== double-UID dumps ====")
    for meta in player_meta:
        name = meta["name"]
        p = meta["p"]
        rows = meta["double_rows"]
        lines.append(f"\n## {name} double-UID hits={len(rows)}")
        for r in rows:
            lines.append(f"  abs={r['abs']} marker_rel={r['marker_rel']}")
            lines.append(f"    hex: {r['blob'][:128].hex(' ')}")
            lines.append(f"    u8: {list(r['blob'][:96])}")
            if r["marker_rel"] is not None and "mental" in p["attributes"]:
                region = r["blob"][r["marker_rel"] :]
                mental = gv(p, "mental", MENTAL)
                for scale in (1, 5):
                    mcov = best_cover(region, [v * scale for v in mental], 64)
                    lines.append(
                        f"    mental x{scale} full-cover offs={mcov[:8]} n={len(mcov)}"
                    )
                for scale in (1, 5):
                    vals = [v * scale for v in mental]
                    for stride in (1, 2, 3, 4):
                        sh = stride_hits(region, vals, stride)
                        if sh:
                            lines.append(
                                f"    mental x{scale} stride={stride} starts={sh[:8]}"
                            )

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text[:10000])
    print(f"\n... wrote {OUT} ({len(text)} chars)")


if __name__ == "__main__":
    main()
