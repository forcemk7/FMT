---
id: T240
title: Match experience layout, sort, loans, hide
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T20:20:00+02:00"
started_at: "2026-09-06T20:20:00+02:00"
completed_at: "2026-09-06T20:26:00+02:00"
depends_on: [T238]
---

# T240 — Match experience layout, sort, loans, hide

## Why

Cards still overlap faces/names; order wrong vs intended ladder; loaned-out peers must not compete on parent team; hide only when resolved count is 0.

## Scope

- In: Fix row layout (no face overflow); ME sort First → Res/II → Under N (high→low) → Normal aff; exclude `loanedOut` from parent cards; loan destination marks focus current; hide when resolved count on team is 0
- Out: Changing Squad desk sort; claiming Normal `0x01` load works without user verify

## Acceptance criteria

- [x] Faces/names/projected do not overlap (flex row + forced 22px faces)
- [x] Card order First → Res/II → Under N → Normal (Squad desk untouched)
- [x] Loaned-out players omitted from parent team ME competition
- [x] Hide teams with 0 resolved players on `squadTeamUid`
- [x] Tests + commit `T240: …`
- [x] Progress asks user for Normal affiliate verify help

## Progress

- Layout: flex rows, 22px faces `!important`, fixed 5-row pad, no scroller
- Sort bands updated; Under N by TeamType high→low
- Loan compete rules + tests
- **Normal `0x01` still not verified live** — need user help (see report)

Commit: `9610fd4`