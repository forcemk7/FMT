#!/usr/bin/env python3
"""Spike: locate stored CA/PA (i16) near person doubles — ONE decompress.

Community: CA/PA are 16-bit signed ints (effective 1–200; PA may be negative
range codes -1..-10 in editor DBs, usually resolved in career saves).

Collects lookback/lookforward windows for a small anchor set in one zstd pass,
then ranks (kind, relative_offset) layouts by cross-player coverage + Haaland-high.
"""

from __future__ import annotations

import json
import struct
import time
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
OUT = ROOT / "tmp" / "fm-spike" / "capa-person-spike.txt"
EXTRACT = ROOT / "tmp" / "fm-spike" / "extract-ft-verify.json"

# Prefer high-CA veterans + Assan + Haaland for relative validation
SEED_UIDS = [
    ("Assan Ouédraogo", 2000188173),
    ("Erling Haaland", 43159044),  # may be wrong — will also try fixture if present
    ("Dennis Seimen", 2000175080),
    ("Robert Müller", 2002266341),
    ("Paco Suárez", 2000136577),
]

WIN_BEFORE = 128
WIN_AFTER = 96
MAX_DOUBLES = 4


def log(s: str = "") -> None:
    print(s, flush=True)


def plausible_ca(v: int) -> bool:
    return 1 <= v <= 200


def plausible_pa(v: int) -> bool:
    return plausible_ca(v) or (-10 <= v <= -1)


def stream_concat(path: Path):
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
            try:
                reader.close()
            except zstd.ZstdError:
                pass


def collect_windows(uids: dict[int, str]) -> dict[int, list[bytes]]:
    """uid -> list of windows around double-UID sites (first UID at WIN_BEFORE)."""
    needles = {uid: struct.pack("<I", uid) for uid in uids}
    found: dict[int, list[bytes]] = {uid: [] for uid in uids}
    need = {uid: MAX_DOUBLES for uid in uids}
    abs_base = 0
    carry = b""
    overlap = WIN_BEFORE + WIN_AFTER + 128

    for block in stream_concat(SAVE):
        data = carry + block
        # scan each unfinished uid
        for uid, nb in needles.items():
            if need[uid] <= 0:
                continue
            start = 0
            while need[uid] > 0:
                j = data.find(nb, start)
                if j < 0:
                    break
                # second copy within +4..+48
                k = data.find(nb, j + 4, min(len(data), j + 48))
                if k > 0:
                    lo = j - WIN_BEFORE
                    hi = k + WIN_AFTER
                    if lo >= 0 and hi <= len(data):
                        found[uid].append(data[lo:hi])
                        need[uid] -= 1
                start = j + 1
        abs_base += len(block)
        carry = data[-overlap:]
        if all(n <= 0 for n in need.values()):
            break
        if abs_base and abs_base % (64 * 1024 * 1024) < 8 * 1024 * 1024:
            left = sum(1 for n in need.values() if n > 0)
            log(f"  …{abs_base // (1024 * 1024)} MiB scanned, {left} uids still open")
    return found


def candidates_in_window(win: bytes) -> list[tuple[str, int, int, int]]:
    """Relative offset is vs first UID at WIN_BEFORE."""
    rel0 = WIN_BEFORE
    out: list[tuple[str, int, int, int]] = []
    # i16le pairs adjacent / +2 gap
    for i in range(0, len(win) - 3):
        ca = struct.unpack_from("<h", win, i)[0]
        pa0 = struct.unpack_from("<h", win, i + 2)[0]
        if plausible_ca(ca) and plausible_pa(pa0):
            if pa0 < 0 or ca <= pa0:
                out.append(("i16+0", i - rel0, ca, pa0))
        if i + 5 < len(win):
            pa2 = struct.unpack_from("<h", win, i + 4)[0]
            if plausible_ca(ca) and plausible_pa(pa2) and (pa2 < 0 or ca <= pa2):
                out.append(("i16+2gap", i - rel0, ca, pa2))
        # also bare u8 pair (older editors sometimes)
        b0, b1 = win[i], win[i + 1]
        if 1 <= b0 <= b1 <= 200:
            out.append(("u8+0", i - rel0, b0, b1))
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    anchors: list[tuple[str, int]] = []
    if EXTRACT.exists():
        d = json.loads(EXTRACT.read_text(encoding="utf-8-sig"))
        # pick mix: first 6 + last 4 (often different ability bands)
        players = d.get("players") or []
        for p in players[:6] + players[-4:]:
            if p.get("uid"):
                anchors.append((p.get("name") or "?", int(p["uid"])))
    for name, uid in SEED_UIDS:
        anchors.append((name, uid))

    # dedupe
    seen: set[int] = set()
    uniq: list[tuple[str, int]] = []
    for name, uid in anchors:
        if uid in seen:
            continue
        seen.add(uid)
        uniq.append((name, uid))
    anchors = uniq[:14]
    uid_names = {u: n for n, u in anchors}

    log(f"one-pass CAPA spike · {len(anchors)} anchors · {SAVE.name}")
    t0 = time.perf_counter()
    windows = collect_windows(uid_names)
    log(f"collect done in {time.perf_counter() - t0:.1f}s")

    lines: list[str] = [
        "# CA/PA person-double spike (one pass)",
        f"save={SAVE.name}",
        f"anchors={len(anchors)}",
        "",
    ]

    offset_players: dict[tuple[str, int], set[int]] = defaultdict(set)
    offset_vals: dict[tuple[str, int], dict[int, tuple[int, int]]] = defaultdict(dict)
    per_player_modal: dict[int, list[tuple[str, int, int, int]]] = {}

    for name, uid in anchors:
        wins = windows.get(uid) or []
        lines.append(f"## {name} uid={uid} doubles={len(wins)}")
        if not wins:
            lines.append("  (no doubles)")
            continue
        # count (kind, off, ca, pa) across doubles
        ctr: Counter[tuple[str, int, int, int]] = Counter()
        for win in wins:
            for kind, off, ca, pa in candidates_in_window(win):
                if -96 <= off <= 80:
                    ctr[(kind, off, ca, pa)] += 1
        # modal (ca,pa) per (kind,off)
        by_off: dict[tuple[str, int], Counter[tuple[int, int]]] = defaultdict(Counter)
        for (kind, off, ca, pa), n in ctr.items():
            by_off[(kind, off)][(ca, pa)] += n
        picks: list[tuple[str, int, int, int]] = []
        for (kind, off), c2 in by_off.items():
            (ca, pa), n = c2.most_common(1)[0]
            picks.append((kind, off, ca, pa))
            offset_players[(kind, off)].add(uid)
            offset_vals[(kind, off)][uid] = (ca, pa)
        per_player_modal[uid] = picks
        for (kind, off, ca, pa), n in sorted(ctr.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {kind} off={off:+d} ca={ca} pa={pa} hits={n}/{len(wins)}")
        lines.append("")

    lines.append("## ranked shared offsets")
    ranked = sorted(offset_players.items(), key=lambda kv: -len(kv[1]))
    for (kind, off), uids in ranked[:30]:
        vals = [offset_vals[(kind, off)][u] for u in uids]
        cas = [c for c, _ in vals]
        pas = [p for _, p in vals]
        spread = (max(cas) - min(cas)) if cas else 0
        # Haaland if present
        h = offset_vals[(kind, off)].get(43159044) or offset_vals[(kind, off)].get(
            2000014163
        )
        score = len(uids) * 3 + min(50, spread)
        if h and h[0] >= 150:
            score += 25
        if h and (h[1] >= 170 or h[1] < 0):
            score += 10
        # diversity: unique CA values help
        score += min(20, len(set(cas)) * 2)
        sample = ", ".join(
            f"{uid_names[u].split()[-1]}={offset_vals[(kind, off)][u]}"
            for u in list(uids)[:5]
        )
        lines.append(
            f"  score={score} {kind} off={off:+d} n={len(uids)} "
            f"ca=[{min(cas)}..{max(cas)}] pa=[{min(pas)}..{max(pas)}] "
            f"haaland={h} | {sample}"
        )

    # Also dump bytes 22–43 of a known CA card if extract has history — skipped here.
    lines.append(f"\nelapsed={time.perf_counter() - t0:.1f}s")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {OUT}")
    # print summary tail
    for line in lines:
        if line.startswith("  score=") or line.startswith("#") or line.startswith("save"):
            log(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
