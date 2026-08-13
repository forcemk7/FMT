#!/usr/bin/env python3
"""Person-centric favoured-club: Assan + shared club-link prefixes.

From City co-location dumps, Assan appears in records like:
  03 01 02 <AssanUid> ... 01 03 02 <City 679>
Also seen: ?? 3f 02 <clubId> (often staff/manager-ish).

Test whether BOTH favoured clubs share a person-side prefix near Assan.
"""

from __future__ import annotations

import struct
import time
from collections import Counter
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "favoured-club-assan-prefix.txt"

UID = 2000188173
SCH, CITY = 920, 679
UID_B = struct.pack("<I", UID)
SCH_B = struct.pack("<I", SCH)
CITY_B = struct.pack("<I", CITY)

# Candidate club-link prefixes observed/hypothesized
PREFIXES = {
    "01 03 02": bytes.fromhex("010302"),
    "03 01 02": bytes.fromhex("030102"),
    "3f 02": bytes.fromhex("3f02"),
    "99 3f 02": bytes.fromhex("993f02"),
    "02": bytes.fromhex("02"),  # bare typed id
}


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
    WIN = 256

    # Global: prefix+club counts
    global_counts: dict[str, Counter] = {k: Counter() for k in PREFIXES}
    # Near Assan: prefix+club within window
    near_assan: dict[str, Counter] = {k: Counter() for k in PREFIXES}
    # Windows where Assan co-occurs with BOTH prefix+Sch and prefix+City (same prefix)
    both_by_prefix: dict[str, list] = {k: [] for k in PREFIXES}

    # Also: find Assan person-rows that contain BOTH raw club ids, dump them
    both_raw: list[tuple[int, bytes, int]] = []

    abs_base = 0
    carry = b""
    overlap = WIN + 16
    t0 = time.perf_counter()
    est = max(SAVE.stat().st_size * 3, 1)
    last = -1
    uid_hits = 0

    log("scanning prefixes…")
    for block in stream_blocks(SAVE):
        data = carry + block
        search_end = len(data) - (0 if abs_base == 0 else WIN)
        start0 = max(0, len(carry) - overlap - 3) if abs_base else 0

        # Global prefix+club (only scan selective prefixes; skip bare "02" globally)
        for name, pref in PREFIXES.items():
            if name == "02":
                continue
            for club, cb in (("Sch", SCH_B), ("City", CITY_B)):
                needle = pref + cb
                start = start0
                while True:
                    j = data.find(needle, start, search_end + len(needle))
                    if j < 0 or j >= search_end:
                        break
                    global_counts[name][club] += 1
                    start = j + 1

        # Assan windows
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
            rel = j - lo

            if SCH_B in win and CITY_B in win:
                both_raw.append((abs_hit, win, rel))

            for name, pref in PREFIXES.items():
                has_s = (pref + SCH_B) in win
                has_c = (pref + CITY_B) in win
                if has_s:
                    near_assan[name]["Sch"] += 1
                if has_c:
                    near_assan[name]["City"] += 1
                if has_s and has_c:
                    both_by_prefix[name].append((abs_hit, win, rel))
            start = j + 1

        abs_base += len(block)
        carry = data[-overlap:]
        pct = int(min(99, abs_base * 100 / est))
        if pct != last and pct % 10 == 0:
            last = pct
            log(f"  … ~{pct}% uid={uid_hits} bothRaw={len(both_raw)}")

    log(f"done {time.perf_counter() - t0:.1f}s")

    lines: list[str] = []
    lines.append("# Assan favoured-club PREFIX lock")
    lines.append(f"save={SAVE.name}")
    lines.append(f"uid={UID} sch={SCH} city={CITY} uidHits={uid_hits}")
    lines.append("")
    lines.append("## Global prefix+club counts")
    for name in PREFIXES:
        if name == "02":
            continue
        lines.append(f"  [{name}] Sch={global_counts[name]['Sch']} City={global_counts[name]['City']}")

    lines.append("")
    lines.append("## Near Assan (±256): prefix+club hit windows")
    for name in PREFIXES:
        lines.append(
            f"  [{name}] Sch={near_assan[name]['Sch']} City={near_assan[name]['City']} "
            f"both={len(both_by_prefix[name])}"
        )

    lines.append("")
    lines.append(f"## Assan windows with BOTH raw clubIds: {len(both_raw)}")
    # Analyze common bytes immediately before each clubId in those windows
    before_s: Counter[bytes] = Counter()
    before_c: Counter[bytes] = Counter()
    for abs_hit, win, rel in both_raw:
        for needle, bucket in ((SCH_B, before_s), (CITY_B, before_c)):
            p = 0
            while True:
                k = win.find(needle, p)
                if k < 0:
                    break
                bucket[win[max(0, k - 3) : k]] += 1
                p = k + 1
    lines.append("3 bytes before Schalke:")
    for b, n in before_s.most_common(12):
        lines.append(f"  {b.hex(' ')}: {n}")
    lines.append("3 bytes before City:")
    for b, n in before_c.most_common(12):
        lines.append(f"  {b.hex(' ')}: {n}")

    # Dump best windows: prefer shared prefix both
    dumped = 0
    lines.append("")
    lines.append("## dumps: shared-prefix BOTH clubs")
    for name, lst in both_by_prefix.items():
        if not lst:
            continue
        lines.append(f"\n# prefix {name} ({len(lst)} windows)")
        for abs_hit, win, rel in lst[:4]:
            marks = {rel: "Assan"}
            for label, needle in (
                (f"{name}+Sch", PREFIXES[name] + SCH_B),
                (f"{name}+City", PREFIXES[name] + CITY_B),
                ("920", SCH_B),
                ("679", CITY_B),
            ):
                p = 0
                while True:
                    k = win.find(needle, p)
                    if k < 0:
                        break
                    marks.setdefault(k, label)
                    p = k + 1
            lines.append(f"\n### abs={abs_hit} prefix={name}")
            lines.extend(hexdump(win, marks))
            dumped += 1

    if dumped == 0:
        lines.append("(none) — dumping raw both-club windows")
        for abs_hit, win, rel in both_raw[:8]:
            marks = {rel: "Assan"}
            p = 0
            while True:
                k = win.find(SCH_B, p)
                if k < 0:
                    break
                marks.setdefault(k, "920")
                p = k + 1
            p = 0
            while True:
                k = win.find(CITY_B, p)
                if k < 0:
                    break
                marks.setdefault(k, "679")
                p = k + 1
            lines.append(f"\n### abs={abs_hit} raw-both")
            lines.extend(hexdump(win, marks))

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    for line in lines[:55]:
        log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
