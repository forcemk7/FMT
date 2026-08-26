---
id: T169
title: HAS practical band colors everywhere
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-26T21:00:00+02:00"
started_at: "2026-08-26T21:00:00+02:00"
completed_at: "2026-08-26T21:03:00+02:00"
depends_on: []
---

# T169 — HAS practical band colors everywhere

## Why

Loop A/B: HAS theoretical max (~18.3) is edit-only; attr bands on raw HAS misread elite (~15.6) as mid/upper. One absolute practical scale for every HAS score display.

## Scope

- In: `hasBand` with δ=2.5 practical range + gold `super` above; Squad Personality ring; Dashboard Top/Bottom HAS score chips
- Out: Recoloring Pro/Pre/… tooltip cells (stay attr tones); squad-relative membership of Top/Bottom lists

## Acceptance criteria

- [x] `hasBand(score)`: > practical ceiling → super; [floor_p, ceil_p] → four equal bands; below floor_p → low
- [x] Squad Personality ring uses `hasBand` (not `attributeBand`)
- [x] Dashboard HAS score chips use `hasBand` (not squad elite/poor thresholds)
- [x] Unit tests for ceiling + band boundaries

## Progress

- Constants: ceiling 495/27, offset 2.5 → practical ~3.5–15.83; gold via `--gold`
- Verified: `npm test -- --run src/domain/has-score.test.ts`
- Commit: `b0c7146`
