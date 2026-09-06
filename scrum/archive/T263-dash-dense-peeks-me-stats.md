---
id: T263
title: Dash denser peeks, positions, ME stats, chip clip fix
status: done
priority: 2
owner: auto
claimed_at: "2026-09-07T01:35:00+02:00"
started_at: "2026-09-07T01:35:00+02:00"
completed_at: "2026-09-07T01:38:00+02:00"
depends_on: [T262]
---

# T263 — Dash denser peeks, positions, ME stats, chip clip fix

## Why

Fullscreen still scrolls peeks; ability rows need best position; ME needs age/CA/PA; Worst personality chips clip mid-pill (flex-end + overflow hidden).

## Scope

- In: Fit peeks without widget scroll — peek size 4 + smaller dash faces
- In: Best players/talent extras include best position
- In: ME extras include age, CA, PA
- In: Personality chips must not clip mid-pill
- Out: Changing widget count/order

## Acceptance

- [x] Peeks fit in viewport widgets without internal scroll (typical fullscreen)
- [x] Ability rows show best position
- [x] ME rows show age + CA + PA
- [x] Pressure/Leadership chips no longer left-clipped
- [x] Commit `T263: …`

## Progress

- `DASH_PEEK_SIZE` 4; denser peek rows + 28px faces; widget body `overflow:hidden`
- Ability: logo · teamType · position · age · secondary → main
- ME: age · CA · PA · move rail → rank
- Personality chips: no mid-pill clip (`overflow:visible`, intact flex basis)
- Commit: `437e7f6`
