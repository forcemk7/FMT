---
id: T001
title: Lock Dynamics binary layout from ground truth
status: ready
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T007, T008, T009, T010, T011, T012, T013, T014]
---

# T001 — Lock Dynamics binary layout from ground truth

## Why

Phase 1b — **paused until T014**. Gilson Mentoring blocked by missing Det/Lea extract after T013 honesty gate.

## Scope

- In: ground truth fixtures, binary hunt near FT `listAbs` / team body, produce `dynamics-layout-locked.json` (or equivalent lock artifact)
- Out: mentoring UI wiring (T003); full loan/scouting digressions

## Acceptance criteria

- [ ] Ground truth under `data/fixtures/dynamics-ground-truth-*-wip.json` is complete enough to validate a layout
- [ ] Layout lock artifact exists and is reproducible against the A/B (or demotion) save pair
- [ ] Spike/notes document the offset/join path for the next extract wire-up
- [ ] Out-of-scope quarantine respected

## Notes / pointers

- README "Dynamics lock path"
- Prefer pure hierarchy-demotion save pair if available (`dynamics-a.fm` / `dynamics-b.fm` today may be squad-move)
- Scripts live under `scripts/spike-dynamics-*.py`; fixtures under `data/fixtures/`

## Progress

_(worker fills)_
