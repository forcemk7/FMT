#!/usr/bin/env python3
"""Quick: roster membership for loan GT names + Kasprzak/Kirsch."""
import json
from pathlib import Path

EXTRACT = Path(r"C:\Users\mrdev\Documents\Projects\.sandbox\FMT\tmp\live-0112-extract.json")
raw = EXTRACT.read_bytes()
for enc in ("utf-16", "utf-8-sig", "utf-8"):
    try:
        data = json.loads(raw.decode(enc))
        break
    except Exception:
        pass

roster = []
for unit, key in (("FT", None), ("II", "reserves"), ("U19", "u19")):
    group = (
        data.get("players") or []
        if key is None
        else (data.get(key) or {}).get("players") or []
    )
    for p in group:
        roster.append((unit, p))

needles = (
    "kaspr",
    "kirsch",
    "gorris",
    "görr",
    "risse",
    "perez",
    "pérez",
    "abbe",
    "millwood",
    "kraft",
    "davysk",
    "dunkel",
    "resvan",
    "mhlongo",
    "zetz",
    "sipho",
    "vlad",
    "braescu",
    "brăescu",
    "manole",
    "öztürk",
    "ozturk",
)
print(f"roster size={len(roster)}")
for unit, p in roster:
    n = (p.get("name") or "").lower()
    if any(x in n for x in needles) or (p.get("loan") or {}).get("status"):
        print(
            f"{unit} job={p.get('jobId')} uid={p.get('uid')} "
            f"loan={(p.get('loan') or {}).get('status')} name={p.get('name')!r}"
        )

# uid search for known gaps
want_uids = {
    2002215969: "Gorrissen",
    2002217460: "Risse",
    2002251850: "Perez",
    2002266504: "Abbe",
}
have = {int(p.get("uid") or 0) for _, p in roster}
for u, n in want_uids.items():
    print(f"uid {u} {n} in_roster={u in have}")
