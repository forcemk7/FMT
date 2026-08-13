"""Near Seimen UID/IID: find windows that contain his distinctive attribute values."""

from __future__ import annotations

import json
import struct
from collections import Counter
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
SEIMEN = next(
    p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
    if p["uid"] == 2000175080
)
OUT = Path("tmp/fm-spike/seimen-attr-near-uid.txt")

UID = struct.pack("<I", 2000175080)
IID = struct.pack("<I", 0x0001BB6D)

# Distinctive values that together uniquely fingerprint Seimen
MUST = {
    "det": 18,
    "lea": 16,
    "flair": 8,
    "otb": 1,
    "fk": 3,
    "punch": 7,  # punching tendency
}
# Also gather full flat list for density scoring
ALL = []
for group in SEIMEN["attributes"].values():
    ALL.extend(group.values())


def stream_blocks():
    with SAVE.open("rb") as f:
        f.seek(26)
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


def score_window(win: bytes) -> dict:
    # require must-have values present
    for v in MUST.values():
        if v not in win:
            return {}
    # positions of must values
    pos = {k: [i for i, b in enumerate(win) if b == v] for k, v in MUST.items()}
    # density: how many of ALL attrs appear (count unique matches)
    present = sum(1 for v in ALL if v in win)
    return {"present": present, "total": len(ALL), "pos": pos}


def main() -> None:
    RADIUS = 1024
    lines = []
    candidates = []

    abs_base = 0
    carry = b""
    overlap = RADIUS * 2
    for block in stream_blocks():
        data = carry + block
        for label, needle in (("uid", UID), ("iid", IID)):
            start = 0
            while True:
                i = data.find(needle, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                ws = max(0, i - RADIUS)
                we = min(len(data), i + 4 + RADIUS)
                win = data[ws:we]
                origin = i - ws
                sc = score_window(win)
                if sc:
                    candidates.append(
                        {
                            "label": label,
                            "abs": abs_off,
                            "present": sc["present"],
                            "pos": {k: [p - origin for p in v] for k, v in sc["pos"].items()},
                            "hex": win[max(0, origin - 32) : origin + 96].hex(" "),
                            "blob": win,
                            "origin": origin,
                        }
                    )
                start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]

    candidates.sort(key=lambda c: -c["present"])
    lines.append(f"candidates with all MUST attrs near uid/iid: {len(candidates)}")
    lines.append(f"top present counts: {Counter(c['present'] for c in candidates).most_common(10)}")

    for c in candidates[:12]:
        lines.append(
            f"\n{c['label']}@abs={c['abs']} present={c['present']}/{len(ALL)}"
        )
        lines.append(f"  must rel offsets: {c['pos']}")
        lines.append(f"  around id: {c['hex']}")

        # Try to find a compact span covering det,lea,flair,otb,fk
        must_rels = []
        for k in ("det", "lea", "flair", "otb", "fk"):
            must_rels.extend(c["pos"][k])
        if must_rels:
            lo, hi = min(must_rels), max(must_rels)
            lines.append(f"  must-span rel=[{lo},{hi}] width={hi-lo+1}")
            if hi - lo < 200:
                origin = c["origin"]
                span = list(c["blob"][origin + lo : origin + hi + 1])
                lines.append(f"  span bytes: {span}")

    # Also try u16le encoding of mental screen order
    mental = SEIMEN["attributes"]["mental"]
    order = [
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
    u16 = b"".join(struct.pack("<H", mental[k]) for k in order)
    u16be = b"".join(struct.pack(">H", mental[k]) for k in order)
    padded = b"".join(bytes([mental[k], 0]) for k in order)
    lines.append(f"\nu16le mental pat: {u16.hex(' ')}")
    lines.append(f"u16be mental pat: {u16be.hex(' ')}")
    lines.append(f"u8_0 mental pat: {padded.hex(' ')}")

    # search these three patterns globally
    for name, pat in (("u16le", u16), ("u16be", u16be), ("u8_0", padded)):
        abs_base = 0
        carry = b""
        found = []
        for block in stream_blocks():
            data = carry + block
            start = 0
            while len(found) < 5:
                i = data.find(pat, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                ws = max(0, i - 64)
                we = min(len(data), i + len(pat) + 64)
                win = data[ws:we]
                found.append(
                    (
                        abs_off,
                        win.find(UID) - (i - ws) if UID in win else None,
                        win.find(IID) - (i - ws) if IID in win else None,
                        win.hex(" "),
                    )
                )
                start = i + 1
            abs_base += len(block)
            carry = data[-(len(pat) + 64) :]
            if len(found) >= 5:
                break
        lines.append(f"\n{name} hits={len(found)}")
        for abs_off, urel, irel, hx in found:
            lines.append(f"  abs={abs_off} uid_rel={urel} iid_rel={irel}")
            lines.append(f"    {hx[:200]}...")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
