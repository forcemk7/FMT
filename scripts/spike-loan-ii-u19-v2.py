#!/usr/bin/env python3
"""
T004B follow-up: verify loan clubIds + Millwood hunt + FP filter for 64ff24.
Append-only spike outputs: tmp/fm-spike/spike-loan-ii-u19-v2.txt
"""

from __future__ import annotations

import json
import mmap
import struct
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
OUT = ROOT / "tmp" / "fm-spike" / "spike-loan-ii-u19-v2.txt"
PARENT = 920

# Candidates from v1 motif+21 dups
CANDIDATES = {
    "Manole/Augsburg": 2238,
    "Braescu/Koln": 916,
    "Ozturk/Essen?": 2249,
    "Sipho/Legia": 1456,
    "Vlad/?": 912,
}

GT = [
    ("II", "Manole", 2002390860, 506986, 2238, "Augsburg"),
    ("II", "Braescu", 2002390854, 506980, 916, "Koln"),
    ("U19", "Millwood", 2002422274, 538884, None, "Paderborn"),
    ("U19", "Ozturk", 2002266096, 365838, 2249, "Essen"),
    ("FT", "Sipho", 2002282525, 382267, 1456, "Legia"),
]


def load_extract() -> dict:
    raw = EXTRACT.read_bytes()
    for enc in ("utf-16", "utf-8-sig"):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            pass
    raise RuntimeError("extract decode fail")


def find_all(mm: mmap.mmap, needle: bytes, limit: int = 80) -> list[int]:
    out, pos = [], 0
    while len(out) < limit:
        j = mm.find(needle, pos)
        if j < 0:
            break
        out.append(j)
        pos = j + 1
    return out


def lp32_at(mm: mmap.mmap, off: int) -> str | None:
    if off < 0 or off + 4 > len(mm):
        return None
    n = struct.unpack_from("<I", mm, off)[0]
    if not (1 <= n <= 80):
        return None
    raw = mm[off + 4 : off + 4 + n]
    if len(raw) != n:
        return None
    # ascii-ish
    if all(32 <= b < 127 or b in (0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC9, 0xD6, 0xDC, 0xE4, 0xF6, 0xFC, 0xDF) for b in raw):
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return raw.decode("latin-1", errors="replace")
    return None


def names_near_club(mm: mmap.mmap, club: int, *, radius: int = 256) -> list[str]:
    """Find lp32 names near clubId occurrences (and clubId×2)."""
    names: list[str] = []
    cb = struct.pack("<I", club)
    for off in find_all(mm, cb + cb, limit=40):  # dup pair
        for rel in range(-radius, radius, 1):
            s = lp32_at(mm, off + rel)
            if s and any(c.isalpha() for c in s) and s not in names:
                names.append(s)
                if len(names) >= 12:
                    return names
    if names:
        return names
    for off in find_all(mm, cb, limit=40):
        for rel in range(-radius, radius, 1):
            s = lp32_at(mm, off + rel)
            if s and any(c.isalpha() for c in s) and s not in names:
                names.append(s)
                if len(names) >= 12:
                    return names
    return names


def utf16_near_club(mm: mmap.mmap, club: int) -> list[str]:
    """Search for known substrings near club dup; return which matched."""
    needles = {
        "Augsburg": "Augsburg".encode("utf-16-le"),
        "Koln": "Köln".encode("utf-16-le"),
        "Paderborn": "Paderborn".encode("utf-16-le"),
        "Essen": "Essen".encode("utf-16-le"),
        "Legia": "Legia".encode("utf-16-le"),
        "Frankfurt": "Frankfurt".encode("utf-16-le"),
        "Schalke": "Schalke".encode("utf-16-le"),
    }
    hits = []
    cb = struct.pack("<I", club) * 2
    for off in find_all(mm, cb, limit=30):
        window = mm[max(0, off - 400) : off + 400]
        for label, n in needles.items():
            if n in window and label not in hits:
                hits.append(label)
    return hits


def parse_loan_obj(mm: mmap.mmap, motif_at: int) -> dict:
    """Parse shared layout after 64 ff 2x (Sipho lock)."""
    kind = mm[motif_at + 2]
    field0 = struct.unpack_from("<I", mm, motif_at + 3)[0]
    # scan for first dup club
    loan = None
    loan_rel = None
    for rel in range(0, 64):
        a = struct.unpack_from("<I", mm, motif_at + rel)[0]
        b = struct.unpack_from("<I", mm, motif_at + rel + 4)[0]
        if a == b and 50 <= a <= 100_000 and a != PARENT:
            loan = a
            loan_rel = rel
            break
    # bytes before motif
    pre4 = mm[motif_at - 4 : motif_at].hex() if motif_at >= 4 else ""
    pre8 = mm[motif_at - 8 : motif_at].hex() if motif_at >= 8 else ""
    # trailer after loan dup
    trail = None
    if loan_rel is not None:
        trail = mm[motif_at + loan_rel + 8 : motif_at + loan_rel + 16].hex()
    return {
        "kind": kind,
        "field0": field0,
        "loan": loan,
        "loanRel": loan_rel,
        "pre4": pre4,
        "pre8": pre8,
        "trail": trail,
    }


def motif_detect_filtered(
    mm: mmap.mmap,
    jobs: set[int],
    *,
    kinds: set[int],
    back_hi: int,
    require_pre4_zero: bool,
    require_loan_rel_21: bool,
    require_trail_0a00: bool,
) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for kind in kinds:
        motif = bytes((0x64, 0xFF, kind))
        pos = 0
        while True:
            j = mm.find(motif, pos)
            if j < 0:
                break
            if require_pre4_zero and j >= 4:
                if mm[j - 4 : j] != b"\x00\x00\x00\x00":
                    pos = j + 1
                    continue
            matched = None
            back = None
            for b in range(8, back_hi + 1):
                start = j - b
                if start < 0:
                    continue
                job = struct.unpack_from("<I", mm, start)[0]
                if job in jobs:
                    matched = job
                    back = b
                    break
            if matched is not None and matched not in out:
                parsed = parse_loan_obj(mm, j)
                ok = True
                if require_loan_rel_21 and parsed["loanRel"] != 21:
                    ok = False
                if require_trail_0a00 and parsed["trail"] and not parsed["trail"].startswith("0a00"):
                    ok = False
                if ok:
                    out[matched] = {
                        "kind": kind,
                        "motifAt": j,
                        "back": back,
                        **parsed,
                    }
            pos = j + 1
    return out


def millwood_hunt(mm: mmap.mmap, job: int, uid: int) -> list[str]:
    lines = []
    # 1) all 64ff2x within 256 of any job hit
    jb = struct.pack("<I", job)
    job_offs = find_all(mm, jb, limit=200)
    lines.append(f"jobHits={len(job_offs)}")
    motif_near = []
    for off in job_offs:
        window_lo = max(0, off - 64)
        window = mm[window_lo : off + 256]
        k = 0
        while True:
            i = window.find(b"\x64\xff", k)
            if i < 0:
                break
            abs_i = window_lo + i
            kind = mm[abs_i + 2] if abs_i + 2 < len(mm) else None
            rel = abs_i - off
            if -64 <= rel <= 200:
                parsed = parse_loan_obj(mm, abs_i)
                motif_near.append((off, rel, kind, parsed))
            k = i + 1
    lines.append(f"motifsNearJob={len(motif_near)}")
    for row in motif_near[:20]:
        lines.append(f"  job@{row[0]} motifRel={row[1]} kind={row[2]} parsed={row[3]}")

    # 2) uid double sites + nearby clubs / motifs
    ub = struct.pack("<I", uid)
    uid_offs = find_all(mm, ub, limit=80)
    lines.append(f"uidHits={len(uid_offs)}")
    for off in uid_offs[:30]:
        # double?
        is_double = mm.find(ub, off + 4, min(len(mm), off + 48)) > 0
        if not is_double:
            continue
        clubs = []
        motifs = []
        for rel in range(-128, 256):
            abs_off = off + rel
            if abs_off < 0 or abs_off + 3 >= len(mm):
                continue
            if mm[abs_off : abs_off + 2] == b"\x64\xff":
                motifs.append((rel, mm[abs_off + 2]))
            if rel % 4 == 0 and abs_off + 8 <= len(mm):
                a = struct.unpack_from("<I", mm, abs_off)[0]
                b = struct.unpack_from("<I", mm, abs_off + 4)[0]
                if a == b and 50 <= a <= 100_000 and a not in (PARENT, uid, job):
                    clubs.append((rel, a))
        if motifs or clubs:
            lines.append(
                f"  doubleUid@{off} motifs={motifs[:8]} clubDups={clubs[:10]}"
            )

    # 3) search Paderborn club candidates from name→dup near string
    needle = "Paderborn".encode("utf-16-le")
    pad_clubs: Counter[int] = Counter()
    for off in find_all(mm, needle, limit=40):
        for rel in range(-128, 256, 4):
            abs_off = off + rel
            if abs_off < 0 or abs_off + 8 > len(mm):
                continue
            a = struct.unpack_from("<I", mm, abs_off)[0]
            b = struct.unpack_from("<I", mm, abs_off + 4)[0]
            if a == b and 50 <= a <= 100_000:
                pad_clubs[a] += 1
    lines.append(f"Paderborn utf16-near dup clubs: {pad_clubs.most_common(10)}")

    # 4) does any Paderborn candidate appear within 8KB of Millwood job or uid?
    for cid, _n in pad_clubs.most_common(6):
        cb = struct.pack("<I", cid)
        near_job = 0
        for off in job_offs[:50]:
            chunk = mm[max(0, off - 4096) : off + 4096]
            near_job += chunk.count(cb)
        near_uid = 0
        for off in uid_offs[:20]:
            chunk = mm[max(0, off - 4096) : off + 4096]
            near_uid += chunk.count(cb)
        lines.append(f"  club {cid} nearJobHits~={near_job} nearUidHits~={near_uid}")
    return lines


def main() -> int:
    data = load_extract()
    units = {
        "FT": data["players"],
        "II": data["reserves"]["players"],
        "U19": data["u19"]["players"],
    }
    all_jobs = {int(p["jobId"]) for ps in units.values() for p in ps}
    gt_jobs = {t[3] for t in GT}

    lines = ["# T004B spike-loan-ii-u19-v2", ""]
    with BIN.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            lines.append("## verify candidate clubIds via nearby names")
            for label, cid in CANDIDATES.items():
                u16 = utf16_near_club(mm, cid)
                lp = names_near_club(mm, cid)
                lines.append(f"  {label} id={cid} utf16Near={u16} lp32Near={lp[:8]}")
            lines.append("")

            lines.append("## filter sweeps on 64ff24+26")
            configs = [
                ("raw24/26 back48", {0x24, 0x26}, 48, False, False, False),
                ("pre4=0 back48", {0x24, 0x26}, 48, True, False, False),
                ("pre4=0 loanRel21 back48", {0x24, 0x26}, 48, True, True, False),
                ("pre4=0 loanRel21 trail0a00 back48", {0x24, 0x26}, 48, True, True, True),
                ("pre4=0 loanRel21 trail0a00 back56", {0x24, 0x26}, 56, True, True, True),
                ("only26 loanRel21 back48", {0x26}, 48, False, True, False),
            ]
            for label, kinds, bhi, pre, l21, tr in configs:
                hit = motif_detect_filtered(
                    mm,
                    all_jobs,
                    kinds=kinds,
                    back_hi=bhi,
                    require_pre4_zero=pre,
                    require_loan_rel_21=l21,
                    require_trail_0a00=tr,
                )
                lines.append(f"### {label} tagged={len(hit)}")
                for unit, name, uid, job, expect, club in GT:
                    h = hit.get(job)
                    ok = ""
                    if h and expect is not None:
                        ok = "OK" if h.get("loan") == expect else f"clubMismatch got={h.get('loan')}"
                    elif h and expect is None:
                        ok = "HIT(no expect)"
                    else:
                        ok = "miss"
                    lines.append(f"  {ok} {unit} {name} job={job} {h}")
                fps = []
                for unit, ps in units.items():
                    for p in ps:
                        j = int(p["jobId"])
                        if j in hit and j not in gt_jobs:
                            if unit == "FT" and (p.get("loan") or {}).get("status") == "loanedOut":
                                continue
                            fps.append((unit, p.get("name"), j, hit[j].get("loan"), hit[j].get("kind")))
                lines.append(f"  FP count={len(fps)} sample={fps[:8]}")
                lines.append("")

            lines.append("## Millwood deep hunt")
            lines.extend(millwood_hunt(mm, 538884, 2002422274))
        finally:
            mm.close()

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
