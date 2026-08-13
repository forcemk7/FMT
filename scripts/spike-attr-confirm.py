"""Single-pass confirm Det/Lead encodings adjacent to Unique IDs."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/attr-confirm.txt")


def main() -> None:
    patterns: dict[str, bytes] = {}
    for p in PLAYERS:
        det, lea = p["det"], p["lea"]
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        n = p["name"]
        patterns.update(
            {
                f"{n}|det_lea_02_uid": bytes([det, lea, 0x02]) + uid,
                f"{n}|det_00_lea_7f_02_uid": bytes([det, 0, lea, 0x7F, 0x02]) + uid,
                f"{n}|lea_00_det_7f_02_uid": bytes([lea, 0, det, 0x7F, 0x02]) + uid,
                f"{n}|02_uid_det_lea": b"\x02" + uid + bytes([det, lea]),
                f"{n}|02_uid_det_lea_80": b"\x02" + uid + bytes([det, lea, 0x80]),
                f"{n}|uid_det_lea": uid + bytes([det, lea]),
                f"{n}|uid_00_det_lea": uid + b"\x00" + bytes([det, lea]),
                f"{n}|det_lea_80_near": bytes([det, lea, 0x80]),
                f"{n}|xx_det_lea_80_02_uid": bytes([det, lea, 0x80, 0x02]) + uid,
                f"{n}|pre_det_lea": bytes([det, lea]),  # too broad; still count near uid later
            }
        )

    hits = {k: [] for k in patterns}
    geom = {p["name"]: {} for p in PLAYERS}
    uid_of = {p["name"]: struct.pack("<I", p["uid"] & 0xFFFFFFFF) for p in PLAYERS}
    detlea = {p["name"]: (p["det"], p["lea"]) for p in PLAYERS}

    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        overlap = 64
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                for name, pat in patterns.items():
                    if len(hits[name]) >= 10:
                        continue
                    # skip ultra-broad alone
                    if name.endswith("|pre_det_lea"):
                        continue
                    start = 0
                    while len(hits[name]) < 10:
                        i = data.find(pat, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        if hits[name] and hits[name][-1] == abs_off:
                            start = i + 1
                            continue
                        ctx = data[max(0, i - 8) : i + len(pat) + 20]
                        hits[name].append((abs_off, ctx.hex(" ")))
                        start = i + 1

                # loose geometry around each uid
                for pname, uid in uid_of.items():
                    det, lea = detlea[pname]
                    start = 0
                    while True:
                        i = data.find(uid, start)
                        if i < 0:
                            break
                        for rel in range(-24, 25):
                            at = i + rel
                            if 0 <= at < len(data) and data[at] == det:
                                for g in (1, 2, 3, 4, 5):
                                    if at + g < len(data) and data[at + g] == lea:
                                        key = f"det@{rel}/+{g}"
                                        geom[pname][key] = geom[pname].get(key, 0) + 1
                        start = i + 1

                abs_base += len(block)
                carry = data[-overlap:]
        finally:
            reader.close()

    lines = []
    for p in PLAYERS:
        n = p["name"]
        lines.append(f"\n======== {n} det={p['det']} lea={p['lea']} ========")
        for key in sorted(hits):
            if not key.startswith(n + "|"):
                continue
            rows = hits[key]
            if not rows:
                continue
            lines.append(f"  {key.split('|',1)[1]}: {len(rows)}")
            for off, ctx in rows[:4]:
                lines.append(f"    @{off}  {ctx}")
        lines.append("  loose geom +/-24:")
        for k, c in sorted(geom[n].items(), key=lambda kv: -kv[1])[:15]:
            lines.append(f"    n={c}  {k}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
