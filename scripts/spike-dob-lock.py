#!/usr/bin/env python3
"""Lock DOB/age near person double-UID for fixture players."""

from __future__ import annotations

import json
import mmap
import struct
from datetime import date
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
SAVE = next((ROOT / "data" / "saves").glob("*.fm"))
FIXTURE = ROOT / "data" / "fixtures" / "save-players.json"
PLAYERS = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
OUT = ROOT / "tmp" / "fm-spike" / "dob-lock.txt"
PERSON_HEAD = 512 * 1024 * 1024


def decompress_head(path: Path, nbytes: int = PERSON_HEAD) -> Path:
    out_dir = ROOT / "tmp" / "fm-spike"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "dob-lock-decomp.bin"
    with path.open("rb") as f:
        head = f.read(26)
        assert head[2:6] == b"fmf." and head[25] == 3
        reader = zstd.ZstdDecompressor().stream_reader(f)
        written = 0
        with tmp.open("wb") as out:
            while written < nbytes:
                chunk = reader.read(min(8 * 1024 * 1024, nbytes - written))
                if not chunk:
                    break
                out.write(chunk)
                written += len(chunk)
        reader.close()
    return tmp


def days_since(epoch: date, dob: date) -> int:
    return (dob - epoch).days


def collect_doubles(buf: mmap.mmap, uid: int, limit: int = 8) -> list[int]:
    pat = struct.pack("<II", uid, uid)
    hits: list[int] = []
    end = min(len(buf), PERSON_HEAD)
    j = buf.find(pat, 0, end)
    while j >= 0 and len(hits) < limit:
        hits.append(j)
        j = buf.find(pat, j + 1, end)
    return hits


def scan_window(win: bytes, rel0: int, pats: dict[str, bytes]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for name, pat in pats.items():
        offs: list[int] = []
        start = 0
        while True:
            i = win.find(pat, start)
            if i < 0:
                break
            offs.append(i - rel0)
            start = i + 1
        if offs:
            out[name] = offs[:20]
    return out


def main() -> None:
    lines: list[str] = [f"save={SAVE.name}", f"fixture={len(PLAYERS)} players", ""]
    print("decompressing…", flush=True)
    tmp = decompress_head(SAVE)
    print(f"tmp={tmp} bytes={tmp.stat().st_size}", flush=True)
    by_player: dict[str, dict[str, set[int]]] = {}

    with tmp.open("rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for p in PLAYERS:
                uid = int(p["uid"])
                y, m, d = map(int, p["dob"].split("-"))
                dob = date(y, m, d)
                age = int(p["age"])
                doubles = collect_doubles(mm, uid)
                lines.append(
                    f"## {p['name']} uid={uid} dob={p['dob']} age={age} doubles={doubles[:4]}"
                )
                if not doubles:
                    lines.append("  NO doubles in PERSON_HEAD")
                    continue

                pats = {
                    "days_y1900_u32": struct.pack(
                        "<I", days_since(date(1900, 1, 1), dob)
                    ),
                    "days_excel_u32": struct.pack(
                        "<I", days_since(date(1899, 12, 30), dob)
                    ),
                    "days_unix_u32": struct.pack(
                        "<I", days_since(date(1970, 1, 1), dob)
                    ),
                    "dmy": struct.pack("<BBH", d, m, y),
                    "ymd": struct.pack("<HBB", y, m, d),
                    "ymd_be": struct.pack(">HBB", y, m, d),
                    "packed_dmy": struct.pack("<I", d | (m << 8) | (y << 16)),
                    "year_u16": struct.pack("<H", y),
                    "age_u8": bytes([age]),
                    "age_u16": struct.pack("<H", age),
                    "height_u8": bytes([p["height_cm"]]),
                    "tag_6c07": bytes.fromhex("6c07"),
                    "tag02_days_y1900": b"\x02"
                    + struct.pack("<I", days_since(date(1900, 1, 1), dob)),
                    "tag01_days_y1900": b"\x01"
                    + struct.pack("<I", days_since(date(1900, 1, 1), dob)),
                }

                dab = doubles[0]
                radius = 8192
                lo = max(0, dab - radius)
                hi = min(len(mm), dab + radius)
                win = bytes(mm[lo:hi])
                rel0 = dab - lo
                hits = scan_window(win, rel0, pats)
                by_player[p["name"]] = {k: set(v) for k, v in hits.items()}
                if hits:
                    for k, offs in sorted(hits.items()):
                        lines.append(f"  {k}: rel={offs[:12]}")
                else:
                    lines.append("  no classic DOB/age patterns in ±8KB of first double")

                blob = bytes(mm[dab : dab + 160])
                lines.append(f"  double+0..159: {blob.hex(' ')}")
                if len(blob) >= 35:
                    person_index = struct.unpack_from("<I", blob, 31)[0]
                    lines.append(f"  personIndex@+31 = {person_index}")
        finally:
            mm.close()

    try:
        tmp.unlink(missing_ok=True)
    except OSError as err:
        lines.append(f"(tmp cleanup: {err})")

    lines.append("\n## consensus offsets across players (same relative offset)")
    keys: set[str] = set()
    for m in by_player.values():
        keys |= set(m)
    for k in sorted(keys):
        sets = [by_player[n].get(k, set()) for n in by_player]
        if not sets or any(not s for s in sets):
            continue
        shared = set.intersection(*sets)
        if shared:
            lines.append(f"  SHARED {k}: {sorted(shared)[:20]}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
