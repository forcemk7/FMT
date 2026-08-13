"""Hunt 05 8c 0c attribute blocks linked to each player's internal ID."""

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
INTERNAL = {
    "Dennis Seimen": 0x0001BB6D,
    "Patrick Bandeira": 0x0005191C,
    "Robert Müller": 0x00059603,
}
OUT = Path("tmp/fm-spike/iid-marker-blocks.txt")

MARKER = bytes.fromhex("058c0c")
# Variant headers seen earlier near attr-looking data
MARKERS = [
    bytes.fromhex("058c0c"),
    bytes.fromhex("050c1a058c0c"),
    bytes.fromhex("050c19058c0c"),
    bytes.fromhex("05cc1b058c0c"),
]

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

    meta = []
    for p in PLAYERS:
        name = p["name"]
        meta.append(
            {
                "name": name,
                "p": p,
                "iid": struct.pack("<I", INTERNAL[name]),
                "uid": struct.pack("<I", p["uid"] & 0xFFFFFFFF),
                "iid_count": 0,
                # iid hit with marker in +/- window
                "iid_near_marker": [],
                # marker hit with iid in preceding 96 bytes
                "marker_with_iid": [],
            }
        )

    # Person-index from double-UID (after ffff): Bandeira 0x04ae, Müller 0x04d1, Seimen 0x06fe
    INDEX = {
        "Dennis Seimen": 0x06FE,
        "Patrick Bandeira": 0x04AE,
        "Robert Müller": 0x04D1,
    }
    for m in meta:
        m["idx"] = struct.pack("<I", INDEX[m["name"]])
        m["idx_near_marker"] = []

    R = 384
    abs_base = 0
    carry = b""
    overlap = R * 2 + 16

    print(f"scanning {SAVE.name} for iid-marker links...")
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

                for m in meta:
                    iid = m["iid"]
                    uid = m["uid"]
                    idx = m["idx"]

                    # --- IID occurrences ---
                    start = 0
                    while True:
                        i = data.find(iid, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        m["iid_count"] += 1
                        ws = max(0, i - R)
                        we = min(len(data), i + 4 + R)
                        win = data[ws:we]
                        base = i - ws
                        # marker search relative to iid
                        mark_rels = []
                        for mk in MARKERS:
                            pos = 0
                            while True:
                                j = win.find(mk, pos)
                                if j < 0:
                                    break
                                mark_rels.append((j - base, mk.hex()))
                                pos = j + 1
                        if mark_rels and len(m["iid_near_marker"]) < 20:
                            uid_rel = win.find(uid)
                            blob_from = max(0, base - 32)
                            blob = win[blob_from:]
                            m["iid_near_marker"].append(
                                {
                                    "iid_abs": abs_off,
                                    "marks": mark_rels[:8],
                                    "uid_rel": (uid_rel - base) if uid_rel >= 0 else None,
                                    "blob": blob[:256],
                                    "hex_before": win[max(0, base - 48) : base].hex(" "),
                                    "hex_after": win[base : base + 96].hex(" "),
                                }
                            )
                        start = i + 1

                    # --- INDEX (double-UID person idx) near marker ---
                    if len(m["idx_near_marker"]) < 12:
                        start = 0
                        while len(m["idx_near_marker"]) < 12:
                            i = data.find(idx, start)
                            if i < 0:
                                break
                            abs_off = abs_base - len(carry) + i
                            win = data[max(0, i - 64) : i + 192]
                            base = i - max(0, i - 64)
                            j = win.find(MARKER)
                            if j >= 0:
                                # require iid or uid also nearby OR skip filter (index is short!)
                                # 0x04ae is only 2 meaningful bytes often — reduce false positives:
                                # require marker within +128 and at least one more signature
                                iid_here = win.find(iid)
                                uid_here = win.find(uid)
                                if iid_here >= 0 or uid_here >= 0 or (
                                    j - base
                                ) in range(0, 96):
                                    # still too noisy for bare index — require iid or uid
                                    if iid_here >= 0 or uid_here >= 0:
                                        m["idx_near_marker"].append(
                                            {
                                                "idx_abs": abs_off,
                                                "marker_rel": j - base,
                                                "iid_rel": (iid_here - base)
                                                if iid_here >= 0
                                                else None,
                                                "uid_rel": (uid_here - base)
                                                if uid_here >= 0
                                                else None,
                                                "blob": win[j : j + 160],
                                            }
                                        )
                            start = i + 1

                    # --- Marker occurrences with IID in preceding 80 bytes ---
                    if len(m["marker_with_iid"]) < 15:
                        start = 0
                        while len(m["marker_with_iid"]) < 15:
                            i = data.find(MARKER, start)
                            if i < 0:
                                break
                            abs_off = abs_base - len(carry) + i
                            pre = data[max(0, i - 96) : i]
                            post = data[i : i + 160]
                            j = pre.find(iid)
                            if j >= 0:
                                uid_rel = pre.find(uid)
                                m["marker_with_iid"].append(
                                    {
                                        "marker_abs": abs_off,
                                        "iid_rel": j - len(pre),  # negative
                                        "uid_rel_pre": (uid_rel - len(pre))
                                        if uid_rel >= 0
                                        else None,
                                        "pre_hex": pre.hex(" "),
                                        "post": post,
                                    }
                                )
                            start = i + 1

                abs_base += len(block)
                carry = data[-overlap:]
        finally:
            reader.close()

    # ---- report ----
    for m in meta:
        name = m["name"]
        p = m["p"]
        lines.append(
            f"\n======== {name} iid=0x{INTERNAL[name]:08X} idx=0x{INDEX[name]:04X} "
            f"iid_hits={m['iid_count']} ========"
        )
        lines.append(
            f"  iid_near_marker={len(m['iid_near_marker'])} "
            f"marker_with_iid_pre={len(m['marker_with_iid'])} "
            f"idx_near_marker={len(m['idx_near_marker'])}"
        )

        mental = gv(p, "mental", MENTAL) if "mental" in p["attributes"] else []
        phys = gv(p, "physical", PHYS) if "physical" in p["attributes"] else []

        lines.append("\n  -- iid near marker --")
        for r in m["iid_near_marker"]:
            lines.append(
                f"  iid@abs={r['iid_abs']} marks={r['marks']} uid_rel={r['uid_rel']}"
            )
            lines.append(f"    before: {r['hex_before']}")
            lines.append(f"    after:  {r['hex_after']}")
            blob = r["blob"]
            # cover scans on whole blob
            if mental:
                for scale, lab in ((1, "raw"), (5, "x5")):
                    mcov = best_cover(blob, [v * scale for v in mental], 64)
                    pcov = best_cover(blob, [v * scale for v in phys], 48)
                    lines.append(
                        f"    mental {lab} cover offs={mcov[:6]} n={len(mcov)}; "
                        f"phys {lab} cover offs={pcov[:6]} n={len(pcov)}"
                    )
                for scale in (1, 5):
                    vals = [v * scale for v in mental]
                    for stride in (1, 2, 3, 4):
                        sh = stride_hits(blob, vals, stride)
                        if sh:
                            lines.append(
                                f"    mental x{scale} stride={stride} @ {sh[:6]}"
                            )

        lines.append("\n  -- marker preceded by iid --")
        for r in m["marker_with_iid"]:
            post = r["post"]
            lines.append(
                f"  marker@abs={r['marker_abs']} iid_rel={r['iid_rel']} "
                f"uid_pre={r['uid_rel_pre']}"
            )
            lines.append(f"    pre: {r['pre_hex']}")
            lines.append(f"    post u8: {list(post[:96])}")
            if mental:
                for scale, lab in ((1, "raw"), (5, "x5")):
                    mcov = best_cover(post, [v * scale for v in mental], 64)
                    pcov = best_cover(post, [v * scale for v in phys], 48)
                    lines.append(
                        f"    mental {lab} cover offs={mcov[:6]} n={len(mcov)}; "
                        f"phys {lab} cover offs={pcov[:6]} n={len(pcov)}"
                    )
                # distinctive adjacent pairs at start of post
                if name.startswith("Patrick"):
                    # look for lea=14 near det=16 somewhere in post as raw
                    for i in range(len(post) - 1):
                        if post[i] == 16 and post[i + 1] == 14:
                            lines.append(
                                f"    det,lea raw @+{i}: {list(post[i : i + 24])}"
                            )
                elif name.startswith("Robert"):
                    for i in range(len(post) - 1):
                        if post[i] == 16 and post[i + 1] == 17:
                            lines.append(
                                f"    det,lea raw @+{i}: {list(post[i : i + 24])}"
                            )
                else:
                    for i in range(len(post) - 1):
                        if post[i] == 18 and post[i + 1] == 16:
                            lines.append(
                                f"    det,lea raw @+{i}: {list(post[i : i + 24])}"
                            )

        lines.append("\n  -- idx + iid/uid near marker --")
        for r in m["idx_near_marker"]:
            lines.append(
                f"  idx@abs={r['idx_abs']} marker_rel={r['marker_rel']} "
                f"iid_rel={r['iid_rel']} uid_rel={r['uid_rel']}"
            )
            lines.append(f"    post-marker: {list(r['blob'][:80])}")

        # ---- Compare: if we got post-marker blobs, try fixed-offset lea/nf diffs ----
        posts = [r["post"] for r in m["marker_with_iid"]]
        if posts:
            lines.append(f"\n  first post hex: {posts[0][:128].hex(' ')}")

    # Cross-player: if each has ≥1 marker_with_iid post, diff first posts for lea/nf
    lines.append("\n\n======== cross-player post-marker fixed offset probes ========")
    posts = {}
    for m in meta:
        if m["marker_with_iid"]:
            posts[m["name"]] = m["marker_with_iid"][0]["post"]
    if len(posts) >= 2 and "Patrick Bandeira" in posts and "Robert Müller" in posts:
        b = posts["Patrick Bandeira"]
        r = posts["Robert Müller"]
        n = min(len(b), len(r), 160)
        lines.append("Bandeira vs Müller post-marker diffs (attr-candidate probes):")
        # lea 14 vs 17
        hits = [i for i in range(n) if b[i] == 14 and r[i] == 17]
        lines.append(f"  offs Band14/Mull17: {hits}")
        hits = [i for i in range(n) if b[i] == 16 and r[i] == 9]  # nf
        lines.append(f"  offs Band16/Mull9 (nf?): {hits}")
        hits = [i for i in range(n) if b[i] == 18 and r[i] == 12]  # conc
        lines.append(f"  offs Band18/Mull12 (conc?): {hits}")
        hits = [i for i in range(n) if b[i] == 16 and r[i] == 18]  # dec
        lines.append(f"  offs Band16/Mull18 (dec?): {hits}")
        hits = [i for i in range(n) if b[i] == 16 and r[i] == 16]  # shared det
        lines.append(f"  offs both-16: {hits[:40]}")
        # *5
        hits = [i for i in range(n) if b[i] == 70 and r[i] == 85]
        lines.append(f"  offs lea*5 70/85: {hits}")
        hits = [i for i in range(n) if b[i] == 80 and r[i] == 45]
        lines.append(f"  offs nf*5 80/45: {hits}")
        # show aligned first 96
        lines.append(f"  B[0:96]={list(b[:96])}")
        lines.append(f"  M[0:96]={list(r[:96])}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text[:12000])
    print(f"\n... wrote {OUT} ({len(text)} chars)")


if __name__ == "__main__":
    main()
