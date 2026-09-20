---
id: T268
title: Dash Ability label + right trail CA/PA align
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T02:24:00+02:00"
started_at: "2026-09-07T02:24:00+02:00"
completed_at: "2026-09-07T02:27:00+02:00"
depends_on: [T267]
---

# T268 — Dash Ability label + right trail CA/PA align

## Why

Movers still say CA; ability/ME trails feel loose; main pill too wide; 2- vs 3-digit CA/PA don’t column-align.

## Scope

- In: Mover chip `CA` → `Ability`
- In: Best players/talent/ME — one right-aligned trail group; fixed compact CA/PA columns (label + tabular num)
- In: Main ability pill same fixed width (not oversized)
- Out: Personality peeks / ranking

## Acceptance

- [x] Movers show `Ability +N` not `CA +N`
- [x] Ability + ME trails right-aligned as a group; CA/PA digits column-align
- [x] Main pill fixed compact width across ability peeks
- [x] Commit `T268: …`

## Progress

- Mover: `CA` → `Ability`
- Ability/ME: single `dash-row-trail` (right-aligned); shared `--dash-capa-slot`; num in `3ch` right-aligned
- Main pill uses same slot width (tighter padding)
- Commit: `9d444e1`
