"""Search float32/float16 encodings of distinctive attrs near double-UID and globally."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/float-attrs.txt")
DOUBLE = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}


def extract(abs_target: int, length: int = 512) -> bytes:
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        abs_base = 0
        carry = b""
        buf = bytearray()
        end = abs_target + length
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
                if chunk_start < end and abs_base + len(block) > abs_target:
                    lo = max(0, abs_target - chunk_start)
                    hi = min(len(data), end - chunk_start)
                    already = len(buf)
                    want_from = abs_target + already
                    lo2 = max(lo, want_from - chunk_start)
                    if lo2 < hi:
                        buf.extend(data[lo2:hi])
                abs_base += len(block)
                carry = data[-64:]
                if len(buf) >= length:
                    break
        finally:
            reader.close()
    return bytes(buf)


def f32(v: float) -> bytes:
    return struct.pack("<f", float(v))


def f16(v: float) -> bytes:
    # python 3.6+ 
    return struct.pack("<e", float(v))


def main() -> None:
    lines = []
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Distinctive packs as consecutive float32
    tests = []
    for p in PLAYERS:
        name = p["name"]
        m = p["attributes"]["mental"]
        # det, lea as f32 pair
        tests.append((name, "det_lea_f32", f32(m["determination"]) + f32(m["leadership"])))
        tests.append((name, "det_lea_f16", f16(m["determination"]) + f16(m["leadership"])))
        if "naturalFitness" in p["attributes"]["physical"]:
            nf = p["attributes"]["physical"]["naturalFitness"]
            tests.append((name, "nf_f32", f32(nf)))
            tests.append((name, "det_nf_f32", f32(m["determination"]) + f32(nf)))

    # Near double-UID
    lines.append("==== floats near double-UID blobs ====")
    for name, abs_off in DOUBLE.items():
        blob = extract(abs_off, 512)
        lines.append(f"\n## {name}")
        for n, label, pat in tests:
            if n != name:
                continue
            i = blob.find(pat)
            lines.append(f"  {label} in-blob: {i} pat={pat.hex(' ')}")
            # also any offset decode as det
            det = PLAYERS[name] if False else next(p for p in PLAYERS if p["name"] == name)
            d = det["attributes"]["mental"]["determination"]
            # scan all f32
            hits = []
            for off in range(0, len(blob) - 4, 1):
                try:
                    val = struct.unpack_from("<f", blob, off)[0]
                except Exception:
                    continue
                if abs(val - d) < 1e-6:
                    hits.append(off)
            lines.append(f"  f32==det({d}) offs={hits[:20]}")

    # Global search for rare f32 pairs
    lines.append("\n==== global float pair search ====")
    # Seimen otb=1.0, flair=8.0 consecutive f32 — distinctive
    seimen = next(p for p in PLAYERS if p["name"] == "Dennis Seimen")
    rare = f32(1.0) + f32(8.0)  # otb, flair wrong order
    rare2 = f32(8.0) + f32(1.0)
    rare3 = f32(18.0) + f32(16.0)  # det,lea
    # Bandeira pen=5, Müller nf=9 as f32 alone too common
    pats = [
        ("seimen otb1_flair8", rare),
        ("seimen flair8_otb1", rare2),
        ("seimen det18_lea16", rare3),
        (
            "band conc18_dec16",
            f32(18) + f32(16),
        ),
        (
            "mull dec18_det16",
            f32(18) + f32(16),
        ),
        ("band nf16_pace17", f32(16) + f32(17)),
        ("mull nf9_pace15", f32(9) + f32(15)),
    ]

    # single pass
    hitmap = {lab: [] for lab, _ in pats}
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
                for lab, pat in pats:
                    if len(hitmap[lab]) >= 5:
                        continue
                    start = 0
                    while len(hitmap[lab]) < 5:
                        i = data.find(pat, start)
                        if i < 0:
                            break
                        abs_off = abs_base - len(carry) + i
                        if not hitmap[lab] or hitmap[lab][-1] != abs_off:
                            hitmap[lab].append(abs_off)
                        start = i + 1
                abs_base += len(block)
                carry = data[-32:]
        finally:
            reader.close()

    for lab, hits in hitmap.items():
        lines.append(f"  {lab}: n={len(hits)} {hits}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii"))
    print(f"\n... wrote {OUT}")


if __name__ == "__main__":
    main()
