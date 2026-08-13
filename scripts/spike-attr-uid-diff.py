"""Diff bytes after UID in name-colocated person records across 3 players."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
PLAYERS = json.loads(
    Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
)
OUT = Path("tmp/fm-spike/attr-uid-diff.txt")


def stream_blocks():
    with SAVE.open("rb") as f:
        f.seek(26)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    b = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    break
                if not b:
                    break
                yield b
        finally:
            reader.close()


def find_person_blob(uid: int, name: str, after: int = 256) -> tuple[int, bytes] | None:
    """Return (abs_off, bytes starting at uid) for a name-colocated record."""
    uid_b = struct.pack("<I", uid & 0xFFFFFFFF)
    name_b = name.encode("utf-8")
    needle = struct.pack("<I", len(name_b)) + name_b
    abs_base = 0
    carry = b""
    for block in stream_blocks():
        data = carry + block
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            abs_off = abs_base - len(carry) + i
            # require late DB region and uid behind name
            behind = data[max(0, i - 160) : i]
            if abs_off > 1_000_000_000 and uid_b in behind:
                # find last uid before name in this behind region
                j = behind.rfind(uid_b)
                uid_abs = abs_off - (len(behind) - j)
                # gather from uid in full data
                uid_in_data = i - (len(behind) - j)
                blob = data[uid_in_data : uid_in_data + after]
                if len(blob) >= after:
                    return uid_abs, blob
            start = i + 1
        abs_base += len(block)
        carry = data[-400:]
    return None


def main() -> None:
    blobs = {}
    lines = []
    for p in PLAYERS:
        hit = find_person_blob(p["uid"], p["name"], after=320)
        if not hit:
            lines.append(f"{p['name']}: NOT FOUND")
            continue
        abs_off, blob = hit
        blobs[p["name"]] = (p, abs_off, blob)
        lines.append(f"\n{p['name']} uid_abs={abs_off} det={p['det']} lea={p['lea']}")
        lines.append(blob.hex(" "))
        lines.append(str(list(blob[:160])))

    # Compare offsets 0..159: for each offset, collect values across players
    if len(blobs) == 3:
        names = list(blobs.keys())
        lines.append("\n==== offset candidates matching each player's det ====")
        for off in range(0, 256):
            vals = []
            ok_det = True
            ok_lea = True
            for n in names:
                p, _, blob = blobs[n]
                if off >= len(blob):
                    ok_det = ok_lea = False
                    break
                v = blob[off]
                vals.append(v)
                if v != p["det"]:
                    ok_det = False
                if v != p["lea"]:
                    ok_lea = False
            if ok_det:
                lines.append(f"  DET offset +{off}: values={vals}")
            if ok_lea:
                lines.append(f"  LEA offset +{off}: values={vals}")

        # Also det/lea as u16le at aligned offsets
        lines.append("\n==== u16le det/lea candidates ====")
        for off in range(0, 250):
            dets = []
            leas = []
            for n in names:
                p, _, blob = blobs[n]
                dets.append(struct.unpack_from("<H", blob, off)[0])
                leas.append(struct.unpack_from("<H", blob, off)[0])
            if all(d == blobs[n][0]["det"] for n, d in zip(names, dets)):
                lines.append(f"  DET u16le +{off}: {dets}")
            if all(l == blobs[n][0]["lea"] for n, l in zip(names, leas)):
                lines.append(f"  LEA u16le +{off}: {leas}")

        # If Seimen has full attrs, score offsets where Seimen matches each attr value
        seimen = blobs["Dennis Seimen"][0]
        if "attributes" in seimen:
            lines.append("\n==== Seimen attr value offsets in his blob ====")
            flat = []
            for g, attrs in seimen["attributes"].items():
                for k, v in attrs.items():
                    flat.append((f"{g}.{k}", v))
            sblob = blobs["Dennis Seimen"][2]
            for label, v in flat:
                offs = [i for i, b in enumerate(sblob) if b == v]
                lines.append(f"  {label}={v}: offs={offs[:20]}")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
