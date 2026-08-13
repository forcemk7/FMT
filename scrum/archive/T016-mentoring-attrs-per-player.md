---
id: T016
title: Dense mentoring attr chips must be per-player (who owns the delta)
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T00:44:54
started_at: 2026-08-13T00:45:30
completed_at: 2026-08-13T00:47:34
depends_on: [T015]
---

# T016 — Dense mentoring attr chips must be per-player (who owns the delta)

## Why

**Loop break (behavior):** T015 made deltas visible under density, but as **one anonymous chip row** above three seats. User: “I have no clue who these attributes belong to.” Mentoring feedback is useless if Det/Pro/… can’t be tied to a named player. Screenshot 2026-08-13 post-T015: single Attr strip per card, three players below.

## Scope

- In: dense Mentoring cards — every visible attr/delta on the card is **attributable to one seated player** (label, alignment under seat, or three mini-rows). Full matrix on hover/detail may remain.
- Out: Dynamics extract; inventing new metrics; T014 Det/Lea; going back to clipped unreadability

## Acceptance criteria

- [x] With ≥6 groups, user can tell **which player** each shown Det (and other chip attrs) belongs to without opening a tip
- [x] No single unlabeled group-wide attr strip as the only on-card feedback
- [x] Hover/detail full matrix still available
- [x] Density still readable (no return to blank clipped matrix-only cards)

## Notes / pointers

- T015 archived: “compact mentee attr chips above seats” — wrong aggregation for the job
- Prefer chips **on/under each seat** (Det + key pulls) over one shared row
- `web/main.ts` mentoring card dense path; `.mentoring-cards`

## Progress

Shipped: dense (≥6) cards put attr chips **under each seat** (mentors = values; mentee = values + pull ▲/▼). Removed group-wide anonymous strip. Full matrix still on hover/focus/click per seat chips + detail modal. Verified typecheck (no new errors; pre-existing mentoring.ts EOTP only) and code-path review of `denseSeatAttrs` + fingerprint `per-seat-v1`.
