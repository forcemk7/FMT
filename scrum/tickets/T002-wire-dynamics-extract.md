---
id: T002
title: Wire dynamics{} into extract-first-team
status: ready
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T001]
---

# T002 — Wire dynamics{} into extract-first-team

## Why

Phase 1. Once layout is locked, extract must emit Dynamics so mentoring (and UI) can consume them.

## Scope

- In: `scripts/extract-first-team-fast.py` (and shared types if needed) emit `dynamics{}` per player/team as defined by the lock
- Out: Mentoring seating logic changes (T003); unrelated extract features

## Acceptance criteria

- [ ] Extract outputs `dynamics{}` matching the locked layout for FT (II/U19 if trivial; otherwise note follow-up)
- [ ] Fixture or regression check proves fields against ground truth
- [ ] Types / save wrappers updated if the web/dev path consumes extract JSON
- [ ] Depends on T001 lock remaining valid

## Notes / pointers

- Depends on T001
- `shared/save/` extract wrappers + types
- Keep changes minimal — only Dynamics fields needed for mentoring

## Progress

_(worker fills)_
