---
id: T038
title: Newest save — which other recent signing got Det/Lea
status: done
owner: auto
claimed_at: "2026-08-14T10:40:00+02:00"
started_at: "2026-08-14T10:45:00+02:00"
completed_at: "2026-08-14T11:05:00+02:00"
priority: 1
depends_on: [T014]
---

# T038 — Other recent signing Det/Lea: T014 tip vs remaining hist=0

## Why

**Loop:** >= filter needs honest Det/Lea. T014 unlocked Gilson via first wiped Progress Report tip. User saw **another recent signing** with Det/Lea on the newest save — need to know if that is the same tip class (so T014 already covers it) or a different locus (do not wire extract this ticket).

## Scope

- In: Newest `.fm` under `data/saves/` (mtime)
- In: Identify which **other** recent signing (not Gilson) now has extractable Det/Lea
- In: A/B that player vs remaining **hist=0** teammates — T014 tip path (`_accept_first_wiped_progress_tip`: u16>0, in-band gap, tech wiped) **or something else**
- In: One session; document only
- Out: Extract wire / product code; Suggest; CA/PA; inventing numbers
- Out: Leave decompressed `.bin` on disk (delete after)

## Acceptance criteria

- [x] Named player + UID of the other recent signing who has Det/Lea on newest save (or explicit "none besides Gilson")
- [x] Classification: T014 tip class vs other (live card / hist>1 / decoy / unknown)
- [x] A/B table vs remaining hist=0 (pack, hist, u16, gap, wiped, live_status, Det/Lea)
- [x] No extract code change
- [x] Decompress `.bin` deleted

## Notes / pointers

- T014: Gilson UID `2002200653` Det14/Lea16 via first wiped tip on `dynamics-b.fm`; "Gilson-only tip of this class this save"
- Extract: `scripts/extract-first-team-fast.py` `_accept_first_wiped_progress_tip`
- Do not invent Det/Lea
- Probe: `scripts/_probe-t038-hist0-ab.py`
- Lock: `data/fixtures/det-lea-t038-other-signing.json`

## Progress

**Shipped:** Newest save is still `dynamics-b.fm`. Other recent signing with Det/Lea is **Lars Gabrielsen** (II, UID `2002323685`, NEWGEN) **Det=16 Lea=9** via the **same T014 first-wiped Progress Report tip** (hist=1, gap=1369 in-band, snapshotU16=36520, b23=41, technical stripped). Not a live/non-wiped CA card. T014 already covers him — no extract wire.

**A/B (FT+II+U19, 85 rows):** 2 T014-class tips (Gilson FT + Gabrielsen II); 81 live/history cards; 2 remaining hist=0 still `—` (FT uid `2002115380` name unresolved; II Christian Yao `2002424608`).

**Verified:** `python scripts/_probe-t038-hist0-ab.py` against `dynamics-b.fm` (extract exit 0). Session `fmt-*.bin` deleted (extract unlinks; Temp glob empty after). No change to `extract-first-team-fast.py`.

**Residual risk:** T014 “Gilson-only” was FT-scoped; II was the miss. Remaining hist=0 stay honest `—`. Extract `gameDate` on this file reports 2039-07-25 (unused for class).
