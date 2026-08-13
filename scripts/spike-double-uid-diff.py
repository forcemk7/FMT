"""Dump+align double-UID attr candidates; diff Bandeira vs Müller vs Seimen."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}
OUT = Path("tmp/fm-spike/double-uid-diff.txt")

# Interesting double-UID abs offsets from prior pass
TARGETS = {
    "Dennis Seimen": 157471994,  # attribute-looking layout (skip list-table hits)
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}


def extract_at(abs_target: int, length: int = 512) -> bytes:
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        buf = bytearray()
        need_end = abs_target + length
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
                if chunk_start < need_end and abs_base + len(block) > abs_target:
                    lo = max(0, abs_target - chunk_start)
                    hi = min(len(data), need_end - chunk_start)
                    already = len(buf)
                    want_from = abs_target + already
                    lo2 = max(lo, want_from - chunk_start)
                    if lo2 < hi:
                        buf.extend(data[lo2:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= length:
                    break
                if abs_base > need_end + 8 * 1024 * 1024:
                    break
        finally:
            reader.close()
    return bytes(buf)


def flat_attrs(p: dict) -> list[tuple[str, int]]:
    out = []
    for group, attrs in p["attributes"].items():
        for k, v in attrs.items():
            out.append((f"{group}.{k}", v))
    return out


def find_value_offsets(blob: bytes, val: int) -> list[int]:
    return [i for i, b in enumerate(blob) if b == val]


def main() -> None:
    lines: list[str] = []
    blobs: dict[str, bytes] = {}

    for name, abs_off in TARGETS.items():
        blob = extract_at(abs_off, 512)
        blobs[name] = blob
        p = PLAYERS[name]
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        lines.append(f"\n======== {name} abs={abs_off} len={len(blob)} ========")
        lines.append(f"UID match at 0: {blob[:4] == uid}, double: {blob[:8] == uid + uid}")
        # header parse guess
        # [0:8] double uid
        # then ~ variable header until role-ish 1-20 block
        lines.append(f"hex[0:128]:\n  {blob[:128].hex(' ')}")
        lines.append(f"hex[128:256]:\n  {blob[128:256].hex(' ')}")
        lines.append(f"hex[256:384]:\n  {blob[256:384].hex(' ')}")
        lines.append(f"u8[0:160]: {list(blob[:160])}")

        # locate ff ff ff ff
        ff = blob.find(b"\xff\xff\xff\xff")
        lines.append(f"first ffffffff @ {ff}")
        if ff >= 0:
            # next 16 bytes after run of ffs
            i = ff
            while i < len(blob) and blob[i] == 0xFF:
                i += 1
            lines.append(f"  after_ff @{i}: {list(blob[i : i + 24])} hex={blob[i:i+24].hex(' ')}")

        # candidate index u32 at common-ish offset 32?
        for off in (8, 12, 16, 20, 24, 28, 32, 36):
            if off + 4 <= len(blob):
                lines.append(f"  u32@{off}={struct.unpack_from('<I', blob, off)[0]}")

        # Map known attrs: where does each attr value appear?
        lines.append("attr value occurrences (1-20 raw) in blob:")
        for label, val in flat_attrs(p):
            offs = find_value_offsets(blob, val)
            # only show sparse/distinctive
            if val in (1, 3, 5, 7, 8, 9, 18) or label.endswith(
                ("determination", "leadership", "naturalFitness", "decisions", "concentration")
            ):
                lines.append(f"  {label}={val} @ {offs[:30]}")

        lines.append("attr*5 occurrences:")
        for label, val in flat_attrs(p):
            if val * 5 > 255:
                continue
            if val in (1, 3, 5, 7, 8, 9, 16, 17, 18) or label.endswith(
                ("determination", "leadership", "naturalFitness", "decisions")
            ):
                offs = find_value_offsets(blob, val * 5)
                lines.append(f"  {label}*5={val*5} @ {offs[:20]}")

    # ---- pairwise offset equality for common structure ----
    names = list(TARGETS.keys())
    b_name, m_name, s_name = "Patrick Bandeira", "Robert Müller", "Dennis Seimen"
    b, m, s = blobs[b_name], blobs[m_name], blobs[s_name]
    n = min(len(b), len(m), len(s))

    lines.append("\n\n======== pairwise same-byte offsets (first 256) ========")
    same_bm = [i for i in range(min(256, n)) if b[i] == m[i]]
    same_all = [i for i in range(min(256, n)) if b[i] == m[i] == s[i]]
    lines.append(f"Bandeira==Müller count in [0:256]: {len(same_bm)}")
    lines.append(f"all three equal count in [0:256]: {len(same_all)}")
    lines.append(f"all-three-equal offsets: {same_all}")

    # Diff map: for each offset, (b,m,s)
    lines.append("\n======== byte diff Bandeira vs Müller (where differ, first 200) ========")
    diffs = []
    for i in range(min(200, len(b), len(m))):
        if b[i] != m[i]:
            diffs.append((i, b[i], m[i]))
    for i, bv, mv in diffs:
        lines.append(f"  +{i}: Band={bv} Mull={mv} delta={mv - bv}")

    # Hypothesis: find offset where Band lea=14 and Mull lea=17 (raw)
    # and Band nf=16 Mull nf=9, Band det=16 Mull det=16 (same)
    pb, pm = PLAYERS[b_name], PLAYERS[m_name]
    lines.append("\n======== hypothesis: offset triplets matching known diffs ========")
    # det both 16
    det = 16
    lea_b, lea_m = pb["lea"], pm["lea"]  # 14, 17
    nf_b = pb["attributes"]["physical"]["naturalFitness"]  # 16
    nf_m = pm["attributes"]["physical"]["naturalFitness"]  # 9
    conc_b = pb["attributes"]["mental"]["concentration"]  # 18
    conc_m = pm["attributes"]["mental"]["concentration"]  # 12
    dec_b = pb["attributes"]["mental"]["decisions"]  # 16
    dec_m = pm["attributes"]["mental"]["decisions"]  # 18
    bal_b = pb["attributes"]["physical"]["balance"]  # 18
    bal_m = pm["attributes"]["physical"]["balance"]  # 18

    def match_pairs(pairs: list[tuple[int, int]], label: str) -> None:
        """Find offsets where Band==p0 and Mull==p1 (and optionally same for both)."""
        hits = []
        for i in range(min(len(b), len(m))):
            if all(b[i + k] == bv and m[i + k] == mv for k, (bv, mv) in enumerate(pairs) if i + k < min(len(b), len(m))):
                # verify length
                if i + len(pairs) <= min(len(b), len(m)):
                    if all(
                        b[i + k] == bv and m[i + k] == mv
                        for k, (bv, mv) in enumerate(pairs)
                    ):
                        hits.append(i)
        lines.append(f"  {label}: n={len(hits)} offs={hits[:25]}")

    match_pairs([(lea_b, lea_m)], "lea raw Band14/Mull17")
    match_pairs([(nf_b, nf_m)], "nf raw Band16/Mull9")
    match_pairs([(conc_b, conc_m)], "conc raw Band18/Mull12")
    match_pairs([(dec_b, dec_m)], "dec raw Band16/Mull18")
    match_pairs([(lea_b, lea_m), (nf_b, nf_m)], "lea then nf (adjacent)")
    match_pairs([(det, det), (lea_b, lea_m)], "det,lea adjacent")
    match_pairs([(lea_b * 5, lea_m * 5)], "lea *5 Band70/Mull85")
    match_pairs([(nf_b * 5, nf_m * 5)], "nf *5 Band80/Mull45")
    match_pairs([(conc_b * 5, conc_m * 5)], "conc *5 Band90/Mull60")
    match_pairs([(dec_b * 5, dec_m * 5)], "dec *5 Band80/Mull90")
    match_pairs([(bal_b, bal_m)], "balance raw both 18 (sanity many)")
    match_pairs([(18, 18)], "any both-18")

    # Offsets where Band==Mull==16 (shared det/etc) AND nearby lea differs
    lines.append("\n======== offsets with Band==Mull==16, scan +/-8 for lea pair ========")
    for i in range(min(len(b), len(m))):
        if b[i] == 16 and m[i] == 16:
            for d in range(-8, 9):
                j = i + d
                if 0 <= j < min(len(b), len(m)) and b[j] == lea_b and m[j] == lea_m:
                    ctx_b = list(b[max(0, i - 4) : i + 12])
                    ctx_m = list(m[max(0, i - 4) : i + 12])
                    lines.append(
                        f"  shared16@{i} lea@{j} (d={d})\n"
                        f"    B={ctx_b}\n    M={ctx_m}"
                    )

    # Same for *5: shared 80 (16*5), lea 70 vs 85
    lines.append("\n======== offsets Band==Mull==80 (*5 of 16), nearby lea*5 ========")
    for i in range(min(len(b), len(m))):
        if b[i] == 80 and m[i] == 80:
            for d in range(-12, 13):
                j = i + d
                if (
                    0 <= j < min(len(b), len(m))
                    and b[j] == lea_b * 5
                    and m[j] == lea_m * 5
                ):
                    lines.append(
                        f"  shared80@{i} lea*5@{j} d={d} "
                        f"B={list(b[max(0,i-4):i+16])} M={list(m[max(0,i-4):i+16])}"
                    )

    # Include Seimen: otb=1 should appear; find offsets where B/M differ from S in mental
    lines.append("\n======== Seimen-only distinctive in his blob vs others at same offset ========")
    # Align by structure: all start with double UID. Compare offset-by-offset for first 128
    # Look for offset where S has 1 (otb) and B/M have 11/15
    otb_s, otb_b, otb_m = 1, 11, 15
    for i in range(min(128, n)):
        if s[i] == otb_s and b[i] == otb_b and m[i] == otb_m:
            lines.append(f"  otb raw match @ {i}")
        if s[i] == otb_s * 5 and b[i] == otb_b * 5 and m[i] == otb_m * 5:
            lines.append(f"  otb *5 match @ {i}")

    # Mental vector as *5 — search as subsequence with gaps in each blob
    lines.append("\n======== search mental*5 as ordered subsequence (gap<=2) ========")

    def ordered_subseq(blob: bytes, vals: list[int], max_gap: int) -> list[list[int]]:
        """Return list of index paths for ordered matches with gaps."""
        paths = []

        def rec(vi: int, pos: int, path: list[int]) -> None:
            if vi == len(vals):
                paths.append(path[:])
                return
            if len(paths) >= 5:
                return
            lo = pos
            hi = min(len(blob), pos + max_gap + 1) if vi > 0 else len(blob)
            if vi == 0:
                # find all starts
                start = 0
                while len(paths) < 5:
                    j = blob.find(bytes([vals[0]]), start)
                    if j < 0:
                        break
                    rec(1, j + 1, [j])
                    start = j + 1
                return
            for j in range(lo, hi):
                if blob[j] == vals[vi]:
                    path.append(j)
                    rec(vi + 1, j + 1, path)
                    path.pop()
                    if len(paths) >= 5:
                        return

        rec(0, 0, [])
        return paths

    for name in (b_name, m_name, s_name):
        p = PLAYERS[name]
        mental = [
            p["attributes"]["mental"][k]
            for k in (
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
            )
        ]
        blob = blobs[name]
        for scale in (1, 5):
            vals = [v * scale for v in mental]
            for gap in (0, 1, 2):
                paths = ordered_subseq(blob, vals, gap)
                if paths:
                    lines.append(
                        f"  {name} mental x{scale} gap<={gap}: {len(paths)} "
                        f"first={paths[0]}"
                    )

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text[:14000])
    print(f"\n... wrote {OUT} ({len(text)} chars)")


if __name__ == "__main__":
    main()
