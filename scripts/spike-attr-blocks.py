"""Expand around det/lea/0x80 triples; check UID proximity and attr runs."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/attr-blocks.txt")


def main() -> None:
    # one pass, track each player's det/lea/80 occurrences with wide context
    needles = {
        p["name"]: (
            bytes([p["det"], p["lea"], 0x80]),
            struct.pack("<I", p["uid"] & 0xFFFFFFFF),
            p,
        )
        for p in PLAYERS
    }
    results = {n: [] for n in needles}

    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        overlap = 512
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                for name, (pat, uid, _p) in needles.items():
                    if len(results[name]) >= 20:
                        continue
                    start = 0
                    while len(results[name]) < 20:
                        i = data.find(pat, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        if results[name] and results[name][-1]["abs"] == abs_off:
                            start = i + 1
                            continue
                        ws = max(0, i - 128)
                        we = min(len(data), i + 64)
                        win = data[ws:we]
                        uid_at = win.find(uid)
                        # longest 1..20 run ending at det (rel to win)
                        det_at = i - ws
                        run_start = det_at
                        while run_start > 0 and 1 <= win[run_start - 1] <= 20:
                            run_start -= 1
                        run = list(win[run_start : det_at + 2])  # include det,lea
                        results[name].append(
                            {
                                "abs": abs_off,
                                "uid_rel": (uid_at - det_at) if uid_at >= 0 else None,
                                "run_len": len(run),
                                "run": run,
                                "before": win[max(0, det_at - 48) : det_at].hex(" "),
                                "after": win[det_at : det_at + 32].hex(" "),
                            }
                        )
                        start = i + 1
                abs_base += len(block)
                carry = data[-overlap:]
        finally:
            reader.close()

    lines = []
    for p in PLAYERS:
        name = p["name"]
        rows = results[name]
        with_uid = [r for r in rows if r["uid_rel"] is not None]
        lines.append(
            f"\n======== {name} det={p['det']} lea={p['lea']} "
            f"hits={len(rows)} with_uid_in_+/-128={len(with_uid)} ========"
        )
        # prefer rows with uid, else longest runs
        shown = with_uid[:8] or sorted(rows, key=lambda r: -r["run_len"])[:8]
        for r in shown:
            lines.append(
                f"  abs={r['abs']} uid_rel_to_det={r['uid_rel']} run_len={r['run_len']} run={r['run']}"
            )
            lines.append(f"    before: {r['before']}")
            lines.append(f"    after:  {r['after']}")

        # consensus: run lengths and whether uid offset clusters
        from collections import Counter

        lines.append(
            f"  run_len hist: {Counter(r['run_len'] for r in rows).most_common(8)}"
        )
        lines.append(
            f"  uid_rel hist: {Counter(r['uid_rel'] for r in with_uid).most_common(8)}"
        )

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
