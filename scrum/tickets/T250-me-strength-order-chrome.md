---
id: T250
title: ME card order by team strength + status chrome
status: ready
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
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

- [ ] Stronger same-pos depth sorts left within band (or documented override)
- [ ] Current team card visually distinct from projected ladder cards
- [ ] Commit `T250: …`

## Progress

Ready after T249. Prefer max-CA first; reputation only if needed.
