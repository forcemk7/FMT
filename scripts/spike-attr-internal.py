"""Link person internal IDs to det/lea/0x80 attribute blocks."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

# From prior person-record dumps
INTERNAL = {
    "Dennis Seimen": 0x0001BB6D,  # 6d bb 01 00
    "Patrick Bandeira": 0x0005191C,  # 1c 19 05 00
    "Robert Müller": 0x00059603,  # 03 96 05 00
}
OUT = Path("tmp/fm-spike/attr-internal-link.txt")


def main() -> None:
    # confirm internals appear near uid for sanity
    lines = []
    needles = {}
    for p in PLAYERS:
        n = p["name"]
        iid = struct.pack("<I", INTERNAL[n])
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        det, lea = p["det"], p["lea"]
        needles[n] = {
            "iid": iid,
            "uid": uid,
            "triple": bytes([det, lea, 0x80]),
            "p": p,
        }

    # single pass: for each internal-id hit, check if triple and/or uid near
    findings = {n: [] for n in needles}
    iid_counts = {n: 0 for n in needles}

    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        R = 256
        overlap = R * 2
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                for n, info in needles.items():
                    start = 0
                    while True:
                        i = data.find(info["iid"], start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        iid_counts[n] += 1
                        ws = max(0, i - R)
                        we = min(len(data), i + 4 + R)
                        win = data[ws:we]
                        base = i - ws
                        uid_pos = win.find(info["uid"])
                        trip_pos = win.find(info["triple"])
                        # also any 1-20 run length ending at triple
                        rec = {
                            "abs": abs_off,
                            "uid_rel": (uid_pos - base) if uid_pos >= 0 else None,
                            "triple_rel": (trip_pos - base) if trip_pos >= 0 else None,
                        }
                        if trip_pos >= 0:
                            # dump context around triple
                            t = trip_pos
                            rec["triple_ctx"] = win[max(0, t - 64) : t + 32].hex(" ")
                            # attr run
                            run_start = t
                            while run_start > 0 and 1 <= win[run_start - 1] <= 20:
                                run_start -= 1
                            rec["run"] = list(win[run_start : t + 2])
                        if uid_pos >= 0 or trip_pos >= 0:
                            if len(findings[n]) < 25:
                                findings[n].append(rec)
                        start = i + 1
                abs_base += len(block)
                carry = data[-overlap:]
        finally:
            reader.close()

    for p in PLAYERS:
        n = p["name"]
        lines.append(
            f"\n======== {n} iid={INTERNAL[n]} det={p['det']} lea={p['lea']} "
            f"iid_hits={iid_counts[n]} interesting={len(findings[n])} ========"
        )
        with_both = [
            r
            for r in findings[n]
            if r["uid_rel"] is not None and r["triple_rel"] is not None
        ]
        with_trip = [r for r in findings[n] if r["triple_rel"] is not None]
        with_uid = [r for r in findings[n] if r["uid_rel"] is not None]
        lines.append(
            f"  near uid: {len(with_uid)}  near triple: {len(with_trip)}  both: {len(with_both)}"
        )
        for r in (with_both or with_trip or with_uid)[:12]:
            lines.append(
                f"  iid@abs={r['abs']} uid_rel={r['uid_rel']} triple_rel={r['triple_rel']} run={r.get('run')}"
            )
            if "triple_ctx" in r:
                lines.append(f"    ctx: {r['triple_ctx']}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
