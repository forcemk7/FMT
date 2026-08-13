"""Decode aligned name-trail fields; chase mid-ids (possible birth city)."""

from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/name-trail-map.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}

# UID immediately before lp32(full name) — from prior resolve / map
RECORDS = {
    "Dennis Seimen": 1955884456,  # early UID in block; real name UID slightly after
    "Patrick Bandeira": 1965543032,
    "Robert Müller": 1955845509,
}


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


def find_trail_after_names(uid: int, abs_hint: int) -> tuple[int, bytes]:
    """Return (trail_abs, 128 bytes of trail) after last-name null."""
    blob = extract(abs_hint, 400, before=32)
    uid_b = struct.pack("<I", uid)
    # prefer the UID that is followed by lp32 with plausible length
    start = 0
    while True:
        j = blob.find(uid_b, start)
        if j < 0:
            raise RuntimeError(f"uid not found near {abs_hint}")
        if j + 8 < len(blob):
            (n,) = struct.unpack_from("<I", blob, j + 4)
            if 3 <= n <= 40:
                off = j + 4
                # skip full + last
                for _ in range(2):
                    (n,) = struct.unpack_from("<I", blob, off)
                    off += 4 + n
                if off < len(blob) and blob[off] == 0:
                    off += 1  # separator after last name
                trail_abs = abs_hint - 32 + off
                return trail_abs, blob[off : off + 128]
        start = j + 1


def ascii_near(abs_pos: int, rad: int = 64) -> str:
    b = extract(abs_pos, rad, before=rad)
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


def main() -> None:
    lines: list[str] = []
    mid_ids: dict[str, int] = {}
    decoded: dict[str, dict] = {}

    for name, hint in RECORDS.items():
        p = PLAYERS[name]
        trail_abs, trail = find_trail_after_names(p["uid"], hint)
        vis6 = list(trail[0:6])
        u32_6 = struct.unpack_from("<I", trail, 6)[0]
        u32_10 = struct.unpack_from("<I", trail, 10)[0]
        u32_14 = struct.unpack_from("<I", trail, 14)[0]
        u32_18 = struct.unpack_from("<I", trail, 18)[0]
        u32_22 = struct.unpack_from("<I", trail, 22)[0]
        u16_26 = struct.unpack_from("<H", trail, 26)[0]
        f_28 = struct.unpack_from("<f", trail, 28)[0]
        u32_32 = struct.unpack_from("<I", trail, 32)[0]
        rest = trail[36:96]

        mid_ids[name] = u32_18
        decoded[name] = {
            "trail_abs": trail_abs,
            "vis6": vis6,
            "u32_6": u32_6,
            "u32_10": u32_10,
            "u32_14": u32_14,
            "mid_id": u32_18,
            "u32_22": u32_22,
            "u16_26": u16_26,
            "float28": f_28,
            "u32_32": u32_32,
        }

        lines.append(f"## {name}")
        lines.append(
            f"  known: nation={p['nation']} nation2={p.get('nation2')} foot={p['foot']} "
            f"dob={p['dob']} height={p['height_cm']} age={p['age']} kind={p['kind']}"
        )
        lines.append(f"  trail@{trail_abs}")
        lines.append(f"  +0..+5  vis6? {vis6}")
        lines.append(f"  +6      u32={u32_6}")
        lines.append(f"  +10     u32={u32_10} (0x{u32_10:X})")
        lines.append(
            f"  +14     u32={u32_14 if u32_14 != 0xFFFFFFFF else 'NULL'} (0x{u32_14:X})"
        )
        lines.append(f"  +18     mid_id={u32_18}  <- chase")
        lines.append(f"  +22     u32={u32_22}")
        lines.append(f"  +26     u16={u16_26}")
        lines.append(f"  +28     f32={f_28:.6f}")
        lines.append(f"  +32     u32={u32_32}")
        lines.append(f"  +36..   {rest[:48].hex(' ')}")
        # relation-ish scan
        rels = []
        i = 36
        while i + 12 < len(trail):
            if trail[i : i + 2] == b"\x03\x00" and trail[i + 3 : i + 6] == b"\x03\x01\x02":
                typ = trail[i + 2]
                (val,) = struct.unpack_from("<I", trail, i + 6)
                rels.append((i, typ, val))
                i += 14
                continue
            # NEWGEN variant: NN 03 4e 64 01 03 02 u32
            if (
                i + 12 < len(trail)
                and trail[i + 1 : i + 6] == b"\x03\x4e\x64\x01\x03"
                and trail[i + 6 : i + 7] == b"\x02"
            ):
                (val,) = struct.unpack_from("<I", trail, i + 7)
                rels.append((i, f"ng_{trail[i]}", val))
                i += 15
                continue
            i += 1
        lines.append(f"  rels: {rels[:10]}")
        lines.append("")

    # Cross-check known scalars in trail
    lines.append("======== known-value fingerprints in first 48 trail bytes ========")
    for name, d in decoded.items():
        p = PLAYERS[name]
        trail_abs, trail = find_trail_after_names(p["uid"], RECORDS[name])
        win = trail[:48]
        for label, val in [
            ("height", p["height_cm"]),
            ("h-100", p["height_cm"] - 100),
            ("age", p["age"]),
            ("det", p["det"]),
            ("lea", p["lea"]),
        ]:
            hits = [i for i, b in enumerate(win) if b == val]
            lines.append(f"  {name} {label}={val} @ {hits}")

    # Chase mid_ids single-pass
    lines.append("\n======== mid_id chase (possible city/region) ========")
    pats = {n: struct.pack("<I", mid_ids[n]) for n in mid_ids}
    findings: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    abs_base = 0
    carry = b""
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
                for name, pat in pats.items():
                    if len(findings[name]) >= 20:
                        continue
                    start = 0
                    while len(findings[name]) < 20:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        abs_hit = chunk_start + j
                        if abs_hit >= abs_base:
                            after = data[j : j + 40]
                            printable = sum(32 <= b < 127 for b in after[4:36])
                            kind = "ascii" if printable >= 10 else "other"
                            if after[4:8] == pat:
                                kind = "dup_pair"
                            if b"\x01\x00\x6c\x07" in after:
                                kind = "near_type"
                            # skip the trail itself
                            own = decoded[name]["trail_abs"] + 18
                            if abs(abs_hit - own) > 4:
                                findings[name].append(
                                    (
                                        abs_hit,
                                        kind,
                                        "".join(
                                            chr(b) if 32 <= b < 127 else "."
                                            for b in data[max(0, j - 32) : j + 48]
                                        ),
                                    )
                                )
                        start = j + 1
                abs_base += len(block)
                carry = data[-8:]
        finally:
            reader.close()

    for name, mid in mid_ids.items():
        rows = findings[name]
        kinds = Counter(k for _, k, _ in rows)
        lines.append(f"\n{name} mid_id={mid} kinds={dict(kinds)}")
        for abs_hit, kind, asc in rows[:10]:
            lines.append(f"  @{abs_hit} [{kind}] {asc}")

    lines.append(
        """
======== FIELD MAP (name trail after last-name) ========
+0..+5   six u8s (appearance / classification — unlabeled)
+6..+9   u32 (0 or 1 here)
+10..+13 u32 (Seimen/Müller=0x303, Bandeira=0x314)
+14..+17 u32 or NULL (Seimen=790; newgens NULL)
+18..+21 mid_id (birth city / region candidate)
+22..+25 u32
+26..+27 u16
+28..+31 float32 (also appears in pre-name header)
+32..+35 u32
+36..    typed relation list (REAL vs NEWGEN shapes differ)

NOT found as raw bytes in first 48: height, age, det, lea, DOB year.
Nation/foot likely in vis6 or mid_id / relation list — chase continues.
"""
    )

    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
