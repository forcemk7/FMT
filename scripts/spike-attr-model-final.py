"""Final attr-model test: Band + Müller + Seimen (incl. GK@+44)."""

from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

import zstandard as zstd

SAVE = next(Path("data/saves").glob("*.fm"))
OUT = Path("tmp/fm-spike/attr-model-final.txt")
PLAYERS = {
    p["name"]: p
    for p in json.loads(
        Path("data/fixtures/save-players.json").read_text(encoding="utf-8-sig")
    )
}
DOUBLE = {
    "Dennis Seimen": 157471994,
    "Patrick Bandeira": 264934792,
    "Robert Müller": 279879830,
}
U16S = {
    "Dennis Seimen": [31020],
    "Patrick Bandeira": [40920, 41140],
    "Robert Müller": [38720],
}

MENTAL = [
    "aggression",
    "anticipation",
    "bravery",
    "vision",
    "decisions",
    "determination",
    "flair",
    "leadership",
    "offTheBall",
    "positioning",
    "teamwork",
    "workRate",
    "composure",
    "concentration",
]
PHYS = [
    "acceleration",
    "agility",
    "balance",
    "pace",
    "stamina",
    "strength",
    "jumpingReach",
    "naturalFitness",
]
TECH = [
    "crossing",
    "dribbling",
    "finishing",
    "heading",
    "longShots",
    "longThrows",
    "marking",
    "passing",
    "penaltyTaking",
    "freeKickTaking",
    "tackling",
    "technique",
    "firstTouch",
    "corners",
]
# GK core @ +44..+54 (11 bytes). FT+Passing appear later for GKs.
GK_CORE = [
    "aerialReach",
    "commandOfArea",
    "communication",
    "eccentricity",
    "handling",
    "kicking",
    "reflexes",
    "rushingOutTendency",
    "punchingTendency",
    "throwing",
    "oneOnOnes",
]


def fx(name: str) -> dict:
    a = PLAYERS[name]["attributes"]
    out = {
        "mental": [int(a["mental"][k]) for k in MENTAL],
        "physical": [int(a["physical"][k]) for k in PHYS],
    }
    if "setPieces" in a and "crossing" in a.get("technical", {}):
        tech = []
        for k in TECH:
            src = a["technical"] if k in a["technical"] else a["setPieces"]
            tech.append(int(src[k]))
        out["tech"] = tech
        out["kind"] = "outfield"
    else:
        out["gk_core"] = [int(a["goalkeeping"][k]) for k in GK_CORE]
        out["gk_ft"] = int(a["goalkeeping"]["firstTouch"])
        out["gk_pass"] = int(a["goalkeeping"]["passing"])
        out["gk_extra"] = {
            "penaltyTaking": int(a["technical"]["penaltyTaking"]),
            "technique": int(a["technical"]["technique"]),
            "freeKickTaking": int(a["technical"]["freeKickTaking"]),
        }
        out["kind"] = "gk"
    return out


def disp(b: bytes) -> list[int]:
    return [round(x / 5) for x in b]


def score(got, expect, tol=1):
    ok = exact = soft = 0
    for g, e in zip(got, expect):
        d = abs(g - e)
        if d == 0:
            exact += 1
            ok += 1
        elif d <= tol:
            ok += 1
            soft += d
        else:
            soft += d
    return ok, exact, soft, len(expect)


def is_attrish(b: bytes, i: int) -> bool:
    if i + 69 > len(b):
        return False
    if b[i + 34] or b[i + 35] or b[i + 43] != 0x01:
        return False
    return sum(1 for x in b[i : i + 22] if 25 <= x <= 105) >= 12


def find_u16(want: set[int]):
    found: dict[int, list[tuple[int, bytes]]] = defaultdict(list)
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
                chunk_start = abs_base - len(carry)
                for u16 in want:
                    pat = struct.pack("<H", u16)
                    start = 0
                    while True:
                        j = data.find(pat, start)
                        if j < 0:
                            break
                        if j >= 36:
                            ri = j - 36
                            if is_attrish(data, ri):
                                rec = data[ri : ri + 69]
                                if len(rec) == 69:
                                    found[u16].append((chunk_start + ri, bytes(rec)))
                        start = j + 1
                abs_base += len(block)
                carry = data[-80:]
        finally:
            reader.close()
    for u16, rows in list(found.items()):
        seen = set()
        uniq = []
        for a, r in rows:
            if a in seen:
                continue
            seen.add(a)
            uniq.append((a, r))
        found[u16] = uniq
    return found


def decode(rec: bytes, kind: str) -> dict:
    out = {
        "mental": disp(rec[0:14]),
        "physical": disp(rec[14:22]),
        "seal": (rec[22], rec[24]),
        "u16": struct.unpack_from("<H", rec, 36)[0],
        "b23": rec[23],
    }
    if kind == "outfield":
        out["tech"] = disp(rec[55:69])
        out["mid11"] = disp(rec[44:55])
    else:
        out["gk_core"] = disp(rec[44:55])
        # candidate FT/Pass in +55 block
        out["tail"] = disp(rec[55:69])
        out["raw_tail"] = list(rec[55:69])
    return out


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


def main() -> None:
    lines: list[str] = []
    lines.append("=== FINAL ATTR MODEL ===")
    lines.append(f"Mental@+0:  {', '.join(MENTAL)}")
    lines.append(f"Phys@+14:   {', '.join(PHYS)}")
    lines.append(f"Tech@+55:   {', '.join(TECH)}  (outfield)")
    lines.append(f"GK@+44:     {', '.join(GK_CORE)}")
    lines.append("display = round(byte / 5); store scale 1-100")
    lines.append("")

    want = {u for us in U16S.values() for u in us}
    rows = find_u16(want)

    summary = []
    for name, u16s in U16S.items():
        f = fx(name)
        lines.append(f"######## {name} kind={f['kind']} ########")
        best_overall = None
        for u16 in u16s:
            for abs_i, rec in rows.get(u16, []):
                d = decode(rec, f["kind"])
                mok, mex, ms, mn = score(d["mental"], f["mental"])
                pok, pex, ps, pn = score(d["physical"], f["physical"])
                if f["kind"] == "outfield":
                    tok, tex, ts, tn = score(d["tech"], f["tech"])
                    total_ok = mok + pok + tok
                    total_ex = mex + pex + tex
                    soft = ms + ps + ts
                    denom = mn + pn + tn
                    detail = f"M{mok}/{mn}({mex}ex) P{pok}/{pn}({pex}ex) T{tok}/{tn}({tex}ex)"
                    extras = {}
                else:
                    gok, gex, gs, gn = score(d["gk_core"], f["gk_core"])
                    # probe tail for passing=13, firstTouch=11
                    tail = d["tail"]
                    # find best positions for pass/ft
                    ft_hits = [i for i, v in enumerate(tail) if abs(v - f["gk_ft"]) <= 1]
                    pa_hits = [i for i, v in enumerate(tail) if abs(v - f["gk_pass"]) <= 1]
                    total_ok = mok + pok + gok
                    total_ex = mex + pex + gex
                    soft = ms + ps + gs
                    denom = mn + pn + gn
                    detail = f"M{mok}/{mn}({mex}ex) P{pok}/{pn}({pex}ex) G{gok}/{gn}({gex}ex)"
                    extras = {"ft_hits_in_tail": ft_hits, "pass_hits_in_tail": pa_hits, "tail": tail}
                # prefer near doubleUID
                dist = abs(abs_i - DOUBLE[name])
                t = (total_ok, total_ex, soft, -dist, abs_i, u16, detail, d, extras, denom, rec)
                if best_overall is None or (
                    -t[0],
                    -t[1],
                    t[2],
                    -t[3],
                ) < (
                    -best_overall[0],
                    -best_overall[1],
                    best_overall[2],
                    -best_overall[3],
                ):
                    best_overall = t

        assert best_overall
        ok, ex, soft, _negdist, abs_i, u16, detail, d, extras, denom, rec = best_overall
        pct = 100 * ok / denom
        lines.append(
            f"  BEST u16={u16} @{abs_i} rel={abs_i-DOUBLE[name]:+d} "
            f"{ok}/{denom}={pct:.0f}% exact={ex}/{denom} softL1={soft}"
        )
        lines.append(f"  {detail}")
        lines.append(f"  seal={d['seal']} b23={d['b23']}")
        lines.append(f"  mental got={d['mental']}")
        lines.append(f"  mental exp={f['mental']}")
        lines.append(f"  phys   got={d['physical']}")
        lines.append(f"  phys   exp={f['physical']}")
        if f["kind"] == "outfield":
            lines.append(f"  tech   got={d['tech']}")
            lines.append(f"  tech   exp={f['tech']}")
            lines.append(f"  mid11  got={d['mid11']} (outfield unlabeled)")
        else:
            lines.append(f"  gkcore got={d['gk_core']}")
            lines.append(f"  gkcore exp={f['gk_core']}")
            lines.append(f"  tail   got={d['tail']}")
            lines.append(f"  ft={f['gk_ft']} pass={f['gk_pass']} extras={f['gk_extra']}")
            lines.append(f"  {extras}")
            # score hypothesized FT@+63 pass@+62 (0-based within tail = +7,+8)
            if len(d["tail"]) >= 9:
                hyp = [d["tail"][7], d["tail"][8]]  # indices in +55 block
                lines.append(f"  hyp pass@+62 / ft@+63: got={hyp} exp=[{f['gk_pass']},{f['gk_ft']}]")

        summary.append((name, u16, ok, denom, ex, soft, abs_i))

    lines.append("\n======== SUMMARY ========")
    all_ok = all_den = all_ex = 0
    for name, u16, ok, denom, ex, soft, abs_i in summary:
        lines.append(
            f"  {name}: u16={u16} {ok}/{denom} ({100*ok/denom:.0f}%) "
            f"exact={ex} soft={soft} card@{abs_i}"
        )
        all_ok += ok
        all_den += denom
        all_ex += ex
    lines.append(
        f"  ALL: {all_ok}/{all_den} ({100*all_ok/all_den:.0f}%) exact={all_ex}/{all_den}"
    )

    # UniqueID / personIndex → u16 link probe
    lines.append("\n======== ID → u16 link probe ========")
    for name, u16s in U16S.items():
        uid = PLAYERS[name]["uid"]
        pidx = {"Dennis Seimen": 1790, "Patrick Bandeira": 1198, "Robert Müller": 1233}[
            name
        ]
        lines.append(f"{name}: UniqueID={uid} personIndex={pidx} u16s={u16s}")
        for u16 in u16s:
            # search coincidences
            lines.append(
                f"  u16={u16} hex=0x{u16:04X}  uid&0xFFFF={uid & 0xFFFF} "
                f"uid>>8&0xFFFF={(uid>>8)&0xFFFF} pidx={pidx} "
                f"pidx*17?={pidx*17} pidx^const?"
            )
            # check if u16 appears in double-UID record
            dbl = DOUBLE[name]
            zone = extract(dbl, 256, before=0)
            # typical double record starts with UniqueID×2
            lines.append(f"  double head: {zone[:64].hex()}")
            pat = struct.pack("<H", u16)
            lines.append(f"  u16 in double[0:256]: {zone.find(pat)}")

    # Try: scan personIndex sheet / nearby for u16
    # Also check arithmetic: Band 40920,41140; delta=220
    lines.append(
        "\n  Band u16 pair delta 41140-40920=220; maybe season/history slot ids"
    )
    lines.append(
        "  Empirically: latest attr snapshots keyed by u16 constant per player "
        "(or small rotating set). Link table TBD; proximity-to-doubleUID works."
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode("ascii"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
