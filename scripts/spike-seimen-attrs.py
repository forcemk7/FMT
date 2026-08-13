"""Fingerprint Dennis Seimen attribute runs in the save; map block layout."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
SEIMEN = next(p for p in FIXTURE if p["uid"] == 2000175080)
OUT = Path("tmp/fm-spike")
OUT.mkdir(parents=True, exist_ok=True)

UID = struct.pack("<I", SEIMEN["uid"] & 0xFFFFFFFF)
IID = struct.pack("<I", 0x0001BB6D)  # from earlier person-record dumps

# In-game column order from the screenshot
MENTAL = bytes(
    [
        SEIMEN["attributes"]["mental"][k]
        for k in (
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
        )
    ]
)
GK = bytes(
    [
        SEIMEN["attributes"]["goalkeeping"][k]
        for k in (
            "aerialReach",
            "commandOfArea",
            "communication",
            "eccentricity",
            "firstTouch",
            "handling",
            "kicking",
            "oneOnOnes",
            "passing",
            "punchingTendency",
            "reflexes",
            "rushingOutTendency",
            "throwing",
        )
    ]
)
PHYS = bytes(
    [
        SEIMEN["attributes"]["physical"][k]
        for k in (
            "acceleration",
            "agility",
            "balance",
            "jumpingReach",
            "naturalFitness",
            "pace",
            "stamina",
            "strength",
        )
    ]
)
TECH = bytes(
    [
        SEIMEN["attributes"]["technical"][k]
        for k in ("freeKickTaking", "penaltyTaking", "technique")
    ]
)

# Strong short fingerprints
SHORT = {
    "mental_full": MENTAL,  # 14 bytes — extremely unique
    "gk_full": GK,
    "phys_full": PHYS,
    "tech_full": TECH,
    "otb_flair_det_lea": bytes([1, 8, 18, 16]),  # wrong order maybe
    "flair_det_lea_otb": bytes([8, 18, 16, 1]),  # screenshot mental order
    "det_lea_otb": bytes([18, 16, 1]),
    "fk_pen_tech": TECH,  # 3,11,11
    "otb_pos_tw_vis_wr": bytes([1, 14, 10, 15, 12]),
}


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


def find_all(patterns: dict[str, bytes], limit: int = 20):
    overlap = max(len(p) for p in patterns.values()) + 256
    carry = b""
    abs_base = 0
    hits = {k: [] for k in patterns}
    for block in stream_blocks():
        data = carry + block
        for name, pat in patterns.items():
            if len(hits[name]) >= limit:
                continue
            start = 0
            while len(hits[name]) < limit:
                i = data.find(pat, start)
                if i < 0:
                    break
                abs_off = abs_base - len(carry) + i
                if hits[name] and hits[name][-1]["abs"] == abs_off:
                    start = i + 1
                    continue
                ws = max(0, i - 128)
                we = min(len(data), i + len(pat) + 128)
                win = data[ws:we]
                rel = i - ws
                hits[name].append(
                    {
                        "abs": abs_off,
                        "uid_rel": _rel(win, UID, rel),
                        "iid_rel": _rel(win, IID, rel),
                        "before": win[max(0, rel - 64) : rel].hex(" "),
                        "match": win[rel : rel + len(pat)].hex(" "),
                        "after": win[rel + len(pat) : rel + len(pat) + 64].hex(" "),
                        "window": win,
                        "rel": rel,
                        "pat_len": len(pat),
                    }
                )
                start = i + 1
        abs_base += len(block)
        carry = data[-overlap:]
        if all(len(hits[k]) >= limit for k in hits):
            break
    return hits


def _rel(win: bytes, needle: bytes, origin: int):
    j = win.find(needle)
    if j < 0:
        return None
    return j - origin


def try_orders(label: str, values: list[int]) -> dict[str, bytes]:
    """Generate a few plausible storage orders."""
    out = {f"{label}|screen": bytes(values)}
    out[f"{label}|rev"] = bytes(reversed(values))
    return out


def main() -> None:
    print("mental fingerprint:", list(MENTAL), MENTAL.hex(" "))
    print("gk fingerprint:", list(GK), GK.hex(" "))
    print("phys fingerprint:", list(PHYS), PHYS.hex(" "))
    print("tech fingerprint:", list(TECH), TECH.hex(" "))

    patterns = dict(SHORT)
    # Also search mental with 0x80 after lea (prior hypothesis)
    patterns["mental_plus_80"] = MENTAL + b"\x80"
    patterns["flair_det_lea_otb_80"] = bytes([8, 18, 16, 1, 0x80])
    patterns["det_lea_80"] = bytes([18, 16, 0x80])

    hits = find_all(patterns, limit=15)

    lines = []
    for name in sorted(hits):
        rows = hits[name]
        lines.append(f"\n### {name}  hits={len(rows)}")
        if not rows:
            continue
        with_id = [r for r in rows if r["uid_rel"] is not None or r["iid_rel"] is not None]
        lines.append(f"  with uid/iid in +/-128: {len(with_id)}")
        for r in (with_id or rows)[:8]:
            lines.append(
                f"  abs={r['abs']} uid_rel={r['uid_rel']} iid_rel={r['iid_rel']}"
            )
            lines.append(f"    before: {r['before']}")
            lines.append(f"    match:  {r['match']}")
            lines.append(f"    after:  {r['after']}")

    text = "\n".join(lines)
    (OUT / "seimen-attr-fingerprint.txt").write_text(text, encoding="utf-8")
    print(text)
    print("\nwrote", OUT / "seimen-attr-fingerprint.txt")

    # If full mental found, dump a richer neighborhood for layout discovery
    mental_hits = hits.get("mental_full") or []
    if mental_hits:
        rich = []
        for r in mental_hits[:5]:
            # re-extract wider from abs by second pass would be heavy; use stored window
            win = r["window"]
            rel = r["rel"]
            # scan for other sections nearby
            for label, pat in (("gk", GK), ("phys", PHYS), ("tech", TECH)):
                j = win.find(pat)
                rich.append(
                    f"mental@abs={r['abs']}: {label} in window rel={None if j < 0 else j - rel}"
                )
            # dump +/- 200 as u8 list around mental
            s = max(0, rel - 80)
            e = min(len(win), rel + len(MENTAL) + 80)
            chunk = list(win[s:e])
            rich.append(f"  bytes[{s - rel}..{e - rel}]: {chunk}")
        (OUT / "seimen-attr-layout.txt").write_text("\n".join(rich), encoding="utf-8")
        print("\n".join(rich))


if __name__ == "__main__":
    main()
