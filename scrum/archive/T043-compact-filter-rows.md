---
id: T043
title: Compact HA filter rows — value then −+ together
status: done
priority: 2
owner: worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T041]
---

# T043 — Filter chips shrink to content; ± sit after the value

## Why

**Loop:** after one-click the user nudges ~10 numeric floors. T041 put − value + inside a stepper that **grows** (`flex: 1`), so + lands on the far right of a full-width row. FM keeps value then **− +** as one cluster. User: don’t stretch the row when content doesn’t need it; spacing across the panel is fine.

## Scope

- In: Squad HA filter **row** is shrink-to-content (not 100% width). Panel may wrap / flow so several compact rows share the width
- In: Numeric cluster order: **value, then − and + together** immediately to its right, then the row’s remove. Same for Age (drop the split where − is left of the field and + is at the row end)
- Out: Ranker page. FM reorder chevrons, And toggle, trash icon. New filter logic. T042. Suggest

## Acceptance criteria

- [x] A Determination row is only as wide as key + op + value + −+ + remove — not stretched across the panel
- [x] − and + are adjacent, both immediately right of the value
- [x] Ten one-click filters can use horizontal wrap instead of ten full-bleed stacked bars
- [x] Per-row ± and footer −1/+1 / Clear All still work
- [x] AND/OR joins still readable

## Notes / pointers

- Cause: `.squad-filter-stepper { flex: 1 1 auto }` and `.squad-filter-stepper .ranker-filter-value { flex: 1 }` in `web/styles.css`; DOM is currently `minus, value, plus` (`renderSquadHaFilters` in `web/main.ts`)
- Steal FM cluster: `[value] [−] [+]` then remove. `#squad-filter-rows` / `.ranker-filter-row`
- Do not restyle HAS Ranker filters unless they share the same CSS and a one-line fix is required to keep them from breaking

## Progress

- Shipped: `#squad-filter-rows` wraps compact chips (`width: max-content`); stepper no longer `flex: 1`.
- Numeric cluster DOM is `value, −, +` then remove (Age included). Ranker CSS untouched.
- Verified: `npx vitest run tests/squad-ha-table.test.ts` (35 passed); `tsc --noEmit` clean. Footer −1/+1 / Clear All unchanged.
