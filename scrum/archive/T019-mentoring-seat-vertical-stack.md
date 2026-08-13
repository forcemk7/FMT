---
id: T019
title: Mentoring seat cards stack face / name / info vertically
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T01:49:00+02:00
started_at: 2026-08-13T01:50:00+02:00
completed_at: 2026-08-13T01:55:00+02:00
depends_on: [T018]
---

# T019 — Mentoring seat cards stack face / name / info vertically

## Why

**Loop break (behavior):** Post-T018 seats are wide but still **horizontal** (tiny face left, name truncated: “Patrick …”, “Josef T…”). User: with this card size, **stack image → name → info vertically** so names truncate less and faces are more prominent — still the name-first scan job.

## Scope

- In: Mentoring member seat layout = vertical stack (larger face, fuller name, de-emphasized Dynamics line)
- In: keep T018 hover matrix + column highlight + click → dynamics modal
- Out: Dynamics extract; chip walls; T014; changing group grid column count unless required for vertical seats

## Acceptance criteria

- [x] Dense Mentoring: each seat is vertical (face above name above status)
- [x] Names show more characters than post-T018 horizontal truncation (spot-check Patrick Bandeira / Josef Tusjak readable enough to identify)
- [x] Face larger / more prominent than horizontal strip
- [x] T018 hover/click behavior preserved
- [x] No extract changes

## Notes / pointers

- Screenshot 2026-08-13: three narrow horizontal seats per group; heavy ellipsis
- CSS `.mentoring-seat*` / dense card shell after T018

## Progress

- Shipped: `.mentoring-seat-card` → column stack (face → name → dynamics); dense face 3.35rem; names 2-line clamp (full seat width); dynamics de-emphasized.
- T018 wiring untouched (`wireMentoringMatrixTip` / click → dynamics modal).
- Bust `attrUi: seat-stack-v1` so dense cards re-render.
- Verified: CSS cascade (dense overrides card); hover/click selectors unchanged; no extract edits.
- Residual: very long names may still wrap/clamp at 2 lines; layout only.
