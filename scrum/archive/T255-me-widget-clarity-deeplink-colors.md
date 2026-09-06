---
id: T255
title: ME widget clarity + profile tab deep-link + card colors
status: done
priority: 2
owner: auto
claimed_at: "2026-09-06T23:57:00+02:00"
started_at: "2026-09-06T23:57:00+02:00"
completed_at: "2026-09-07T00:03:00+02:00"
depends_on: [T254]
---

# T255 — ME widget clarity + profile tab deep-link + card colors

## Why

Dashboard ME peek shows generic “Under 19s → First Team” without club identity; rows under-use width; click lands on Attributes; profile ME cards need stronger current vs best cues.

## Scope

- In: Club-specific from → to copy on ME dash rows
- In: Wider dash peek copy / less wasted empty column space
- In: Open player profile on Match experience tab from ME widget (peek + full view)
- In: ME cards — blue = current (if not best); neon green = best First option (including when current is best)
- Out: T253 division RE; new opportunity rules

## Acceptance

- [x] Dash row names specific clubs on both sides of the move
- [x] ME widget click → profile Match experience tab
- [x] Current / best card colors distinct (blue / neon green)
- [x] Commit `T255: …`

## Progress

- Shipped: `Club · TeamType → Club · TeamType`; peek width; `openPlayer(..., { tab })`; blue current / neon-green best (+ badges)
- Verified: vitest ME + opportunities (14)
- Commit: (this ticket)
