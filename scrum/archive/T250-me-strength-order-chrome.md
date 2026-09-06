---
id: T250
title: ME card order by team strength + status chrome
status: done
priority: 3
owner: auto
claimed_at: "2026-09-06T23:33:00+02:00"
started_at: "2026-09-06T23:33:00+02:00"
completed_at: "2026-09-06T23:36:00+02:00"
depends_on: [T249]
---

# T250 — ME card order by team strength + status chrome

## Why

After loan filter + reserves load, cards still need a “best → worst opportunity” scan and clearer current vs projected / ladder cues.

## Scope

- In: Within TeamType band (or replacing club-name secondary), order cards by a strength signal — default: max CA on the card’s same-position list (simple, no new RE)
- In: Visual distinction for focus current team vs other ladder steps (minimal CSS; no theme rewrite)
- Out: Division reputation / league avg RE unless max-CA proves useless; Squad desk

## Acceptance criteria

- [x] Stronger same-pos depth sorts left within band (or documented override)
- [x] Current team card visually distinct from projected ladder cards
- [x] Commit `T250: …`

## Progress

- Shipped: `sortMatchExperienceCards` — band then max same-pos CA; `isFocusCurrentTeam` + `.match-experience-card-current` chrome
- Verified: `npx vitest run src/domain/match-experience.test.ts` (12 passed)
- Commit: (this ticket)
