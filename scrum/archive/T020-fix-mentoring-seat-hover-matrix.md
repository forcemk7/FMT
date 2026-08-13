---
id: T020
title: Fix dense Mentoring seat attr hover matrix
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T02:58:00+02:00
started_at: 2026-08-13T02:59:00+02:00
completed_at: 2026-08-13T03:05:00+02:00
depends_on: [T018, T019]
---

# T020 — Fix dense Mentoring seat attr hover matrix

## Why

**Loop break (behavior):** Dense Mentoring attr×player matrix on seat hover no longer appears (noticed especially on Dynamics-complete groups). Without hover attrs, user cannot check Det/influence feedback on the board — T018 regression.

## Scope

- In: restore reliable seat-hover matrix (column highlight) for dense cards; keep click → Dynamics modal
- Out: Dynamics extract; picker chrome; group Dynamics mega-modal; T014

## Acceptance criteria

- [x] Dense Mentoring: hovering a seat shows the attr matrix tip (not off-screen / instant-dismiss)
- [x] Hovered player column still highlighted
- [x] Click seat still opens Dynamics modal
- [x] Works whether Dynamics are missing / partial / complete

## Progress

- Shipped: tip position uses real size after reflow + fallback when measure is 0×0 (was parking matrix off-screen, worst on right-column seats); rAF re-position; short hide delay; tip z-index 10000; re-attach if detached; drop native `title` clash; `attrUi: seat-hover-v2`.
- Verified: code-path review of `positionMetricTip` / `wireMentoringMatrixTip` / dense seat wiring; click → Dynamics unchanged; no extract edits.
- Residual: confirm in UI on a Dynamics-complete group after refresh.
