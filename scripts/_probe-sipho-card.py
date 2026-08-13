#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import mmap
import os
import struct
import tempfile
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("eft", ROOT / "scripts" / "extract-first-team-fast.py")
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

UID = 2002282525
MENTAL = list(mod.MENTAL) if hasattr(mod, "MENTAL") else None


def decompress(save: Path) -> Path:
    zstd_off = int(mod.probe_container(save)["zstdOffset"])
    fd, tmp_name = tempfile.mkstemp(prefix="fmt-p-", suffix=".bin"); os.close(fd)
    tmp = Path(tmp_name); out_bytes = 0
    with save.open("rb") as f, tmp.open("wb") as out:
        f.seek(zstd_off)
        r = zstd.ZstdDecompressor().stream_reader(f)
        try:
            while True:
                try:
                    chunk = r.read(8 << 20)
                except zstd.ZstdError:
                    if out_bytes == 0: raise
                    break
                if not chunk: break
                out.write(chunk); out_bytes += len(chunk)
        finally:
            r.close()
    return tmp


def dump_card(label, buf, i):
    rec = buf[i:i+69]
    print(f"\n-- {label} off={i} --")
    print(" raw0:22", list(rec[0:22]))
    print(" disp0:22", [round(x/5) for x in rec[0:22]])
    print(" b22-24", list(rec[22:25]), "b34-35", list(rec[34:36]), "b43", rec[43])
    print(" u16", struct.unpack_from("<H", rec, 36)[0], "b23", rec[23])
    print(" atrish", mod.is_attrish(buf, i))
    # why fail?
    reasons = []
    if i+69 > len(buf): reasons.append("short")
    if rec[34] or rec[35]: reasons.append(f"nz34/35={rec[34]},{rec[35]}")
    if rec[43] != 0x01: reasons.append(f"seal={rec[43]}")
    band = sum(1 for x in rec[0:22] if 25 <= x <= 105)
    if band < 12: reasons.append(f"bandcount={band}")
    print(" fail_reasons", reasons or "none")
    if MENTAL:
        mental = {n: round(rec[i]/5) for i,n in enumerate(MENTAL)}
        print(" mental", mental)
    # try decode anyway
    try:
        d = mod.decode_attrs(rec)
        print(" decoded mental", d.get("mental"))
        print(" tech", {k:d.get("technical",{}).get(k) for k in ("penaltyTaking","technique","firstTouch")})
    except Exception as e:
        print(" decode err", e)


def main():
    save = sorted((ROOT/"data"/"saves").glob("*.fm"), key=lambda p:p.stat().st_mtime, reverse=True)[0]
    print("save", save.name)
    tmp = decompress(save)
    try:
        with tmp.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                dab = mod.collect_doubles(mm, UID)[0]
                print("double", dab, "ATTR_LOOKBACK", mod.ATTR_LOOKBACK)

                # inspect gap~6495 candidate (seal ok, det15, not attrish)
                # from prior: gap=6495 relative to 20k window ending at dab
                for look in (20_000,):
                    lo = dab - look
                    region = bytes(mm[lo:dab])
                    # find indices with det raw 75 and seal 1
                    start = 0
                    hits = []
                    while True:
                        z = region.find(b"\x00\x00", start)
                        if z < 0 or z + 35 > len(region): break
                        i = z - 34
                        if i >= 0 and z == i + 34 and i + 69 <= len(region):
                            if region[i+5] == 75 and region[i+43] == 1:
                                hits.append((len(region)-i, i))
                        start = z + 1
                    print("det15+seal hits", hits)
                    for gap, i in hits:
                        dump_card(f"gap={gap}", region, i)

                # forward scan after double
                fwd = bytes(mm[dab:dab+20_000])
                print("\nforward attrish cards:")
                for off, rec in mod._collect_attr_cards(fwd)[:20]:
                    pt = mod._ca_point_from_rec(rec, gap=off)
                    if not pt: continue
                    m = pt.get("mental") or {}
                    print(f"  fwd+{off} Det={m.get('determination')} Lea={m.get('leadership')} Cmp={m.get('composure')} u16={pt.get('snapshotU16')} b23={pt.get('b23')}")

                # count how many forward Det15
                det15f = 0
                for off, rec in mod._collect_attr_cards(fwd):
                    pt = mod._ca_point_from_rec(rec, gap=off)
                    if pt and (pt.get("mental") or {}).get("determination") == 15:
                        det15f += 1
                        m = pt["mental"]
                        print("  FWD DET15", off, m.get("leadership"), m.get("composure"), pt.get("snapshotU16"), pt.get("b23"))
                print("forward Det15 count", det15f)

                # Compare Lea of tip (3) - search any attrish with Lea=3 Det=15 anywhere in ±100k
                lo = max(0, dab - 100_000)
                hi = min(len(mm), dab + 50_000)
                blob = bytes(mm[lo:hi])
                found = []
                for off, rec in mod._collect_attr_cards(blob):
                    pt = mod._ca_point_from_rec(rec)
                    if not pt: continue
                    m = pt.get("mental") or {}
                    if m.get("determination") == 15 and m.get("leadership") in (2,3,4):
                        abs_off = lo + off
                        found.append((abs_off - dab, m.get("determination"), m.get("leadership"), m.get("composure"), pt.get("snapshotU16"), pt.get("b23")))
                print("Det15 Lea~3 within ±100k/50k:", found[:30], "n=", len(found))
            finally:
                mm.close()
    finally:
        tmp.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
