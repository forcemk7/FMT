---
id: T248
title: ME header TeamType first; sort by TeamType
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T22:15:00+02:00"
started_at: "2026-09-06T22:15:00+02:00"
completed_at: "2026-09-06T22:18:00+02:00"
depends_on: [T247]
---

# T248 — ME header TeamType first; sort by TeamType

## Why

Club name as title makes many “First Team” cards hard to scan. Prefer TeamType as header, club as subtitle; sort so all First Teams then Under Ns.

## Scope

- In: ME card header = TeamType; subtitle = clubName (logo stays)
- In: Sort ME cards by TeamType band (First → Res → Under N high→low), then club name
- Out: Loan byte (T245); Squad desk sort

## Acceptance criteria

- [x] Header TeamType, subtitle clubName
- [x] Cards ordered First Teams before Under Ns across clubs
- [x] Tests + commit `T248: …`

## Progress

Shipped: flip title/subtitle; sort band First → Res → Under N; within band by clubName. Verified vitest (11).

Commit: `_(fill)_`
