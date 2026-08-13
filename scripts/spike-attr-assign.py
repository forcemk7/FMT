"""Greedy attribute-offset assignment on aligned double-UID records."""

from __future__ import annotations

import json
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}
OUT = Path("tmp/fm-spike/attr-assign.txt")
TARGETS = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}


def extract(abs_target: int, length: int = 200) -> bytes:
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


def flat_outfield(p: dict) -> dict[str, int]:
    keys = []
    for g in ("technical", "setPieces", "mental", "physical"):
        for k, v in p["attributes"][g].items():
            keys.append((f"{g}.{k}", v))
    return dict(keys)


def assign(scale: int, region: slice, blobs, attrs_b, attrs_m) -> list:
    """Greedy: pick attrs with fewest candidate offsets first."""
    b = blobs["Patrick Bandeira"][region]
    m = blobs["Robert Müller"][region]
    base = region.start
    # candidates[attr] = list of relative offs
    cands = {}
    for k in attrs_b:
        if k not in attrs_m:
            continue
        vb, vm = attrs_b[k] * scale, attrs_m[k] * scale
        if vb > 255 or vm > 255:
            continue
        offs = [i for i in range(len(b)) if b[i] == vb and m[i] == vm]
        cands[k] = offs

    # filter impossible
    impossible = [k for k, o in cands.items() if not o]
    possible = {k: o for k, o in cands.items() if o}

    assigned = {}
    used = set()
    # greedy by scarcest
    for k in sorted(possible, key=lambda x: (len(possible[x]), x)):
        free = [o for o in possible[k] if o not in used]
        if not free:
            continue
        # prefer offs where many scarcest... just take first
        chosen = free[0]
        assigned[k] = base + chosen
        used.add(chosen)

    return assigned, impossible, {k: len(v) for k, v in cands.items()}


def main() -> None:
    lines = []
    blobs = {n: extract(a, 220) for n, a in TARGETS.items()}
    attrs_b = flat_outfield(PLAYERS["Patrick Bandeira"])
    attrs_m = flat_outfield(PLAYERS["Robert Müller"])
    attrs_s = {}
    for g in ("mental", "physical"):
        for k, v in PLAYERS["Dennis Seimen"]["attributes"][g].items():
            attrs_s[f"{g}.{k}"] = v
    # Seimen overlapping tech subset
    for k in ("freeKickTaking", "penaltyTaking", "technique"):
        attrs_s[f"technical.{k}"] = PLAYERS["Dennis Seimen"]["attributes"]["technical"][k]

    lines.append(f"outfield attrs: {len(attrs_b)}")

    for scale in (1, 5):
        for start, end, label in (
            (54, 120, "54:120"),
            (39, 120, "39:120"),
            (0, 200, "0:200"),
            (54, 200, "54:200"),
        ):
            assigned, impossible, counts = assign(
                scale, slice(start, end), blobs, attrs_b, attrs_m
            )
            lines.append(
                f"\n==== scale x{scale} region {label} "
                f"assigned={len(assigned)}/{len(attrs_b)} "
                f"impossible={len(impossible)} ===="
            )
            lines.append(f"  impossible: {impossible}")
            # verify Seimen on overlapping
            seim_ok = 0
            seim_bad = []
            sblob = blobs["Dennis Seimen"]
            for k, abs_off in sorted(assigned.items(), key=lambda x: x[1]):
                vb = attrs_b[k] * scale
                vm = attrs_m[k] * scale
                line = f"  {k}: off={abs_off} B={vb} M={vm}"
                if k in attrs_s:
                    pred = attrs_s[k] * scale
                    actual = sblob[abs_off]
                    ok = actual == pred
                    if ok:
                        seim_ok += 1
                    else:
                        seim_bad.append(k)
                    line += f" S_pred={pred} S_act={actual} ok={ok}"
                lines.append(line)
            lines.append(f"  Seimen overlap hits: {seim_ok} bad={seim_bad}")

            # How many attrs had unique candidate?
            uniq = [k for k, n in counts.items() if n == 1]
            lines.append(f"  unique-cand attrs: {uniq}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode("ascii")[:12000])
    print(f"\n... wrote {OUT}")


if __name__ == "__main__":
    main()
