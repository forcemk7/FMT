#!/usr/bin/env python3
"""Find person records + team-id associations for new Reserve/U19 UIDs."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-person-team-link.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

KNOWN = {
    "Reserve_II": 2002138129,
    "U19": 2002332550,
    "Reserve_prev": 2002206353,
    "U19_prev": 2002423570,
}
for p in FIXTURE:
    KNOWN[p["name"]] = int(p["uid"])
NAME_BY = {v: k for k, v in KNOWN.items()}

# Candidate team ids
TID_FT = 193616  # from shortlists
TID_U19_CAND = 148788  # 34 45 02 00 near FC Schalke 04 U19 name

UID_LO, UID_HI = 1_900_000_000, 2_100_000_000


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


def dump(b: bytes, base: int, n: int | None = None) -> list[str]:
    if n is not None:
        b = b[:n]
    lines = []
    for i in range(0, len(b), 32):
        chunk = b[i : i + 32]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"  {base+i:10d}  {hexs:<96}  {asc}")
    return lines


def find_person_hits(uid: int, limit: int = 30) -> list[int]:
    """Prefer \x00\x02 + uid person markers; also plain uid hits near names."""
    marked = b"\x00\x02" + struct.pack("<I", uid)
    plain = struct.pack("<I", uid)
    hits_m: list[int] = []
    hits_p: list[int] = []
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
                start = 0
                while len(hits_m) < limit:
                    j = data.find(marked, start)
                    if j < 0:
                        break
                    hits_m.append(chunk_start + j)
                    start = j + 1
                start = 0
                while len(hits_p) < limit:
                    j = data.find(plain, start)
                    if j < 0:
                        break
                    hits_p.append(chunk_start + j)
                    start = j + 1
                abs_base += len(block)
                carry = data[-16:]
                if len(hits_m) >= limit:
                    break
        finally:
            reader.close()
    return hits_m if hits_m else hits_p


def nearby_strings(blob: bytes, base: int) -> list[tuple[int, str]]:
    out = []
    i = 0
    while i < len(blob):
        if 0x20 <= blob[i] < 0x7F:
            j = i
            while j < len(blob) and 0x20 <= blob[j] < 0x7F:
                j += 1
            if j - i >= 3:
                s = blob[i:j].decode("ascii", "replace")
                if any(c.isalpha() for c in s):
                    out.append((base + i, s[:80]))
            i = j
        else:
            i += 1
    return out


def find_ids_near(blob: bytes, base: int, ids: dict[str, int]) -> list[str]:
    found = []
    for label, val in ids.items():
        pat = struct.pack("<I", val)
        start = 0
        while True:
            j = blob.find(pat, start)
            if j < 0:
                break
            found.append(f"  {label}={val} @{base+j} d={j:+d}")
            start = j + 1
    return found


def main() -> None:
    lines: list[str] = []

    def log(s: str = "") -> None:
        try:
            print(s)
        except UnicodeEncodeError:
            print(s.encode("ascii", "replace").decode("ascii"))
        lines.append(s)

    candidate_tids = {
        "TID_FT": TID_FT,
        "TID_U19_cand": TID_U19_CAND,
    }

    # Also hunt likely II team id near II name object
    ii = extract(10_087_063, 256, before=128)
    log("u32s near II name that look like teamIds (100000-300000):")
    for i in range(0, len(ii) - 3):
        v = struct.unpack_from("<I", ii, i)[0]
        if 100_000 <= v <= 300_000:
            log(f"  @{10_087_063 - 128 + i} +{i-128} = {v}")
            candidate_tids[f"near_II_{v}"] = v

    ft = extract(3_431_104, 256, before=128)
    log("\nu32s near FT name (100000-300000):")
    for i in range(0, len(ft) - 3):
        v = struct.unpack_from("<I", ft, i)[0]
        if 100_000 <= v <= 300_000:
            log(f"  @{3_431_104 - 128 + i} +{i-128} = {v}")
            candidate_tids[f"near_FT_{v}"] = v

    u19 = extract(60_171_272, 256, before=128)
    log("\nu32s near U19 name (100000-300000):")
    for i in range(0, len(u19) - 3):
        v = struct.unpack_from("<I", u19, i)[0]
        if 100_000 <= v <= 300_000:
            log(f"  @{60_171_272 - 128 + i} +{i-128} = {v}")
            candidate_tids[f"near_U19_{v}"] = v

    log(f"\ncandidate TIDs: {candidate_tids}")

    for label, uid in KNOWN.items():
        log(f"\n######## {label} {uid} ########")
        hits = find_person_hits(uid, limit=15)
        log(f"person/uid hits (prefer 0002+uid): {len(hits)} first={hits[:5]}")
        for h in hits[:5]:
            win = extract(h, 512, before=128)
            base = h - 128
            log(f"\n--- @{h} ---")
            for row in dump(win, base, 256):
                log(row)
            strs = nearby_strings(win, base)
            if strs:
                log("strings:")
                for a, s in strs[:20]:
                    log(f"  @{a} {s!r}")
            tid_hits = find_ids_near(win, base, candidate_tids)
            if tid_hits:
                log("TIDs in ±window:")
                for t in tid_hits:
                    log(t)
            # also scan for any club-ish relation framing
            for i in range(0, len(win) - 12):
                if win[i] == 0x03 and win[i + 3] == 0x03 and win[i + 5] == 0x02:
                    kind = win[i + 1]
                    code = win[i + 2]
                    sub = win[i + 4]
                    val = struct.unpack_from("<I", win, i + 6)[0]
                    if val == uid or (UID_LO <= val <= UID_HI):
                        log(
                            f"  rel @{base+i} kind=0x{kind:02X} code=0x{code:02X} "
                            f"sub={sub} val={val}"
                        )

    # Cross: for each candidate TID, find 7f02/0b02/1402 UID lists that include our knowns
    log("\n######## TID → tagged UID membership ########")
    for tlabel, tid in list(candidate_tids.items())[:12]:
        pat = struct.pack("<I", tid)
        # find a few TID occurrences, scan +4KB for known UIDs
        abs_base = 0
        carry = b""
        found_sites = 0
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
                    start = 0
                    while found_sites < 8:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        abs_ = chunk_start + j
                        # skip if in dense zero regions only — still extract
                        win = extract(abs_, 8192, before=16)
                        present = []
                        for name, uid in KNOWN.items():
                            if struct.pack("<I", uid) in win:
                                present.append(name)
                        if present:
                            log(f"{tlabel}={tid} @{abs_} known_in_+8KB={present}")
                            found_sites += 1
                        start = j + 1
                    abs_base += len(block)
                    carry = data[-8:]
                    if found_sites >= 8:
                        break
            finally:
                reader.close()
        if found_sites == 0:
            log(f"{tlabel}={tid}: no sites with known UIDs in +8KB (sampled)")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
