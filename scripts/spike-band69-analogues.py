"""Find 69B-style records near all three doubles via structural footer,
then try to link Band's u16 const and re-test attr orderings.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/band69-analogues.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}
DOUBLE = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}
BAND_U16 = 0xA0B4
# Footer-ish: 00 00 [u16] 00 00 00 00 00 01 then small 5/10/15-ish run
# Band: ... 00 00 b4 a0 00 00 00 00 00 01 0f 0f 05 0a ...
FOOT_PREFIX = bytes([0x00, 0x00])  # before u16
FOOT_AFTER = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x01])


def extract(abs_target: int, length: int, before: int = 0) -> bytes:
    start = abs_target - before
    end = abs_target + length
    abs_base = 0
    carry = b""
    buf = bytearray()
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    block = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not block:
                    break
                data = carry + block
                chunk_start = abs_base - len(carry)
                if chunk_start < end and abs_base + len(block) > start:
                    already = len(buf)
                    want = start + already
                    lo = max(0, start - chunk_start, want - chunk_start)
                    hi = min(len(data), end - chunk_start)
                    if lo < hi:
                        buf.extend(data[lo:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= before + length:
                    break
        finally:
            reader.close()
    return bytes(buf)


def flat(p: dict) -> dict[str, int]:
    out = {}
    for g, attrs in p["attributes"].items():
        for k, v in attrs.items():
            out[f"{g}.{k}"] = int(v)
    return out


def phys_pairs(p: dict):
    a = flat(p)
    keys = [
        "physical.acceleration",
        "physical.agility",
        "physical.balance",
        "physical.jumpingReach",
        "physical.naturalFitness",
        "physical.pace",
        "physical.stamina",
        "physical.strength",
    ]
    return [(k, a[k]) for k in keys]


def score_phys(buf: bytes, off: int, pairs, tol=2):
    if off + 8 > len(buf):
        return 99, 0
    soft = 0
    ok = 0
    for i, (_, d) in enumerate(pairs):
        exp = d * 5
        diff = abs(buf[off + i] - exp)
        if diff <= tol:
            ok += 1
        else:
            soft += diff - tol
    return soft, ok


def looks_like_attr_prefix(b: bytes) -> bool:
    """First 22 bytes mostly in 35..100 (1-100 attr-ish)."""
    if len(b) < 22:
        return False
    mid = sum(1 for x in b[:22] if 35 <= x <= 100)
    return mid >= 16 and b[22] == 0x07 and b[24] == 0x9C


def main() -> None:
    lines: list[str] = []

    # Band u16 occurrences near UniqueID / double
    lines.append("======== Band u16 0xA0B4 vs UniqueID / double ========")
    pat = struct.pack("<H", BAND_U16)
    uid_b = struct.pack("<I", PLAYERS["Patrick Bandeira"]["uid"])
    zone = extract(DOUBLE["Patrick Bandeira"], 20000, before=20000)
    # search u16 in zone
    u16_hits = []
    start = 0
    while True:
        j = zone.find(pat, start)
        if j < 0:
            break
        u16_hits.append(DOUBLE["Patrick Bandeira"] - 20000 + j)
        start = j + 1
    lines.append(f"u16 hits in dbl±20KB: {len(u16_hits)} first={u16_hits[:15]}")
    uid_in = zone.find(uid_b)
    lines.append(f"UID in same zone: {uid_in} (abs={DOUBLE['Patrick Bandeira']-20000+uid_in if uid_in>=0 else None})")

    # Scan ±32KB around each double for 69B-shaped records
    lines.append("\n======== 69B-shaped records near each double (±32KB) ========")
    for name, dbl in DOUBLE.items():
        win = extract(dbl, 32768, before=32768)
        found = []
        for i in range(0, len(win) - 69):
            # cheap filter: 07 at +22, 9c at +24, zeros at +34,+35, 01 at +42
            if win[i + 22] != 0x07 or win[i + 24] != 0x9C:
                continue
            if win[i + 34] != 0 or win[i + 35] != 0:
                continue
            if win[i + 42] != 1:
                continue
            if not looks_like_attr_prefix(win[i : i + 25]):
                continue
            abs_i = dbl - 32768 + i
            u16 = struct.unpack_from("<H", win, i + 36)[0]
            soft, ok = score_phys(win, i + 14, phys_pairs(PLAYERS[name]), 2)
            found.append((abs_i, u16, soft, ok, list(win[i : i + 22])))
        lines.append(f"\n{name}: shaped hits={len(found)}")
        # sort by phys ok then proximity
        found.sort(key=lambda t: (-t[3], abs(t[0] - dbl)))
        for abs_i, u16, soft, ok, head in found[:12]:
            lines.append(
                f"  @{abs_i} dbl_rel={abs_i-dbl:+d} u16={u16} phys@+14 ok={ok}/8 soft={soft} head={head}"
            )

    # Broaden: drop attr-prefix requirement, keep 07/9c/zeros/01
    lines.append("\n======== looser structure near doubles ========")
    for name, dbl in DOUBLE.items():
        win = extract(dbl, 48000, before=48000)
        found = []
        for i in range(0, len(win) - 69):
            if win[i + 22] != 0x07 or win[i + 24] != 0x9C:
                continue
            if win[i + 34:i + 36] != b"\x00\x00":
                continue
            if win[i + 38:i + 43] != b"\x00\x00\x00\x00\x01":
                continue
            abs_i = dbl - 48000 + i
            u16 = struct.unpack_from("<H", win, i + 36)[0]
            soft, ok = score_phys(win, i + 14, phys_pairs(PLAYERS[name]), 2)
            # also try phys at other offs
            best_ok = ok
            best_off = 14
            for off in (0, 8, 10, 12, 14, 16):
                s2, o2 = score_phys(win, i + off, phys_pairs(PLAYERS[name]), 2)
                if o2 > best_ok:
                    best_ok, best_off, soft = o2, off, s2
            found.append((abs_i, u16, soft, best_ok, best_off, list(win[i : i + 22])))
        found.sort(key=lambda t: (-t[3], abs(t[0] - dbl)))
        lines.append(f"\n{name}: loose hits={len(found)} (show top by phys match)")
        for abs_i, u16, soft, ok, off, head in found[:15]:
            lines.append(
                f"  @{abs_i} rel={abs_i-dbl:+d} u16={u16} best_phys@+{off} ok={ok}/8 soft={soft}"
            )
            if ok >= 5:
                lines.append(f"    head22={head}")

    # Alt mental orderings for Band rec0 against fixture
    lines.append("\n======== Band mental alt-orders @+0 ========")
    rec = extract(264923389, 69)
    a = flat(PLAYERS["Patrick Bandeira"])
    # candidate orders (lists of short names)
    orders = {
        "screen": [
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
        ],
        # swap otb with positioning (seen as possible swap)
        "swap_otb_pos": [
            "aggression",
            "anticipation",
            "bravery",
            "composure",
            "concentration",
            "decisions",
            "determination",
            "flair",
            "leadership",
            "positioning",
            "offTheBall",
            "teamwork",
            "vision",
            "workRate",
        ],
        # older FM "Influence" naming order variants
        "work_first": [
            "workRate",
            "vision",
            "teamwork",
            "positioning",
            "offTheBall",
            "leadership",
            "flair",
            "determination",
            "decisions",
            "concentration",
            "composure",
            "bravery",
            "anticipation",
            "aggression",
        ],
    }
    for label, names in orders.items():
        ok = 0
        soft = 0
        for i, nm in enumerate(names):
            disp = a[f"mental.{nm}"]
            exp = disp * 5
            got = rec[i]
            diff = abs(got - exp)
            if diff <= 2:
                ok += 1
            else:
                soft += diff - 2
        lines.append(f"  {label}: ok={ok}/14 soft={soft}")

    # Treat round(byte/5) as ground truth and report delta vs fixture (staleness view)
    lines.append("\n======== If +0..+21 ARE attrs: display deltas vs fixture ========")
    ment = orders["screen"]
    phys = [
        "acceleration",
        "agility",
        "balance",
        "jumpingReach",
        "naturalFitness",
        "pace",
        "stamina",
        "strength",
    ]
    lines.append("mental@0 as round(b/5):")
    for i, nm in enumerate(ment):
        got = round(rec[i] / 5)
        fix = a[f"mental.{nm}"]
        lines.append(f"  {nm}: save~{got} fixture={fix} delta={got-fix:+d}")
    lines.append("physical@14 as round(b/5):")
    for i, nm in enumerate(phys):
        got = round(rec[14 + i] / 5)
        fix = a[f"physical.{nm}"]
        lines.append(f"  {nm}: save~{got} fixture={fix} delta={got-fix:+d}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
