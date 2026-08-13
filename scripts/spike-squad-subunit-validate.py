#!/usr/bin/env python3
"""Sprint: validate U19 packed jobs are players; find II list via Ermin job."""

from __future__ import annotations

import mmap
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "fm-spike" / "squad-subunit-validate.txt"

U19_JOBS = [
    437493, 437421, 437332, 437169, 436682, 536212, 536066, 535864,
    535844, 535812, 535744, 535741, 535670, 535654, 439854, 439824,
    552105, 554789, 554754, 554729, 554711, 554697, 554595, 554563,
    554554, 437385,
]
JOB_II = 237871
JOB_SOLO = 439758


def pick_bin() -> Path:
    for p in sorted(
        Path.home().joinpath("AppData", "Local", "Temp").glob("fmt-*.bin"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        if p.stat().st_size > 1_500_000_000:
            return p
    raise SystemExit("no bin")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 100) -> list[int]:
    out = []
    start = 0
    while len(out) < limit:
        j = mm.find(needle, start)
        if j < 0:
            break
        out.append(j)
        start = j + 1
    return out


def resolve_job_uid_name(mm: mmap.mmap, job: int) -> tuple[int | None, str | None]:
    jb = struct.pack("<I", job)
    for tag in (0x0B, 0x09, 0x0A, 0x08):
        pat = bytes([tag, 0x02]) + jb + b"\x02"
        for off in find_all(mm, pat, limit=20):
            uid = struct.unpack_from("<I", mm, off + 6)[0]
            if not (1_900_000_000 <= uid <= 2_100_000_000):
                continue
            # name after 0002+uid nearby
            marked = b"\x00\x02" + struct.pack("<I", uid)
            m = mm.find(marked, max(0, off - 40), min(len(mm), off + 120))
            name = None
            if m >= 0:
                for noff in range(m + 6, min(len(mm) - 4, m + 80)):
                    ln = struct.unpack_from("<I", mm, noff)[0]
                    if 2 <= ln <= 40 and noff + 4 + ln <= len(mm):
                        raw = bytes(mm[noff + 4 : noff + 4 + ln])
                        if raw.isascii() and raw[:1].isalpha():
                            name = raw.decode("ascii")
                            # surname
                            n2 = noff + 4 + ln
                            if n2 + 8 <= len(mm):
                                ln2 = struct.unpack_from("<I", mm, n2)[0]
                                if 2 <= ln2 <= 40 and n2 + 4 + ln2 <= len(mm):
                                    raw2 = bytes(mm[n2 + 4 : n2 + 4 + ln2])
                                    if raw2.isascii() and raw2[:1].isalpha():
                                        name = f"{name} {raw2.decode('ascii')}"
                            break
            return uid, name
    return None, None


def find_packed_lists_containing(mm: mmap.mmap, job: int) -> list[dict]:
    """Find count_u16 job packs that include `job`."""
    jb = struct.pack("<I", job)
    out = []
    for hit in find_all(mm, jb, limit=80):
        # job must be 4-aligned within a pack: look back for count
        for back in range(0, 240, 4):
            coff = hit - back - 2
            if coff < 0:
                continue
            # require job slot alignment: (hit - (coff+2)) % 4 == 0
            if (hit - (coff + 2)) % 4 != 0:
                continue
            count = struct.unpack_from("<H", mm, coff)[0]
            if not (12 <= count <= 60):
                continue
            idx = (hit - (coff + 2)) // 4
            if idx >= count:
                continue
            jobs = [
                struct.unpack_from("<I", mm, coff + 2 + 4 * k)[0] for k in range(count)
            ]
            if jobs[idx] != job:
                continue
            ok = sum(1 for j in jobs if 50_000 <= j <= 2_000_000)
            if ok < count * 2 // 3:
                continue
            out.append({"count_at": coff, "count": count, "jobs": jobs, "idx": idx})
            break
    # dedupe by count_at
    seen = set()
    uniq = []
    for r in out:
        if r["count_at"] in seen:
            continue
        seen.add(r["count_at"])
        uniq.append(r)
    return uniq


def main() -> int:
    bin_path = pick_bin()
    t0 = time.perf_counter()
    lines = [f"# subunit validate · {bin_path.name}", ""]
    print(f"mmap {bin_path.name}…", flush=True)

    with bin_path.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            lines.append("## resolve sample U19 packed jobs → uid/name")
            for job in U19_JOBS[:8] + U19_JOBS[14:18]:
                uid, name = resolve_job_uid_name(mm, job)
                lines.append(f"  job={job} → uid={uid} name={name}")

            lines.append("")
            lines.append("## packed lists containing Ermin II job")
            for r in find_packed_lists_containing(mm, JOB_II):
                lines.append(
                    f"  count@{r['count_at']} n={r['count']} idx={r['idx']} "
                    f"jobs0_8={r['jobs'][:8]}"
                )
                lines.append(
                    "  pre48: "
                    + bytes(mm[max(0, r["count_at"] - 48) : r["count_at"] + 4]).hex(" ")
                )
                # name strings nearby?
                win = bytes(mm[max(0, r["count_at"] - 200) : r["count_at"]])
                for s in (b"II", b"U19", b"Schalke", b"Reserve"):
                    if s in win:
                        lines.append(f"  pre-window contains {s!r}")

            lines.append("")
            lines.append("## packed lists containing Solo U19 job")
            for r in find_packed_lists_containing(mm, JOB_SOLO):
                lines.append(
                    f"  count@{r['count_at']} n={r['count']} idx={r['idx']} "
                    f"jobs0_8={r['jobs'][:8]}"
                )
                lines.append(
                    "  pre48: "
                    + bytes(mm[max(0, r["count_at"] - 48) : r["count_at"] + 4]).hex(" ")
                )

            # Header motif of U19 list: twin ptr then … ffffffff 00 ffffffff count
            lines.append("")
            lines.append("## scan for U19-like headers (ffffffff 00 ffffffff <count>) near 'U19'")
            motif = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"
            for h in find_all(mm, b"Schalke 04 U19", limit=10):
                region = bytes(mm[h : min(len(mm), h + 200)])
                j = region.find(motif)
                lines.append(f"U19@{h}: motif_rel={j}")

            for h in find_all(mm, b"Schalke 04 II", limit=20):
                if h < 20_000_000:
                    continue
                region = bytes(mm[max(0, h - 50) : min(len(mm), h + 250)])
                j = region.find(motif)
                if j >= 0:
                    abs_m = max(0, h - 50) + j
                    count = struct.unpack_from("<H", mm, abs_m + len(motif))[0]
                    lines.append(
                        f"II@{h}: motif@{abs_m} count={count}"
                    )

        finally:
            mm.close()

    lines.append(f"\nelapsed={time.perf_counter() - t0:.1f}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
