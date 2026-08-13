"""Find det/lea/0x80 blocks that sit near each player's internal id."""

from __future__ import annotations

import json
import struct
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
OUT = Path("tmp/fm-spike/attr-iid-triple.txt")
R = 512


def main() -> None:
    lines = []
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        overlap = R * 2 + 8
        # accumulate per player
        found = {n: [] for n in INTERNAL}
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                for p in PLAYERS:
                    n = p["name"]
                    if len(found[n]) >= 15:
                        continue
                    triple = bytes([p["det"], p["lea"], 0x80])
                    iid = struct.pack("<I", INTERNAL[n])
                    uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
                    start = 0
                    while len(found[n]) < 15:
                        i = data.find(triple, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        ws = max(0, i - R)
                        we = min(len(data), i + 3 + R)
                        win = data[ws:we]
                        trip_at = i - ws
                        iid_at = win.find(iid)
                        if iid_at < 0:
                            start = i + 1
                            continue
                        uid_at = win.find(uid)
                        # attr run ending at triple
                        run_start = trip_at
                        while run_start > 0 and 1 <= win[run_start - 1] <= 20:
                            run_start -= 1
                        run = list(win[run_start : trip_at + 2])
                        ctx = win[max(0, min(iid_at, trip_at) - 16) : max(iid_at, trip_at) + 48]
                        found[n].append(
                            {
                                "triple_abs": abs_off,
                                "iid_rel": iid_at - trip_at,
                                "uid_rel": (uid_at - trip_at) if uid_at >= 0 else None,
                                "run": run,
                                "ctx": ctx.hex(" "),
                            }
                        )
                        start = i + 1
                abs_base += len(block)
                carry = data[-overlap:]
        finally:
            reader.close()

    for p in PLAYERS:
        n = p["name"]
        rows = found[n]
        lines.append(
            f"\n======== {n} det={p['det']} lea={p['lea']} iid={INTERNAL[n]} "
            f"triple+iid hits={len(rows)} ========"
        )
        from collections import Counter

        lines.append(
            f"  iid_rel hist: {Counter(r['iid_rel'] for r in rows).most_common(10)}"
        )
        lines.append(
            f"  uid_rel hist: {Counter(r['uid_rel'] for r in rows).most_common(10)}"
        )
        lines.append(
            f"  run_len hist: {Counter(len(r['run']) for r in rows).most_common(10)}"
        )
        for r in rows[:8]:
            lines.append(
                f"  triple@abs={r['triple_abs']} iid_rel={r['iid_rel']} "
                f"uid_rel={r['uid_rel']} run={r['run']}"
            )
            lines.append(f"    {r['ctx']}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
