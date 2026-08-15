---
id: T052
title: HA table — hover tooltip for truncated cells
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T033]
---

# T052 — Truncated Name / Personality / Media show full text on hover

## Why

**Loop:** read personality HA on the club table. Name, Personality, and Media ellipsis (`Santiago Con…`, `Evasive, R…`). Unit already has a `title`. Without a tooltip you cannot confirm the combo you are filtering on.

## Scope

- In: Personalities HA table text cells that ellipsis (Name, Personality, Media) get native `title` = full string
- In: Empty `—` cells: no tooltip
- Out: Custom overlay popovers (T034). Ranker page unless it shares the same cell builder in one line. T051 (do not steal). Widening columns. Suggest

## Acceptance criteria

- [x] Hover a truncated Personality or Media cell → full label in the browser tooltip
- [x] Hover a truncated Name → full name
- [x] `—` cells do not show a tooltip
- [x] Row click ≥ filter unchanged

## Notes / pointers

- `overflow: hidden` on ellipsis cells blocks Chromium native `title`. Use the existing header `showMetricTip` when `scrollWidth` exceeds `clientWidth`.
- One fill path for Name / Personality / Media (`SQUAD_HA_ELLIPSIS_KEYS`). Not Name-only. Unit stays its own `title`.
- Empty `—` cells: no tip. Row click ≥ filter unchanged.

## Progress

Native `title` did not show (overflow clip). Fix: shared ellipsis-cell fill for Name / Personality / Media; metric tip only when the painted label is clipped. `—` has no tip. `npx vitest run tests/squad-ha-table.test.ts` — 54 passed. Did not touch T053.
