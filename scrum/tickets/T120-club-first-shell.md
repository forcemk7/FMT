---
id: T120
title: Club-first shell — Squad is the home screen
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T120 — Club-first shell — Squad is the home screen

## Why

GlassScout dashboard / Scout Room / Tactical Board is noise. Owner cannot focus. Old FMT loop started at **Squad**. After Load Active Save, land on one job: the managed club.

## Scope

- In: Default post-connect screen = **Squad** (not Dashboard)
- In: Sidebar nav = **Squad** + **Settings** only (hide or remove Dashboard, Tactical Board, Scout Room, Shortlist from primary nav)
- In: Keep code modules for hidden screens if cheap; do not delete Rust reader
- In: Brand chrome already says FMT — do not regress
- Out: Mentor desk, HA filters, new data fields, installer, full visual redesign system

## Acceptance criteria

- [ ] Load Active Save → user lands on **Squad** with managed-club players
- [ ] Primary nav shows only Squad + Settings (no Dashboard / Scout / Tactics / Shortlist in the main list)
- [ ] Owner can open FMT and know what screen to look at without hunting

## Notes / pointers

- `src/components/fmt-app.tsx`, `app-sidebar.tsx`, `enterWorkspace`
- Old FMT tabs (Loans / Mentoring / Progress) come back only as later tickets when data exists

## Progress

_(worker fills)_
