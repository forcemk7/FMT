#!/usr/bin/env python3
"""Extract First Team / II / U19 squads from packed job-id lists near TID headers."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/squad-roster-locked.txt")
FIXTURE = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)

JOB = {
    113517: "Dennis Seimen",
    334108: "Patrick Bandeira",
    366083: "Robert Müller",
    237871: "Ermin Maric (II)",
    439758: "James Solo (U19)",
    540180: "Sangaré (U19_prev)",
}
UID = {p["name"]: int(p["uid"]) for p in FIXTURE}
UID.update(
    {
        "Ermin Maric (II)": 2002138129,
        "James Solo (U19)": 2002332550,
        "Sangaré (U19_prev)": 2002423570,
    }
)
# invert for resolution: job -> need uid from person record later
TID_FT = 193616
FT_LIST_ABS = 56_015_005  # start of packed job ids after TID header


def log(s: str = "") -> None:
    print(s, flush=True)


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


def parse_packed_u32_run(blob: bytes, start: int, max_n: int = 80) -> list[int]:
    vals = []
    i = start
    while i + 4 <= len(blob) and len(vals) < max_n:
        v = struct.unpack_from("<I", blob, i)[0]
        if not (100_000 <= v <= 800_000):
            break
        vals.append(v)
        i += 4
    return vals


def resolve_jobs_to_names(job_ids: list[int]) -> dict[int, str]:
    """Map job id -> person name via 0b02/09xx ASSOC pattern in save."""
    resolved = {j: JOB[j] for j in job_ids if j in JOB}
    remaining = [j for j in job_ids if j not in resolved]
    if not remaining:
        return resolved

    # search tag 0b/09 02 <job> 02 <uid> then name after 0002+uid
    pats = {}
    for j in remaining:
        jb = struct.pack("<I", j)
        pats[j] = [
            b"\x0b\x02" + jb + b"\x02",
            b"\x09\x02" + jb + b"\x02",
            b"\x08\x02" + jb + b"\x02",
            b"\x0a\x02" + jb + b"\x02",
        ]
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
                for j in list(remaining):
                    for pat in pats[j]:
                        k = data.find(pat)
                        if k < 0:
                            continue
                        if k + len(pat) + 4 > len(data):
                            continue
                        uid = struct.unpack_from("<I", data, k + len(pat))[0]
                        if not (1_900_000_000 <= uid <= 2_100_000_000):
                            continue
                        # find name near 0002+uid nearby
                        marked = b"\x00\x02" + struct.pack("<I", uid)
                        m = data.find(marked, max(0, k - 20), min(len(data), k + 80))
                        if m < 0:
                            m = data.find(marked)
                        if m >= 0:
                            for off in range(m + 6, min(len(data) - 8, m + 80)):
                                ln = struct.unpack_from("<I", data, off)[0]
                                if 2 <= ln <= 40 and off + 4 + ln <= len(data):
                                    raw = data[off + 4 : off + 4 + ln]
                                    if raw.isascii() and all(32 <= b < 127 for b in raw):
                                        name = raw.decode("ascii")
                                        if name[:1].isupper():
                                            # try to get surname too
                                            name2 = name
                                            off2 = off + 4 + ln
                                            if off2 + 8 <= len(data):
                                                ln2 = struct.unpack_from("<I", data, off2)[0]
                                                if 2 <= ln2 <= 40 and off2 + 4 + ln2 <= len(data):
                                                    raw2 = data[off2 + 4 : off2 + 4 + ln2]
                                                    if raw2.isascii() and all(
                                                        32 <= b < 127 for b in raw2
                                                    ):
                                                        s2 = raw2.decode("ascii")
                                                        if s2[:1].isupper():
                                                            name2 = f"{name} {s2}"
                                            resolved[j] = name2
                                            if j in remaining:
                                                remaining.remove(j)
                                            break
                        break
                carry = data[-200:]
                abs_base += len(block)
                if not remaining:
                    break
                if abs_base > 400_000_000 and len(remaining) > 20:
                    # don't scan forever for first pass
                    break
        finally:
            reader.close()
    return resolved


def main() -> None:
    lines: list[str] = []

    def out(s: str = "") -> None:
        log(s)
        lines.append(s)

    # Wide window covering FT list + adjacent team blocks (~56014749 area)
    win = extract(FT_LIST_ABS, 4096, before=512)
    base = FT_LIST_ABS - 512
    out("======== dump around FT packed list ========")
    for row in dump(win, base, 768):
        out(row)

    # Locate TID in window
    tid_rel = win.find(struct.pack("<I", TID_FT))
    out(f"\nTID_FT in window rel={tid_rel} abs={base+tid_rel if tid_rel>=0 else -1}")

    # Parse header: look at bytes just before packed list
    list_rel = 512  # FT_LIST_ABS
    out("\nheader before list:")
    for row in dump(win[list_rel - 64 : list_rel + 16], base + list_rel - 64, 80):
        out(row)

    ft_jobs = parse_packed_u32_run(win, list_rel, 60)
    out(f"\nFirst Team packed jobs: n={len(ft_jobs)}")
    # detect end: after zeros / ff trail in dump we saw ending then 00 00 00 00 ff ff
    # Our parser stops at first non-job-range value — check what follows
    end_rel = list_rel + 4 * len(ft_jobs)
    out(f"bytes after list @{base+end_rel}: {win[end_rel:end_rel+32].hex(' ')}")

    # Find sibling team blocks with same framing `64 ff ?? ?? 02`
    out("\n======== sibling 64 ff headers in ±4KB ========")
    start = 0
    headers = []
    while True:
        j = win.find(b"\x64\xff", start)
        if j < 0:
            break
        headers.append(base + j)
        # dump small context
        for row in dump(win[j : j + 96], base + j, 96):
            out(row)
        # try to find packed job run after possible TID
        # scan forward up to 80 bytes for a run of >=10 job-like u32s
        best = None
        for off in range(j, min(len(win) - 4, j + 120)):
            run = parse_packed_u32_run(win, off, 60)
            if len(run) >= 10:
                best = (base + off, run)
                break
        if best:
            abs_list, run = best
            # TID just before?
            tid = None
            frag = win[max(0, off - 32) : off]
            for i in range(0, len(frag) - 3):
                v = struct.unpack_from("<I", frag, i)[0]
                if 100_000 <= v <= 300_000:
                    tid = v
            out(f"  -> list @{abs_list} n={len(run)} tid_near={tid}")
            flags = [JOB[x] for x in run if x in JOB]
            out(f"     known={flags}")
        start = j + 1
        out()

    # Resolve FT roster names
    out("\n======== resolve First Team roster ========")
    names = resolve_jobs_to_names(ft_jobs)
    known_ft = []
    for i, jid in enumerate(ft_jobs):
        nm = names.get(jid, "?")
        mark = ""
        if jid in JOB:
            mark = f" <<CALIB:{JOB[jid]}"
            known_ft.append(JOB[jid])
        out(f"  [{i:02d}] job={jid}  {nm}{mark}")
    out(f"\ncalibration present: {known_ft}")
    missing = [
        n
        for n in ("Dennis Seimen", "Patrick Bandeira", "Robert Müller")
        if n not in known_ft
    ]
    out(f"calibration missing: {missing}")

    # Check subunit players NOT in FT list
    for jid, label in JOB.items():
        in_ft = jid in ft_jobs
        out(f"  {label} in FT list: {in_ft}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    out(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
