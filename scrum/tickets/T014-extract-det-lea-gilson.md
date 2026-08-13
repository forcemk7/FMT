---
id: T014
title: Extract Det and Lea for Gilson-class players so combo and Mentoring work
status: blocked
priority: 1
owner: auto
claimed_at: 2026-08-12T21:12:00Z
started_at: 2026-08-12T21:15:00Z
completed_at: null
depends_on: [T013]
---

# T014 — Extract Det and Lea for Gilson-class (recent signings / no CA history)

## Why

**Loop break (behavior):** After T013, Domenico Gilson shows **Unknown personality** and cannot sit in Mentoring — FM **Light-Hearted / Evasive, Reserved**, Det=**14**, Lea=**16**, HA pack OK. **User: Gilson is a recent signing** → empty Progress Report CA history (`hist=0`) is expected, not exotic. Det/Lea must be readable **without** a CA tip strip or Mentoring stays broken for every new signing.

Prior RE (same ticket): Det/Lea are not in the 8-byte HA pack; lookback only finds a foreign wiped Det20/Lea3 decoy; product must not invent 14/16 and must not keep poisoning from rejected cards.

## Scope

- In: **RE + wire** a layout lock for current Det/Lea when `build_ca_history` is empty (recent-signing / Gilson-class)
- In: Gilson extract Det=14 Lea=16; card = Light-Hearted × Evasive, Reserved; Mentoring can seat him
- In: stop applying rejected foreign CA decoys as live mental when tip is missing
- Out: Dynamics; FM personality strings; inventing Det/Lea; waiting for a save where Gilson already has history

## Acceptance criteria

- [x] Layout lock (or equivalent fixture) documents where Det/Lea live for hist=0 players — **negative lock** shipped (`data/fixtures/det-lea-hist0-gilson-locked.json`); positive locus **not found**
- [ ] Gilson extract has Det=14 and Lea=16 after re-ingest
- [ ] Squad card is not “Unknown personality”
- [ ] Mentoring Suggest may include Gilson
- [x] Rejected/wiped lookback cards never become live Det/Lea when tip is absent
- [ ] Regression locks Gilson-class (hist=0 + pack present → Det/Lea)

## Notes / pointers

- UID `2002200653`; doubles `[124409164, 251577995]` on `tmp/live-0112-decomp.bin`
- Prior Progress below — resume from miss list; compare a long-tenured FT mate with hist>0 vs Gilson hist=0 for A/B locus
- Prefer pure “same attrs, first CA tip appears after months” if a later save exists — optional, not a blocker

## Blockers

**Positive Det/Lea locus for hist=0 not present in locked encodings on `live-0112-decomp.bin`.**

Exhaustive miss (see fixture):
- No Gilson-owned attrish Det14/Lea16 CA card within ±5MB of person double
- Late-file `det|lea|0x80` table is Muller-only (0 hits for Gilson uid/iid)
- Classic staff-order HA pack with Det: 0 hits
- Pack trailer / fixed dab offsets / raw u8 mental / capa-follow: no shared geometry with tip players

FM GT Det14/Lea16 is real, but those bytes are not in the career-save CA encodings we lock today. Cannot invent 14/16.

**User/SM action:** encoding hint, Genie/RAM dump of Gilson current attrs object, or a save moment where Gilson’s first CA tip strip appears so we can A/B the birth locus (still optional per SM, but we have no other anchor).

## Progress

**Prior RE (blocked era — keep):**

1. HA pack OK; Det/Lea not in pack.
2. hist=0 on dated saves (now explained: recent signing).
3. Foreign wiped Det20/Lea3 decoy rejected; no tip; product still used decoded → poison.
4. Exhaustive miss in then-known encodings near person/pack/name/iid.

**This run (pre-31.01):**

1. A/B hist>0 vs Gilson: tip Det/Lea live only in CA *5 cards; no shared dab/pack/capa relative offsets.
2. Whole-neighborhood owner scan: 0 Gilson-owned d14/l16 cards.
3. Late-file / classic pack / soft fuzzy: miss.
4. Negative lock fixture + decoy poison fix shipped; positive locus still missing.

**2026-08-13 probe — newest save `31.01.2040` (user: acquired 03.01.2040; Det14/Lea16; no progression):**

- File: `data/saves/FC Schalke 04 - … (In-game date 31.01.2040).fm` → `tmp/live-3101-decomp.bin`
- Doubles `[124416853, 249306415]`; pack still Ada14 Amb15 Loy15 Pre18 Pro16 Spo16 Tem13 Con5 @ 249305892
- **hist=0**, lookback **cards=0**, scored=None (no Det20 decoy in window either)
- ±5MB of person double: 11 attrish Det14/Lea16 cards, **0 owned by Gilson UID**
- Same class as 01.12.2039: FM attrs real, not in locked CA encodings for hist=0 players

**Not shipped:** positive Det/Lea locus still unknown.

**Also shipped earlier on T014:** poison stop (`rejected`+empty tip → Det/Lea null); fixture `data/fixtures/det-lea-hist0-gilson-locked.json`.
