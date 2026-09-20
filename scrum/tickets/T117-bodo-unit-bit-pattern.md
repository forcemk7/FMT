---
id: T117
title: Bodø — UniqueID bit-pattern hunt Senior vs 2 vs U19s
status: frozen
priority: 1
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T114]
---

# T117 — Bodø — UniqueID bit-pattern hunt Senior vs 2 vs U19s

## Why

Generic extract is club → **team** → player UniqueIDs, not `+488` names. Bodø is the clean contrast: FM Senior **22** (includes Faye Lund), `+488` has **21** of those names + **10** common-name dups + **2** Reserve + **1** U19. Lund’s **id is known and absent from the blob**. Sunday / Hammadou / Bro Hansen ids are known and **in** the blob as other units. Diff those records; the unit field should pop.

T115 (blocked, do not steal): Santos club `.dat` intern list = 32 at-club (not the 10 most outbound). Reuse that **club → `.dat` → UniqueIDs** path here as the first probe, then split units.

## Scope

- In: Working copy `data/saves/gameDate5.fm` only (T109). Club id **1293**, native `00950e01`, gameDate 2025-03-24
- In: Hunt **bit patterns / object fields** that separate gold UniqueIDs into `senior` | `reserve` (Bodø/Glimt **2**) | `u19` (Bodø/Glimt **U19s**)
- In: Dump `tmp/identity/t117-*.txt` (offsets, hex windows, candidate fields). Not committed
- In: If a structural recipe recovers the **22 Senior IDs including Lund** and **excludes** the 3 other-unit IDs — unittest + fixture (ids in tests, not product law)
- Out: Santos / T115 claim. UI. HA/CA. Shipping Squad as Senior. Filtering `+488` names into units
- Out: World-scan every person in the save as the shipped path. Walk **up** from these 25 ids to club/team, or **down** from club `.dat` / team objects

## Blind

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live SI `games/`
- Do **not** treat names as the lock. IDs are the lock
- Do **not** call `+488` Senior. It is 21 senior names + dups + 2 + U19, **without Lund**
- Do **not** steal T115 (`blocked`, owner cursor-worker)

## Contrast (use all three)

| Role | Why it splits bits |
|------|-------------------|
| **Lund** `53124625` | Senior, **not** in `+488`. Control: Senior list ≠ namelist |
| **Haikin** `58123343` (or any other Senior) | Senior, **is** in `+488`. Same unit as Lund, different namelist membership |
| **Sunday** `2000387266` + **Hammadou** `2000520923` | Bodø/Glimt **2**. In `+488`. Two samples of the same unit |
| **Bro Hansen** `2000448428` | Bodø/Glimt **U19s**. In `+488`. One sample of a third unit |

Sunday and Hammadou must share a pattern Lund/Haikin do not. Bro Hansen must differ from both Senior and 2. Lund and Haikin must share Senior.

## Probe order (cheap first)

1. Replay T115 club UniqueID → `.dat` (`tad.`) packed intern list on **1293**. Count? Is Lund in? Are the 3 out? Dump
2. Person doubles for all **25** gold u32s (T115: `02 40` + intern + uid||uid). Align records
3. Side-by-side hex: Lund | Haikin | Sunday | Hammadou | Bro Hansen (same window size)
4. Search team name bytes near those hits: `Bodø/Glimt 2`, `Bodø/Glimt U19s`, `Bodø/Glimt` (catalog noise exists — require a **player id** next to the team object)
5. Candidate field must be **constant on all 22 Senior** and fail on the 3 others — not a one-id offset

## Acceptance

- [ ] Dump covers all **25** UniqueIDs (22 Senior + 2 + 1 U19)
- [ ] Side-by-side windows for Lund, one other Senior, both 2s, U19
- [ ] Either: structural recipe → **22 Senior IDs including Lund**, **0** of {Sunday, Hammadou, Bro Hansen} in that Senior set — unittest when save present
- [ ] Or: `blocked` with what bits were same/different and which ids missed — not a fitted name filter
- [ ] One commit `T117: …` on `FMT/` if a lock shipped; blocked dump still syncs STATUS, no fake Senior UI

## Gold — gameDate5

### senior (22) — FM Senior Squad Players, owned at club, 0 outgoing

| UniqueID | Name | In +488? |
|----------|------|----------|
| 53059187 | Haitam Aleesami | yes (H. Aleesami) |
| 53181436 | Sondre Auklend | yes (S. Auklend) |
| 2000170102 | Daniel Bassi | yes (D. Bassi) |
| 2000029953 | Magnus Bech Riisnæs | yes (M. Bech Riisnæs) |
| 53099570 | Patrick Berg | yes (+ P. Berg dup) |
| 53109980 | Fredrik Bjørkan | yes (+ F. Bjørkan dup) |
| 53126894 | Odin Bjørtuft | yes (+ O. Bjørtuft dup) |
| 53172074 | Ole-Didrik Blomberg | yes (O. Blomberg) |
| 53113893 | Sondre Brunstad Fet | yes (S. Brunstad Fet) |
| 53145323 | Håkon Evjen | yes (+ H. Evjen dup) |
| **53124625** | **Julian Faye Lund** | **no** |
| 53125231 | Jostein Gundersen | yes (+ J. Gundersen dup) |
| 58123343 | Nikita Haikin | yes |
| 53136627 | Jens Petter Hauge | yes (J. Hauge) |
| 53112786 | Andreas Helmersen | yes (A. Helmersen) |
| 27119248 | Kasper Høgh | yes (+ K. Høgh dup) |
| 27143633 | Anders Klynge | yes (A. Klynge) |
| 53175941 | Isak Määttä | yes (+ I. Määttä dup) |
| 53167502 | August Mikkelsen | yes (+ A. Mikkelsen dup) |
| 2000026184 | Villads Nielsen | yes (V. Nielsen) |
| 53060905 | Ulrik Saltnes | yes (+ U. Saltnes dup) |
| 29240358 | Fredrik Sjøvold | yes (+ F. Sjøvold dup) |

### reserve — Bodø/Glimt 2

| UniqueID | Name |
|----------|------|
| 2000387266 | Gift Sunday |
| 2000520923 | Isak Hammadou |

### u19 — Bodø/Glimt U19s

| UniqueID | Name |
|----------|------|
| 2000448428 | Mikkel Bro Hansen |

## Notes

- T115 script/dump: `scripts/lock-santos-three-status.py`, `tmp/identity/t115-santos-three-status.txt`, `tests/fixtures/t115-santos-gold.json`
- Identity: `scripts/extract-managed-team.py`. Do not revive T108/T110/T111 as success
- T116 stays blocked (loan-status replay). This ticket is **unit** bits, not pink/blue
- Owner count: in-game 22 including Lund; FMT 34 = 21 senior strings + 10 dups + 3 other-unit

## Progress

_(worker fills)_
