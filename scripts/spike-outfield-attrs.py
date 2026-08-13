"""Comparative outfield attr fingerprint hunt for Bandeira + Müller."""

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
OUT = Path("tmp/fm-spike/outfield-attr-map.txt")

MENTAL_ORDER = [
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
PHYS_ORDER = [
    "acceleration",
    "agility",
    "balance",
    "jumpingReach",
    "naturalFitness",
    "pace",
    "stamina",
    "strength",
]
TECH_ORDER = [
    "crossing",
    "dribbling",
    "finishing",
    "firstTouch",
    "heading",
    "longShots",
    "marking",
    "passing",
    "tackling",
    "technique",
]
SET_ORDER = ["corners", "freeKickTaking", "longThrows", "penaltyTaking"]


def packed(p: dict, keys: list[str], group: str) -> bytes:
    return bytes([p["attributes"][group][k] for k in keys])


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


def find_pat(pat: bytes, limit: int = 15):
    abs_base = 0
    carry = b""
    overlap = max(256, len(pat) + 64)
    hits = []
    for block in stream_blocks():
        data = carry + block
        start = 0
        while len(hits) < limit:
            i = data.find(pat, start)
            if i < 0:
                break
            abs_off = abs_base - len(carry) + i
            if hits and hits[-1][0] == abs_off:
                start = i + 1
                continue
            ws = max(0, i - 96)
            we = min(len(data), i + len(pat) + 128)
            hits.append((abs_off, data[ws:we], i - ws, len(pat)))
            start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]
        if len(hits) >= limit:
            break
    return hits


def main() -> None:
    lines = []
    targets = [PLAYERS["Patrick Bandeira"], PLAYERS["Robert Müller"]]

    patterns: dict[str, tuple[dict, bytes]] = {}
    for p in targets:
        for label, group, order in (
            ("mental", "mental", MENTAL_ORDER),
            ("phys", "physical", PHYS_ORDER),
            ("tech", "technical", TECH_ORDER),
            ("set", "setPieces", SET_ORDER),
        ):
            pat = packed(p, order, group)
            patterns[f"{p['name']}|{label}|screen"] = (p, pat)
            patterns[f"{p['name']}|{label}|rev"] = (p, bytes(reversed(pat)))
            # distinctive short mental tails
        m = p["attributes"]["mental"]
        patterns[f"{p['name']}|mentail"] = (
            p,
            bytes(
                [
                    m["determination"],
                    m["flair"],
                    m["leadership"],
                    m["offTheBall"],
                    m["positioning"],
                    m["teamwork"],
                    m["vision"],
                    m["workRate"],
                ]
            ),
        )
        patterns[f"{p['name']}|det_lea"] = (
            p,
            bytes([m["determination"], m["leadership"]]),
        )
        # unique-ish physical pack
        ph = p["attributes"]["physical"]
        patterns[f"{p['name']}|phys8"] = (p, packed(p, PHYS_ORDER, "physical"))

    lines.append("patterns:")
    for k, (p, pat) in patterns.items():
        lines.append(f"  {k}: {list(pat)}  {pat.hex(' ')}")

    # Search important ones first (full packs)
    important = [k for k in patterns if k.endswith("|screen") or k.endswith("|phys8") or k.endswith("|mentail")]
    for key in important:
        p, pat = patterns[key]
        hits = find_pat(pat, limit=10)
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        lines.append(f"\n### {key} hits={len(hits)}")
        for abs_off, win, rel, plen in hits[:6]:
            uid_rel = win.find(uid) - rel if uid in win else None
            lines.append(f"  abs={abs_off} uid_rel={uid_rel}")
            lines.append(f"    before: {win[max(0,rel-48):rel].hex(' ')}")
            lines.append(f"    match:  {win[rel:rel+plen].hex(' ')}")
            lines.append(f"    after:  {win[rel+plen:rel+plen+64].hex(' ')}")
            # if full mental found, check phys/tech nearby
            if "|mental|screen" in key and hits:
                phys = packed(p, PHYS_ORDER, "physical")
                tech = packed(p, TECH_ORDER, "technical")
                lines.append(f"    phys nearby rel={win.find(phys)-rel if phys in win else None}")
                lines.append(f"    tech nearby rel={win.find(tech)-rel if tech in win else None}")

    # Compare: find windows near each UID that contain that player's mental values as multiset
    lines.append("\n\n==== near-UID multiset cover (mental+phys) ====")
    from collections import Counter

    for p in targets:
        uid = struct.pack("<I", p["uid"] & 0xFFFFFFFF)
        needed = list(p["attributes"]["mental"].values()) + list(
            p["attributes"]["physical"].values()
        )
        need = Counter(needed)
        abs_base = 0
        carry = b""
        found = []
        for block in stream_blocks():
            data = carry + block
            start = 0
            while len(found) < 8:
                i = data.find(uid, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                for radius in (128, 256, 512):
                    ws = max(0, i - 32)
                    we = min(len(data), i + 4 + radius)
                    win = data[ws:we]
                    have = Counter(win)
                    if all(have[v] >= c for v, c in need.items()):
                        found.append((abs_off, radius, len(win)))
                        break
                start = i + 1
            abs_base += len(block)
            carry = data[-600:]
            if len(found) >= 8:
                break
        lines.append(f"{p['name']}: covering uid-windows={found}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
