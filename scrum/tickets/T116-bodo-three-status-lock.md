---
id: T116
title: Bodø — replay three-status UniqueID lock (gameDate5)
status: frozen
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T115]
---

# T116 — Bodø — replay three-status UniqueID lock (gameDate5)

## Why

Same three statuses as T115, second native Career. Owner: **22 (22)** — Senior Squad Players **(22)**, no outgoing delta. `+488` is **34 name strings** (duplicates + extras), not those 22 UniqueIDs.

## Status law (same as T115)

| UI colour | Meaning |
|-----------|---------|
| white | owned, at club |
| pink/red | owned, out on loan |
| blue | not owned, inbound loan |

## Scope

- In: After T115 recipe exists — **replay** it on working copy `data/saves/gameDate5.fm` (T109). Do not invent a second path
- In: Classify the **22 UniqueIDs** below. Dump `tmp/identity/` (not committed)
- In: Unittest/fixture for Bodø gold (ids in tests, not product law)
- Out: Other Careers. UI ship. Fitting +488. Expanding SCOPE.md
- Out: Claiming this ticket while T115 is not `done`

## Blind

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live SI `games/`
- Do **not** treat short-name / full-name pairs as two people
- Residual: one FM crop may show **Jens Petter Hauge** `53136627` blue; the other crop lists him white. Owner count **22 (22)** = **zero outgoing**. If Hauge is inbound, gold is 21 owned + 1 inbound. Do not force all-white if the save says inbound

## Acceptance

- [ ] T115 structural recipe reused (not a Bodø-only offset)
- [ ] All 22 UniqueIDs found by **id**
- [ ] Statuses match gold (all `owned_at_club`, unless Hauge locks as `inbound_loan`)
- [ ] `owned_out_on_loan` = **empty** (matches 22=22 and no pink in FM crops)
- [ ] Dump + unittest; one commit `T116: …` on `FMT/`

## Gold — gameDate5 Bodø/Glimt

Native. FM header: Senior Squad Players **(22)**. All names white in crop 1. No pink in either crop.

| UniqueID | Name | Status |
|----------|------|--------|
| 53059187 | Haitam Aleesami | owned_at_club |
| 53181436 | Sondre Auklend | owned_at_club |
| 2000170102 | Daniel Bassi | owned_at_club |
| 2000029953 | Magnus Bech Riisnæs | owned_at_club |
| 53099570 | Patrick Berg | owned_at_club |
| 53109980 | Fredrik Bjørkan | owned_at_club |
| 53126894 | Odin Bjørtuft | owned_at_club |
| 53172074 | Ole-Didrik Blomberg | owned_at_club |
| 53113893 | Sondre Brunstad Fet | owned_at_club |
| 53145323 | Håkon Evjen | owned_at_club |
| 53124625 | Julian Faye Lund | owned_at_club |
| 53125231 | Jostein Gundersen | owned_at_club |
| 58123343 | Nikita Haikin | owned_at_club |
| 53136627 | Jens Petter Hauge | owned_at_club (confirm not inbound) |
| 53112786 | Andreas Helmersen | owned_at_club |
| 27119248 | Kasper Høgh | owned_at_club |
| 27143633 | Anders Klynge | owned_at_club |
| 53175941 | Isak Määttä | owned_at_club |
| 53167502 | August Mikkelsen | owned_at_club |
| 2000026184 | Villads Nielsen | owned_at_club |
| 53060905 | Ulrik Saltnes | owned_at_club |
| 29240358 | Fredrik Sjøvold | owned_at_club |

### +488 clue (34 strings — not the 22 UniqueIDs)

Owner lock (2026-08-17):

**10 abbreviated duplicates** of Senior (common name next to full name):

| FMT string | Same person as |
|------------|----------------|
| P. Berg | Patrick Berg |
| F. Bjørkan | Fredrik Bjørkan |
| O. Bjørtuft | Odin Bjørtuft |
| H. Evjen | Håkon Evjen |
| J. Gundersen | Jostein Gundersen |
| K. Høgh | Kasper Høgh |
| I. Määttä | Isak Määttä |
| A. Mikkelsen | August Mikkelsen |
| U. Saltnes | Ulrik Saltnes |
| F. Sjøvold | Fredrik Sjøvold |

(Owner numbered 1–9 with two “3”s; there are **10** strings. 34−10=**24**, not 25.)

**3 not Senior** — other units, owner UniqueIDs:

| FMT string | In-game | UniqueID | Unit |
|------------|---------|----------|------|
| M. Bro Hansen | Mikkel Bro Hansen | 2000448428 | Bodø/Glimt **U19s** |
| G. Sunday | Gift Sunday | 2000387266 | Bodø/Glimt **2** |
| I. Hammadou | Isak Hammadou | 2000520923 | Bodø/Glimt **2** |

**Missing from +488:** Julian Faye Lund `53124625` (Senior, in FM 22). So 24−3 extras=**21** Senior names in FMT, not 22.

Net 34 vs 22: +10 dups +3 other-unit −1 Lund.

+488 is a **name blob** that mixes Senior common/full + II + U19. Not UniqueIDs. Not Senior-only. Do not ship as Squad law.

## Notes

- Worker: claim only after T115 done. HQ will paste when unblocked
- Santos contrast: there +488 **undershot** (26 ⊂ 42). Here it **overshoots** (name blob + dups + 3 extras)

## Progress

_(worker fills)_
