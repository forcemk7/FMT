"""Dump full 0x0A (and neighbors) club relation UID lists; locate Müller tags."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-club-rel-0a.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
CLUB = 1986866253
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


def resolve_names(uids: list[int]) -> dict[int, str]:
    resolved = dict(NAME_BY)
    remaining = [u for u in uids if u not in resolved]
    pats = {u: b"\x00\x02" + struct.pack("<I", u) for u in remaining}
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
                for uid in list(remaining):
                    j = data.find(pats[uid])
                    if j < 0:
                        continue
                    best = None
                    for off in range(j + 6, min(len(data) - 8, j + 140)):
                        ln = struct.unpack_from("<I", data, off)[0]
                        if 5 <= ln <= 48 and off + 4 + ln <= len(data):
                            raw = data[off + 4 : off + 4 + ln]
                            if raw.isascii() and all(32 <= b < 127 for b in raw):
                                name = raw.decode("ascii")
                                if name[0].isupper() and any(c.isalpha() for c in name):
                                    if best is None or (" " in name and " " not in best):
                                        best = name
                    if best:
                        resolved[uid] = best
                        if " " in best:
                            remaining.remove(uid)
                abs_base += len(block)
                carry = data[-160:]
                if not remaining:
                    break
        finally:
            reader.close()
    return resolved


def main() -> None:
    lines: list[str] = []
    win = extract(CLUB, 40000, before=256)
    base = CLUB - 256
    j = win.find(b"FC Schalke 04")
    after = win[j:]
    after_base = base + j

    # Collect ALL 03 00 XX 03 YY 02 UID and 03 4f…
    entries = []
    i = 0
    while i + 12 <= len(after):
        if after[i] == 0x03 and after[i + 3] == 0x03 and after[i + 5] == 0x02:
            kind = after[i + 1]
            code = after[i + 2]
            sub = after[i + 4]
            val = struct.unpack_from("<I", after, i + 6)[0]
            if UID_LO <= val <= UID_HI:
                entries.append(
                    {
                        "abs": after_base + i,
                        "kind": kind,
                        "code": code,
                        "sub": sub,
                        "uid": val,
                        "raw": after[i : i + 10].hex(),
                    }
                )
            i += 6
        else:
            i += 1

    # Tag context for each fixture
    lines.append("======== fixture relation contexts ========")
    for name, uid in UIDS.items():
        hits = [e for e in entries if e["uid"] == uid]
        lines.append(f"{name}: {len(hits)} relation hits")
        for e in hits:
            lines.append(
                f"  @{e['abs']} kind=0x{e['kind']:02X} code=0x{e['code']:02X} "
                f"sub={e['sub']} raw={e['raw']}"
            )

    # Full 0x0A list (kind==0x00, code==0x0A)
    list_0a = [e for e in entries if e["kind"] == 0x00 and e["code"] == 0x0A]
    # Dedup UIDs preserve order
    uids_0a = list(dict.fromkeys(e["uid"] for e in list_0a))
    lines.append(f"\n======== relation 03 00 0A UID list n={len(uids_0a)} ========")
    print(f"resolving {len(uids_0a)} names for 0x0A…", flush=True)
    names = resolve_names(uids_0a)
    for i, uid in enumerate(uids_0a):
        lines.append(
            f"  [{i:02d}] {uid}  {names.get(uid,'?')}"
            f"{' <<FIX' if uid in NAME_BY else ''}"
        )
    missing = [n for n, u in UIDS.items() if u not in set(uids_0a)]
    lines.append(f"fixtures missing from 0x0A: {missing}")

    # For Müller: dump 32B around each fixture abs from prior slim
    lines.append("\n======== raw dump around Müller club hits ========")
    for abs_i in (1986867518, 1986867562):
        rel = abs_i - base
        chunk = win[max(0, rel - 16) : rel + 32]
        lines.append(f"@{abs_i}: {chunk.hex()}")
        # decode possible relation
        for off in range(max(0, rel - 16), rel):
            if (
                off + 10 <= len(win)
                and win[off] == 0x03
                and win[off + 3] == 0x03
                and win[off + 5] == 0x02
            ):
                val = struct.unpack_from("<I", win, off + 6)[0]
                if val == UIDS["Robert Müller"]:
                    lines.append(
                        f"  rel@{base+off} kind=0x{win[off+1]:02X} "
                        f"code=0x{win[off+2]:02X} sub={win[off+4]}"
                    )

    # Also dump earliest contiguous UID relation block after club name
    lines.append("\n======== first contiguous relation run after club ========")
    first_block = []
    for e in entries:
        if e["abs"] < after_base + 2000:
            first_block.append(e)
    uids_first = list(dict.fromkeys(e["uid"] for e in first_block))
    names_f = resolve_names(uids_first)
    lines.append(f"n={len(uids_first)}")
    for i, uid in enumerate(uids_first):
        ents = [e for e in first_block if e["uid"] == uid]
        codes = [f"0x{e['code']:02X}" for e in ents]
        lines.append(
            f"  [{i:02d}] {uid}  {names_f.get(uid,'?')}  codes={codes}"
            f"{' <<FIX' if uid in NAME_BY else ''}"
        )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
