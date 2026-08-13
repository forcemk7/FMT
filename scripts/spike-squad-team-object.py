"""Find team object for id 193616 and extract its player list."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-team-object-193616.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
UIDS = {p["name"]: int(p["uid"]) for p in FIXTURE}
NAME_BY = {v: k for k, v in UIDS.items()}
TID = 193616
TID_PAT = struct.pack("<I", TID)
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


def lp32_strings(buf: bytes, base: int) -> list[tuple[int, str]]:
    out = []
    i = 0
    while i + 8 <= len(buf):
        ln = struct.unpack_from("<I", buf, i)[0]
        if 2 <= ln <= 80 and i + 4 + ln <= len(buf):
            raw = buf[i + 4 : i + 4 + ln]
            if raw.isascii() and all(32 <= b < 127 for b in raw):
                s = raw.decode("ascii")
                if any(c.isalpha() for c in s):
                    out.append((base + i, s))
                    i += 4 + ln
                    continue
        i += 1
    return out


def resolve_names(uids: list[int]) -> dict[int, str]:
    resolved = dict(NAME_BY)
    remaining = [u for u in uids if u not in resolved]
    if not remaining:
        return resolved
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
                    for off in range(j + 6, min(len(data) - 8, j + 120)):
                        ln = struct.unpack_from("<I", data, off)[0]
                        if 5 <= ln <= 48 and off + 4 + ln <= len(data):
                            raw = data[off + 4 : off + 4 + ln]
                            if raw.isascii() and all(32 <= b < 127 for b in raw):
                                name = raw.decode("ascii")
                                if name[0].isupper() and any(c.isalpha() for c in name):
                                    cur = resolved.get(uid, "")
                                    if " " in name or " " not in cur:
                                        resolved[uid] = name
                                    if " " in name and uid in remaining:
                                        remaining.remove(uid)
                                    break
                abs_base += len(block)
                carry = data[-160:]
                if not remaining:
                    break
        finally:
            reader.close()
    return resolved


def main() -> None:
    lines: list[str] = []

    # Fast: find TID hits that have an lp32 name within ±128 bytes (team object header)
    print("pass1: TID near names…", flush=True)
    candidates: list[tuple[int, str, bytes]] = []
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
                while True:
                    j = data.find(TID_PAT, start)
                    if j < 0:
                        break
                    if j >= 128 and j + 128 <= len(data):
                        ctx = data[j - 128 : j + 128]
                        # look for lp32 name in ctx
                        for off in range(0, len(ctx) - 8):
                            ln = struct.unpack_from("<I", ctx, off)[0]
                            if 3 <= ln <= 60 and off + 4 + ln <= len(ctx):
                                raw = ctx[off + 4 : off + 4 + ln]
                                if raw.isascii() and all(32 <= b < 127 for b in raw):
                                    s = raw.decode("ascii")
                                    if any(c.isalpha() for c in s) and s[0].isupper():
                                        candidates.append(
                                            (chunk_start + j, s, ctx)
                                        )
                                        break
                    start = j + 1
                abs_base += len(block)
                carry = data[-200:]
        finally:
            reader.close()

    # unique by abs
    seen = set()
    uniq = []
    for a, s, ctx in candidates:
        if a in seen:
            continue
        seen.add(a)
        uniq.append((a, s, ctx))
    lines.append(f"TID hits near lp32 names: {len(uniq)}")
    for a, s, ctx in uniq[:40]:
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
        lines.append(f"  @{a} name_near={s!r}")
        lines.append(f"    {asc}")

    # Expand Schalke-named ones
    schalke_hits = [(a, s, ctx) for a, s, ctx in uniq if "Schalke" in s or "schalke" in s]
    lines.append(f"\nSchalke-named near TID: {len(schalke_hits)}")
    for a, s, ctx in schalke_hits:
        lines.append(f"\n### @{a} {s!r}")
        win = extract(a, 8192, before=512)
        base = a - 512
        for sa, ss in lp32_strings(win, base):
            if abs(sa - a) < 4000:
                lines.append(f"  str @{sa} {ss!r}")
        lines.extend(dump(win[512 - 64 : 512 + 256], a - 64, 320))

        # Player list heuristics in this team window
        # 1) count-prefixed UID list
        found_lists = []
        for i in range(0, len(win) - 8):
            count = struct.unpack_from("<I", win, i)[0]
            if 15 <= count <= 45:
                vals = []
                ok = True
                for k in range(count):
                    off = i + 4 + 4 * k
                    if off + 4 > len(win):
                        ok = False
                        break
                    v = struct.unpack_from("<I", win, off)[0]
                    if not (UID_LO <= v <= UID_HI):
                        ok = False
                        break
                    vals.append(v)
                if ok and len(set(vals)) >= count * 0.9:
                    known = [NAME_BY[v] for v in vals if v in NAME_BY]
                    found_lists.append((base + i, count, known, vals))
        lines.append(f"  count-prefixed UID lists(15-45): {len(found_lists)}")
        for abs_i, count, known, vals in found_lists[:5]:
            lines.append(f"    @{abs_i} n={count} known={known}")
            if known:
                names = resolve_names(vals)
                for idx, uid in enumerate(vals):
                    lines.append(
                        f"      [{idx:02d}] {uid}  {names.get(uid,'?')}"
                        f"{' <<FIX' if uid in NAME_BY else ''}"
                    )

        # 2) stride-N UID records (8..32)
        for stride in (4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 64, 174):
            for align in range(min(4, stride)):
                vals = []
                i = align
                # find a start with UID
                while i + 4 <= len(win):
                    v0 = struct.unpack_from("<I", win, i)[0]
                    if UID_LO <= v0 <= UID_HI:
                        break
                    i += 1
                else:
                    continue
                j = i
                while j + 4 <= len(win) and len(vals) < 50:
                    v = struct.unpack_from("<I", win, j)[0]
                    if not (UID_LO <= v <= UID_HI):
                        break
                    vals.append(v)
                    j += stride
                known = [NAME_BY[v] for v in vals if v in NAME_BY]
                if len(vals) >= 15 and len(known) >= 2:
                    lines.append(
                        f"  stride{stride} align{align} @{base+i} n={len(vals)} "
                        f"known={known}"
                    )
                    if len(set(known)) >= 2:
                        names = resolve_names(vals)
                        for idx, uid in enumerate(vals):
                            lines.append(
                                f"      [{idx:02d}] {uid}  {names.get(uid,'?')}"
                                f"{' <<FIX' if uid in NAME_BY else ''}"
                            )

    # Also: expand the 6-player stride-174 strip — it had all 3 fixtures
    lines.append("\n======== revisit stride-174 @813373363 with wider window ========")
    center = 813373363
    win = extract(center, 174 * 60, before=174 * 10)
    base = center - 174 * 10
    # find Seimen alignment
    j = win.find(struct.pack("<I", UIDS["Dennis Seimen"]))
    lines.append(f"Seimen rel={j}")
    if j >= 0:
        # walk backward while UID at stride 174
        start = j
        while start - 174 >= 0:
            v = struct.unpack_from("<I", win, start - 174)[0]
            if not (UID_LO <= v <= UID_HI):
                break
            start -= 174
        vals = []
        off = start
        while off + 4 <= len(win):
            v = struct.unpack_from("<I", win, off)[0]
            if not (UID_LO <= v <= UID_HI):
                break
            vals.append(v)
            off += 174
            if len(vals) >= 50:
                break
        lines.append(f"stride174 run @{base+start} n={len(vals)}")
        names = resolve_names(vals)
        known = [NAME_BY[v] for v in vals if v in NAME_BY]
        lines.append(f"known fixtures: {known}")
        for idx, uid in enumerate(vals):
            lines.append(
                f"  [{idx:02d}] {uid}  {names.get(uid,'?')}"
                f"{' <<FIX' if uid in NAME_BY else ''}"
            )
        # dump record header of first row
        lines.append("first record 64B:")
        lines.extend(dump(win[start : start + 64], base + start))
        # check if TID in preheader
        pre = win[max(0, start - 64) : start]
        lines.append(f"pre64={pre.hex()} TID_in_pre={TID_PAT in pre}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii")[:35000])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
