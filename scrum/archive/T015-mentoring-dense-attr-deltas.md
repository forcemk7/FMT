---
id: T015
title: Mentoring cards show attr deltas when many groups densify
status: done
priority: 2
owner: auto
claimed_at: 2026-08-13T00:24:51
started_at: 2026-08-13T00:25:51
completed_at: 2026-08-13T00:31:35
depends_on: []
---

# T015 — Mentoring cards show attr deltas when many groups densify

## Why

**Loop break (behavior):** User runs **9** mentoring groups. Card grid densifies; the Attr matrix is **clipped** (names only, deltas unreadable). Cannot check Determination / influence outcomes on the board — livelihood step “build groups that won’t ruin Det” loses feedback. Earlier refuse of “compact for more groups” was polish; **steady use with many groups + unreadable attrs** is the reopen.

## Scope

- In: when mentoring cards are dense, each card still exposes usable attr/delta feedback (e.g. compact Det-focused or net-delta summary **plus** full matrix on hover and/or existing detail/edit path)
- In: with ≥6–9 groups on desktop, deltas must be readable without cropping to blank
- Out: Dynamics extract; inter-group influence art; Suggest beyond FT; media 2-row personality polish; extract Det/Lea (T014)

## Acceptance criteria

- [x] With 9 groups (or fixture-equivalent density), each card shows at least Det (and preferably key mentoring attrs) with signed deltas readable on the card **or** one-hover/one-click without leaving Mentoring
- [x] Full attr×player matrix remains available (hover tooltip and/or detail dialog) — not deleted
- [x] Empty / no-delta state still sensible
- [x] No extract/API changes

## Notes / pointers

- Screenshot 2026-08-13: 9 groups, “Attr” header + surnames, matrix body clipped
- CSS: `.mentoring-cards` 2-col + `overflow: hidden` on cards; `.mentoring-matrix`
- Prefer smallest CSS/layout + optional summary row over a redesign

## Progress

Shipped dense (≥6 groups) card UI: compact mentee attr chips (Det emphasized + pull ▲/▼) above seats; full matrix on hover/focus/click tip; detail modal matrix unchanged. Empty → “No attr data”. Verified via typecheck (no new errors; pre-existing mentoring.ts EOTP only) and code-path review of dense fingerprint + tip wiring.
