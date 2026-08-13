---
id: T003
title: Mentoring seating uses dynamics{}
status: ready
priority: 4
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T002]
---

# T003 — Mentoring seating uses dynamics{}

## Why

Phase 1 close-out. Replace attr-only influence proxy with real Dynamics where available so mentoring groups won't ruin Determination for the wrong reasons.

## Scope

- In: mentoring inference + Squad Analyzer seating use `dynamics{}` when present; clear fallback if missing
- Out: Broad mentoring UX redesign; new funnel features

## Acceptance criteria

- [ ] Mentoring suggestions prefer Dynamics hierarchy/social/captaincy signals over attr-only proxy when data exists
- [ ] Manual Dynamics labels reduced or clearly marked as override-only
- [ ] Tests cover at least one dynamics-aware seating path
- [ ] Livelihood loop still works end-to-end in `npm run dev` with a local save

## Notes / pointers

- Depends on T002
- `src/inference/mentoring.ts` and related web mentoring UI
- Stay inside SCOPE.md livelihood loop

## Progress

_(worker fills)_
