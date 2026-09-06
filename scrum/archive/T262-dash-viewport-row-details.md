---
id: T262
title: Dashboard viewport fit + ability/HAS row details
status: done
priority: 2
owner: auto
claimed_at: "2026-09-07T01:28:00+02:00"
started_at: "2026-09-07T01:28:00+02:00"
completed_at: "2026-09-07T01:31:00+02:00"
depends_on: [T261]
---

# T262 — Dashboard viewport fit + ability/HAS row details

## Why

Fullscreen should show all dash widgets without scrolling the page. Ability peeks need age; personality peeks should show full attribute names.

## Scope

- In: Dash widget grid fills viewport (3×2 flex/stretch); peeks scroll inside widgets if needed
- In: Best players/talent extras order: `{logo} {teamType} {N years old} {PA|CA}` then main `{CA|PA}`
- In: Top/Worst personality chips spell full labels (not abbr)
- Out: Changing peek count; ME chrome

## Acceptance

- [x] Fullscreen dash shows all six widgets without main scroll (when height allows)
- [x] Ability rows include age + ordered extras
- [x] Personality chips use full names
- [x] Commit `T262: …`

## Progress

- Dash grid `repeat(3, 1fr)` rows + screen/slot fill; widget bodies scroll
- Ability extras: logo · teamType · age · secondary; main CA/PA
- Personality chips: full `label value`
- Commit: `0bd396a`
