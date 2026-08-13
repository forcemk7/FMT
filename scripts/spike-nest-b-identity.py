"""Single-pass nest_b / sheet column / personIndex bridge analysis.

Important: Seimen+Müller both Germany but nest_b 78 vs 162 → NOT nation.
"""

from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/nest-b-identity.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}

ROWS = {
    "Patrick Bandeira": 206618,
    "Robert Müller": 209313,
    "Dennis Seimen": 252202,
}
NEST_B = {
    "Patrick Bandeira": 189,
    "Robert Müller": 162,
    "Dennis Seimen": 78,
}
UID = {n: PLAYERS[n]["uid"] for n in ROWS}
IDX = {"Patrick Bandeira": 1198, "Robert Müller": 1233, "Dennis Seimen": 1790}

TABLE_BASE = 114372
STRIDE = 77
SHEET_N = 3000
SHEET_HI = TABLE_BASE + STRIDE * SHEET_N


def ascii_window(buf: bytes, center: int, rad: int = 48) -> str:
    lo = max(0, center - rad)
    hi = min(len(buf), center + rad)
    return "".join(chr(b) if 32 <= b < 127 else "." for b in buf[lo:hi])


def main() -> None:
    lines: list[str] = []
    lines.append("## Fixture vs nest_b (NOT nation — Seimen&Müller both Germany)")
    for name, nb in NEST_B.items():
        p = PLAYERS[name]
        lines.append(
            f"  {name}: nest_b={nb} nation={p.get('nation')} nation2={p.get('nation2')} club={p.get('club')}"
        )

    # Needles
    nest_pats = {n: struct.pack("<I", v) for n, v in NEST_B.items()}
    uid_pats = {n: struct.pack("<I", v) for n, v in UID.items()}
    idx_pats = {n: struct.pack("<I", v) for n, v in IDX.items()}
    nation_needles = {
        "Germany": b"Germany",
        "Portugal": b"Portugal",
        "Romania": b"Romania",
    }

    nest_b_c: Counter[int] = Counter()
    nest_a_c: Counter[int] = Counter()
    u23_c: Counter[int] = Counter()
    sheet_buf = bytearray()

    nest_primary: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    nation_hits: dict[str, list[int]] = defaultdict(list)
    nation_nest_near: list[str] = []
    bridges: dict[str, list[tuple[int, int]]] = defaultdict(list)
    uid_hit_count: Counter[str] = Counter()

    # Rolling window for co-location (512 bytes)
    WIN = 512
    carry = b""
    abs_base = 0

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

                # --- sheet sample capture ---
                if chunk_start < SHEET_HI and abs_base + len(block) > TABLE_BASE:
                    lo = max(0, TABLE_BASE - chunk_start)
                    hi = min(len(data), SHEET_HI - chunk_start)
                    # append only new bytes beyond what we have
                    already = len(sheet_buf)
                    want = TABLE_BASE + already
                    lo2 = max(lo, want - chunk_start)
                    if lo2 < hi:
                        sheet_buf.extend(data[lo2:hi])

                # scan inside `data` but skip overlap already scanned in previous carry
                scan_from = len(carry) if carry else 0
                # actually search full data then filter abs; use carry overlap carefully
                # For needles, search only in block region with overlap of 64 for multi-byte
                search = data
                search_base = chunk_start

                # nation strings
                for label, needle in nation_needles.items():
                    if len(nation_hits[label]) >= 12:
                        continue
                    start = 0
                    while len(nation_hits[label]) < 12:
                        j = search.find(needle, start)
                        if j < 0:
                            break
                        abs_hit = search_base + j
                        # skip duplicate from carry overlap: only accept if in new block region
                        if abs_hit >= abs_base:
                            nation_hits[label].append(abs_hit)
                            # check nest_b nearby in local window
                            lo = max(0, j - 64)
                            hi = min(len(search), j + len(needle) + 64)
                            win = search[lo:hi]
                            found = []
                            for n, pat in nest_pats.items():
                                k = win.find(pat)
                                if k >= 0:
                                    found.append(f"{n}:{NEST_B[n]}@rel{k-(j-lo)}")
                            if found:
                                nation_nest_near.append(
                                    f"  {label}@{abs_hit} nest_b: {found} ascii={ascii_window(search, j, 40)}"
                                )
                        start = j + 1

                # nest_b primary outside sheet (cap per player)
                for name, pat in nest_pats.items():
                    if len(nest_primary[name]) >= 15:
                        continue
                    start = 0
                    while len(nest_primary[name]) < 15:
                        j = search.find(pat, start)
                        if j < 0:
                            break
                        abs_hit = search_base + j
                        if abs_hit >= abs_base and not (
                            TABLE_BASE <= abs_hit < SHEET_HI
                        ):
                            after = search[j : j + 48]
                            kind = "other"
                            if after[0:4] == after[4:8] == pat:
                                kind = "dup_at_hit"  # shouldn't happen; hit is first
                            if len(after) >= 8 and after[4:8] == pat:
                                kind = "dup_pair"
                            if b"\x01\x00\x6c\x07" in after or b"\xb6\x00\xe1\x07" in after:
                                kind = "near_type"
                            printable = sum(32 <= b < 127 for b in after[4:36])
                            if printable >= 12:
                                kind = "near_ascii"
                            nest_primary[name].append(
                                (abs_hit, kind, after[:40].hex(" "), ascii_window(search, j, 48))
                            )
                        start = j + 1

                # UID hits + personIndex bridge via local window
                for name, upat in uid_pats.items():
                    start = 0
                    while True:
                        j = search.find(upat, start)
                        if j < 0:
                            break
                        abs_uid = search_base + j
                        if abs_uid >= abs_base:
                            uid_hit_count[name] += 1
                            if uid_hit_count[name] <= 120:
                                lo = max(0, j - WIN)
                                hi = min(len(search), j + 4 + WIN)
                                win = search[lo:hi]
                                ipat = idx_pats[name]
                                k = 0
                                while True:
                                    kk = win.find(ipat, k)
                                    if kk < 0:
                                        break
                                    rel = (lo + kk) - j
                                    bridges[name].append((abs_uid, rel))
                                    k = kk + 1
                        start = j + 1

                abs_base += len(block)
                carry = data[-(WIN + 8) :]
        finally:
            reader.close()

    # decode sheet distributions
    n_rows = len(sheet_buf) // STRIDE
    for i in range(n_rows):
        row = sheet_buf[i * STRIDE : (i + 1) * STRIDE]
        nest_a_c[struct.unpack_from("<I", row, 40)[0]] += 1
        nest_b_c[struct.unpack_from("<I", row, 44)[0]] += 1
        u23_c[struct.unpack_from("<I", row, 23)[0]] += 1

    lines.append(f"\n======== sheet sample n={n_rows} ========")
    lines.append(f"nest_a top: {nest_a_c.most_common(12)}")
    lines.append(f"nest_b unique={len(nest_b_c)} top20: {nest_b_c.most_common(20)}")
    lines.append(f"+23 unique={len(u23_c)} top12: {u23_c.most_common(12)}")
    for name, nb in NEST_B.items():
        lines.append(f"  nest_b={nb} ({name}) count={nest_b_c.get(nb, 0)}")

    lines.append("\n======== nation string × nest_b proximity ========")
    for label, hits in nation_hits.items():
        lines.append(f"  '{label}' hits={len(hits)} first={hits[:4]}")
    if nation_nest_near:
        lines.extend(nation_nest_near)
    else:
        lines.append("  (no nest_b within ±64 of nation ASCII — likely not those string tables)")

    lines.append("\n======== nest_b hits outside sheet (first 15) ========")
    for name in NEST_B:
        rows = nest_primary[name]
        kinds = Counter(k for _, k, _, _ in rows)
        lines.append(f"\n{name} nest_b={NEST_B[name]} kinds={dict(kinds)}")
        for abs_hit, kind, hx, asc in rows[:8]:
            lines.append(f"  @{abs_hit} [{kind}] {hx}")
            if kind in ("near_ascii", "dup_pair"):
                lines.append(f"    ascii~ {asc}")

    lines.append("\n======== personIndex near UniqueID (±512) ========")
    for name in ROWS:
        bs = bridges[name]
        # collapse duplicate abs
        uniq = []
        seen = set()
        for a, r in bs:
            key = (a, r)
            if key in seen:
                continue
            seen.add(key)
            uniq.append((a, r))
        lines.append(
            f"{name}: uid_hits={uid_hit_count[name]} bridge_pairs={len(uniq)}"
        )
        for a, r in uniq[:12]:
            lines.append(f"  uid@{a} idx_rel={r:+d}")

    lines.append("\n======== trailing +52.. as u16le ========")
    for name, abs_row in ROWS.items():
        # sheet already in sheet_buf if in range
        off = abs_row - TABLE_BASE
        row = bytes(sheet_buf[off : off + 77])
        u16s = [struct.unpack_from("<H", row, o)[0] for o in range(52, 76, 2)]
        lines.append(f"{name}: {u16s}")

    lines.append(
        """
======== CONCLUSIONS ========
- nest_b is NOT nationality (Germany→78 and 162).
- nest_b is low-cardinality (~tens of values across thousands of sheet rows).
- nest_b near_type hits are other sheet-nested payloads sharing the same code.
- poolId remains sheet-local; sheet↔double-UID bridge so far is personIndex only.
- Next: name-record trail (nation/foot/DOB) OR find a table containing UniqueID+personIndex
  outside the double-UID blob (bridge_pairs above).
"""
    )

    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
