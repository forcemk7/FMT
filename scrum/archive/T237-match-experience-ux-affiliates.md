---
id: T237
title: Match experience UX + Normal affiliate rosters
status: done
priority: 2
owner: auto
claimed_at: "2026-09-06T19:31:00+02:00"
started_at: "2026-09-06T19:31:00+02:00"
completed_at: "2026-09-06T19:42:00+02:00"
depends_on: [T236]
---

# T237 — Match experience UX + Normal affiliate rosters

## Why

Polish Match experience so per-team position compares stay usable, and extend loaded clubTeams to Normal Affiliated Clubs (0x01) for the FMLE “where would they get games?” glance.

## Scope

- In: Per-card position dropdown; header `{team} {pos} {rank}` + dropdown right; fixed-height 5-row lists with focus in view; hide empty same-pos cards
- In: Load affiliation type `0x01` Normal Affiliated Club First + Under-N teams; sort Senior → Under N → 2nd/II → Aff Senior → Aff Under N
- In: Squad desk keeps excluding Normal affiliates (Match experience only)
- Out: Good Relations / Likely Friendly; logos; auto move/stay advice

## Acceptance criteria

- [x] Each Match experience card has its own position control; ranks update independently
- [x] Cards share a fixed 5-row viewport; focus player scrolled into view; empty same-pos cards hidden
- [x] Normal Affiliated Clubs load First + youth sides into `clubTeams` when present on `club+0x118`
- [x] Squad desk tabs do not list Normal (0x01) affiliates
- [x] Unit tests updated; one commit `T237: …`

## Progress

- Domain: per-team position overrides; hide empty same-pos; Match experience sort bands; fixed 5-row scroll viewport + focus `scrollIntoView`
- Rust: `is_roster_load_affiliation_type` (0x01|0x08); Normal loads First+Under-N with own clubId; II unchanged for Squad
- Squad desk filters out `affiliationType === 0x01`
- Verified: vitest match-experience 9/4; cargo lib compiles; affiliation_types unit test

Commit: _(after git)_
