---
id: T270
title: ME Best = no better ladder move + restore pills
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T03:17:00+02:00"
started_at: "2026-09-07T03:17:00+02:00"
completed_at: "2026-09-07T03:19:00+02:00"
depends_on: [T269]
---

# T270 — ME Best = no better ladder move + restore pills

## Why

T269 “top-2 Current = Best” wrongly keeps youth at U19. Best = stay only when no better ladder move (higher band with rank ≤2). Restore Current/Best ribbons.

## Logic (locked)

**Better move:** other card with `focusRank` in 1..2 and either `band < current.band`, or same First band with a strictly better competitive rank (or current not competitive and other is).

**Best:** if Current has any better move → best of those; else Current (stay). No current → best competitive First.

**Chrome:** stay → green + Current pill. Split → Current blue + Current pill; Best green + Best pill.

## Acceptance

- [x] Robert-style First #1: green + Current only
- [x] Youth U19 #1 with First ≤2: blue Current + green Best
- [x] Buried next step (First rank >2): stay Current green
- [x] Ribbons visible again
- [x] Tests + commit `T270: …`

## Progress

- `isMatchExperienceBetterMove` + rewritten `pickBestMatchExperienceCard`
- Ribbons: stay=`Current` (green), split=blue Current + neon Best
- Verified: 17 tests passed
- Commit: (pending)
