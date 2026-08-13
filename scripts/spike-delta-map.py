"""Map double-UID +54 region via Band/Mull/Seimen attr deltas."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}
OUT = Path("tmp/fm-spike/delta-map.txt")

TARGETS = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}


def extract(abs_target: int, length: int = 256) -> bytes:
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


def flat(p: dict) -> dict[str, int]:
    out = {}
    for g, attrs in p["attributes"].items():
        for k, v in attrs.items():
            out[f"{g}.{k}"] = v
    return out


def main() -> None:
    lines = []
    blobs = {n: extract(a, 200) for n, a in TARGETS.items()}
    b = blobs["Patrick Bandeira"]
    m = blobs["Robert Müller"]
    s = blobs["Dennis Seimen"]

    fb, fm, fs = (
        flat(PLAYERS["Patrick Bandeira"]),
        flat(PLAYERS["Robert Müller"]),
        flat(PLAYERS["Dennis Seimen"]),
    )
    # Shared attr keys across outfield + overlapping with GK mental/phys/tech subset
    shared = sorted(set(fb) & set(fm) & set(fs))
    lines.append(f"shared attrs: {len(shared)}")

    # Region of interest: after 15-byte role block at +39
    # Roles: 39..53, candidate attrs from 54
    # Also scan whole 0..180

    # Build expected deltas Band->Mull for each attr
    expected = {k: fm[k] - fb[k] for k in set(fb) & set(fm)}

    lines.append("\n======== offsets whose Band-Mull delta matches an attr delta ========")
    # For each offset, compute delta, find attrs with that delta, filter by Seimen value match under identity
    candidates_by_off = {}
    for off in range(min(len(b), len(m), len(s))):
        d = m[off] - b[off]
        matched = []
        for k, ed in expected.items():
            if ed != d:
                continue
            # identity: stored byte == attr value
            if b[off] == fb[k] and m[off] == fm[k]:
                # Seimen shared?
                seim_ok = (k not in fs) or (s[off] == fs[k])
                matched.append((k, "identity", seim_ok))
            # *5
            if b[off] == fb[k] * 5 and m[off] == fm[k] * 5:
                seim_ok = (k not in fs) or (s[off] == fs[k] * 5)
                matched.append((k, "x5", seim_ok))
            # *10 if fits
            if fb[k] * 10 <= 255 and b[off] == fb[k] * 10 and m[off] == fm[k] * 10:
                seim_ok = (k not in fs) or (s[off] == fs[k] * 10)
                matched.append((k, "x10", seim_ok))
            # delta-only weak hint (same delta, wrong absolute)
            if abs(ed) >= 2:
                matched.append((k, f"delta-only(d={d})", False))
        if any(t[1] in ("identity", "x5", "x10") for t in matched):
            strong = [t for t in matched if t[1] in ("identity", "x5", "x10")]
            candidates_by_off[off] = strong
            lines.append(
                f"  +{off}: B={b[off]} M={m[off]} S={s[off]} d={d} -> {strong}"
            )

    # Delta-only: find distinctive large deltas unique to one attr
    lines.append("\n======== distinctive large deltas (unique attr) ========")
    # Unique expected deltas
    from collections import defaultdict

    by_delta = defaultdict(list)
    for k, d in expected.items():
        by_delta[d].append(k)
    unique_deltas = {d: ks[0] for d, ks in by_delta.items() if len(ks) == 1 and abs(d) >= 3}
    lines.append(f"unique |delta|>=3 attrs: {unique_deltas}")

    for off in range(min(180, len(b), len(m))):
        d = m[off] - b[off]
        if d in unique_deltas:
            k = unique_deltas[d]
            lines.append(
                f"  +{off}: d={d} maybe {k}  B={b[off]}(?{fb[k]}) M={m[off]}(?{fm[k]}) "
                f"S={s[off]}"
                + (f"(?{fs[k]})" if k in fs else "")
            )
            # Check if linear: b[off] = a*fb[k]+c
            # with same a,c for M: try a=1,c=0 already done; try a=5; try a=1,c=something
            for a in (1, 2, 3, 4, 5, 10):
                # c = B - a*fb
                c = b[off] - a * fb[k]
                if m[off] == a * fm[k] + c:
                    seim = ""
                    if k in fs:
                        pred = a * fs[k] + c
                        seim = f" Seim pred={pred} actual={s[off]} ok={pred == s[off]}"
                    lines.append(f"    LINEAR a={a} c={c}{seim}")

    # Dump aligned +39..+120 for reference
    lines.append("\n======== aligned dump +39..+120 ========")
    lines.append(f"roles+attrs labels:")
    lines.append(f"  Band: {list(b[39:120])}")
    lines.append(f"  Mull: {list(m[39:120])}")
    lines.append(f"  Seim: {list(s[39:120])}")

    # Header CA/PA guess
    lines.append("\n======== header u16 pairs (CA/PA candidates) ========")
    for name, blob in blobs.items():
        pairs = []
        for off in range(8, 28, 2):
            pairs.append((off, struct.unpack_from("<H", blob, off)[0]))
        lines.append(f"  {name}: {pairs}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    # ascii-safe print
    print(text.encode("ascii", "replace").decode("ascii"))
    print(f"\n... wrote {OUT}")


if __name__ == "__main__":
    main()
