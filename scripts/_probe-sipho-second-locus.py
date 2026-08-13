#!/usr/bin/env python3
"""Hunt Det=15 near Sipho double: OOB gaps, raw mental scans, compare 07.11."""
from __future__ import annotations

import importlib.util
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "eft", ROOT / "scripts" / "extract-first-team-fast.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

UID = 2002282525
NAME = "Sipho Sithole"


def decompress(save: Path) -> Path:
    container = mod.probe_container(save)
    zstd_off = int(container["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-probe-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)
    out_bytes = 0
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zstd_off)
        reader = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    chunk = reader.read(8 * 1024 * 1024)
                except zstd.ZstdError:
                    if out_bytes == 0:
                        raise
                    break
                if not chunk:
                    break
                out.write(chunk)
                out_bytes += len(chunk)
        finally:
            reader.close()
    return tmp


def scan_save(label: str, save: Path) -> None:
    print(f"\n######## {label}: {save.name}")
    tmp = decompress(save)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                doubles = mod.collect_doubles(mm, UID)
                print("doubles", doubles)
                for dab in doubles:
                    # Wider lookback than ATTR_LOOKBACK
                    for look in (mod.ATTR_LOOKBACK, 80_000, 200_000):
                        lo = max(0, dab - look)
                        window = bytes(mm[lo:dab])
                        cards = mod._collect_attr_cards(window)
                        det15 = []
                        for off, rec in cards:
                            gap = len(window) - off
                            pt = mod._ca_point_from_rec(rec, gap=gap)
                            if not pt:
                                continue
                            det = (pt.get("mental") or {}).get("determination")
                            if det == 15:
                                det15.append(
                                    (
                                        gap,
                                        (pt.get("mental") or {}).get("leadership"),
                                        (pt.get("mental") or {}).get("composure"),
                                        pt.get("snapshotU16"),
                                        pt.get("b23"),
                                    )
                                )
                        print(f"  look={look} cards={len(cards)} Det15={len(det15)}")
                        for row in det15[:10]:
                            print("   ", row)

                    # Raw scan: mental Det byte = 15*5=75 at offset+5 of attrish cards,
                    # also count potential mental starts very near double (gap<2500)
                    lo = max(0, dab - 20_000)
                    region = bytes(mm[lo:dab])
                    near_hits = []
                    start = 0
                    while True:
                        z = region.find(b"\x00\x00", start)
                        if z < 0 or z + 35 > len(region):
                            break
                        i = z - 34
                        if i >= 0 and z == i + 34:
                            gap = len(region) - i
                            # mental[5] raw
                            det_raw = region[i + 5]
                            det = round(det_raw / 5) if det_raw % 5 == 0 else None
                            seal_ok = region[i + 43] == 0x01 if i + 43 < len(region) else False
                            attrish = mod.is_attrish(region, i) if i + 69 <= len(region) else False
                            if det == 15 or (gap < 2505 and seal_ok):
                                near_hits.append(
                                    (gap, det, det_raw, seal_ok, attrish, region[i + 23] if i+23 < len(region) else None,
                                     struct.unpack_from("<H", region, i + 36)[0] if i+38 <= len(region) else None)
                                )
                        start = z + 1
                    print(f"  near-double / Det15 raw hits ({len(near_hits)}):")
                    for h in near_hits[:40]:
                        print("   ", h)

                    # personality pack near this double?
                    pack = mod.find_mental_trait_pack(mm, doubles)
                    print("  mental pack", pack[1] if pack else None, pack[0] if pack else None)
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    saves = sorted(
        (ROOT / "data" / "saves").glob("*.fm"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # latest + previous november date
    for save in saves[:2]:
        scan_save(save.name.split("date ")[-1][:10], save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
