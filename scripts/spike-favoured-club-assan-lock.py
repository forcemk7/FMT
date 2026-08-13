#!/usr/bin/env python3
"""Lock favoured-club record shape from Assan Ouedraogo ground truth.

Ground truth:
  uid=2000188173 Assan Ouedraogo @ Man City
  favoured: Schalke 04 (920), Man City (679)

Prior scan showed Assan UID co-located with Schalke, and a repeating motif:
  ... 3f 02 <clubId u32> 02 <???> 02 32 87 55 77 ...
Also person refs often tagged 7f02 <uid>.
"""

from __future__ import annotations

import struct
import time
from collections import Counter
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "favoured-club-assan-lock.txt"

UID = 2000188173
SCHALKE, CITY = 920, 679
UID_B = struct.pack("<I", UID)
SCH_B = struct.pack("<I", SCHALKE)
CITY_B = struct.pack("<I", CITY)
# trailing constant seen after Schalke favourites near Assan
TRAIL = bytes.fromhex("0232875577")  # 02 32 87 55 77


def log(s: str = "") -> None:
    print(s, flush=True)


def stream_blocks(path: Path):
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf." and head[25] == 3
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            reader.close()


def hexdump(win: bytes, marks: dict[int, str]) -> list[str]:
    lines = []
    for i in range(0, len(win), 16):
        chunk = win[i : i + 16]
        hx = " ".join(f"{b:02x}" for b in chunk)
        lines.append(f"  +{i:04x}  {hx}")
        for rel, label in sorted(marks.items()):
            if i <= rel < i + 16:
                lines.append("        " + " " * ((rel - i) * 3) + f"^^ {label}")
    return lines


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Assan favoured-club LOCK")
    lines.append(f"save={SAVE.name}")
    lines.append(f"uid={UID} schalke={SCHALKE} city={CITY}")
    lines.append("")

    # Motif A: 3f 02 <clubId>
    motif_s = b"\x3f\x02" + SCH_B
    motif_c = b"\x3f\x02" + CITY_B

    # Motif B: typed club + trail constant
    typed_s_trail = b"\x02" + SCH_B + b"\x02"  # then scan for trail nearby
    # Full: 02 club 02 ?? ?? ?? ?? 02 32 87 55 77  — mid field varies

    WIN = 384
    uid_hits = 0
    both_in_window = 0
    sch_motif_near_uid = 0
    city_motif_near_uid = 0
    both_motifs_near_uid = 0
    gold_windows: list[tuple[int, bytes, int]] = []

    # Global motif counts (club-side reverse viability if person-linked)
    global_sch_motif = 0
    global_city_motif = 0
    global_sch_with_trail = 0
    # For club-side reverse: occurrences of sch motif where Assan UID is nearby
    # For extract: all person UIDs near sch motif with trail

    # Collect person UIDs that appear near Schalke favoured motif (core UID range)
    near_sch_fav: Counter[int] = Counter()
    UID_LO, UID_HI = 2_000_000_000, 2_004_000_000

    abs_base = 0
    carry = b""
    overlap = WIN + 16
    t0 = time.perf_counter()
    est = max(SAVE.stat().st_size * 3, 1)
    last = -1

    log("scanning…")
    for block in stream_blocks(SAVE):
        data = carry + block
        search_end = len(data) - (0 if abs_base == 0 else WIN)
        start0 = max(0, len(carry) - overlap - 3) if abs_base else 0

        # --- global Schalke/City motifs ---
        start = start0
        while True:
            j = data.find(motif_s, start, search_end + 6)
            if j < 0 or j >= search_end:
                break
            global_sch_motif += 1
            # trail within +20
            chunk = data[j : min(len(data), j + 32)]
            if TRAIL in chunk:
                global_sch_with_trail += 1
            # collect nearby typed/core UIDs in ±96
            lo = max(0, j - 96)
            hi = min(len(data), j + 64)
            w = data[lo:hi]
            for i in range(0, len(w) - 3):
                if i > 0 and w[i - 1] != 0x02:
                    continue
                v = struct.unpack_from("<I", w, i)[0]
                if UID_LO <= v <= UID_HI:
                    near_sch_fav[v] += 1
            start = j + 1

        start = start0
        while True:
            j = data.find(motif_c, start, search_end + 6)
            if j < 0 or j >= search_end:
                break
            global_city_motif += 1
            start = j + 1

        # --- Assan UID windows ---
        start = start0
        while True:
            j = data.find(UID_B, start, search_end + 3)
            if j < 0 or j >= search_end:
                break
            uid_hits += 1
            abs_hit = abs_base - len(carry) + j
            lo = max(0, j - WIN)
            hi = min(len(data), j + 4 + WIN)
            win = data[lo:hi]
            has_s = SCH_B in win
            has_c = CITY_B in win
            if has_s and has_c:
                both_in_window += 1
            ms = motif_s in win
            mc = motif_c in win
            if ms:
                sch_motif_near_uid += 1
            if mc:
                city_motif_near_uid += 1
            if ms and mc:
                both_motifs_near_uid += 1
                gold_windows.append((abs_hit, win, j - lo))
            elif ms and has_c and len(gold_windows) < 20:
                # Still useful even without city motif
                gold_windows.append((abs_hit, win, j - lo))
            start = j + 1

        abs_base += len(block)
        carry = data[-overlap:]
        pct = int(min(99, abs_base * 100 / est))
        if pct != last and pct % 10 == 0:
            last = pct
            log(
                f"  … ~{pct}% uid={uid_hits} bothClubs={both_in_window} "
                f"schMotif={global_sch_motif} cityMotif={global_city_motif}"
            )

    log(f"done {time.perf_counter() - t0:.1f}s")

    lines.append("## Assan co-location")
    lines.append(f"uidHits={uid_hits}")
    lines.append(f"window has both clubIds (raw)={both_in_window}")
    lines.append(f"window has 3f02|Schalke motif={sch_motif_near_uid}")
    lines.append(f"window has 3f02|City motif={city_motif_near_uid}")
    lines.append(f"window has BOTH motifs={both_motifs_near_uid}")
    lines.append("")
    lines.append("## Global motif counts (club-side reverse potential)")
    lines.append(f"3f02|Schalke={global_sch_motif}  withTrail={global_sch_with_trail}")
    lines.append(f"3f02|ManCity={global_city_motif}")
    lines.append("")
    lines.append("## Person UIDs near 3f02|Schalke (±96, typed 02|uid, core range)")
    lines.append(f"distinct={len(near_sch_fav)}")
    # Assan should rank high
    assan_n = near_sch_fav.get(UID, 0)
    lines.append(f"Assan count={assan_n}")
    for u, n in near_sch_fav.most_common(40):
        mark = " <-- ASSAN" if u == UID else ""
        lines.append(f"  uid={u} n={n}{mark}")

    lines.append("")
    lines.append(f"## GOLD / motif windows dumped: {len(gold_windows)}")
    # Prefer windows with both motifs
    gold_windows.sort(key=lambda t: -int(motif_s in t[1] and motif_c in t[1]))
    for abs_hit, win, rel_uid in gold_windows[:10]:
        marks = {rel_uid: "Assan"}
        for needle, label in (
            (motif_s, "motif Schalke"),
            (motif_c, "motif City"),
            (SCH_B, "920"),
            (CITY_B, "679"),
            (TRAIL, "trail 32875577"),
        ):
            p = 0
            while True:
                k = win.find(needle, p)
                if k < 0:
                    break
                marks.setdefault(k, label)
                p = k + 1
        lines.append(f"\n### abs={abs_hit}")
        lines.extend(hexdump(win, marks))

    # Analyze bytes between Assan and Schalke motif in gold windows
    lines.append("")
    lines.append("## relative motif positions in dumped windows")
    for abs_hit, win, rel_uid in gold_windows[:15]:
        ms = win.find(motif_s)
        mc = win.find(motif_c)
        lines.append(
            f"  abs={abs_hit} uid@{rel_uid} schMotif@{ms} "
            f"(d={ms - rel_uid if ms >= 0 else None}) "
            f"cityMotif@{mc} (d={mc - rel_uid if mc >= 0 else None})"
        )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    for line in lines[:50]:
        log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
