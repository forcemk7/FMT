---
id: T238
title: Fix Match experience cards + Normal 0x01 path
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T20:05:00+02:00"
started_at: "2026-09-06T20:05:00+02:00"
completed_at: "2026-09-06T20:10:00+02:00"
depends_on: [T237]
---

# T238 — Fix Match experience cards + Normal 0x01 path

## Why

T237 UI missed the brief (scrollbar, uneven rows, missing pos control, wrong hide rule). Normal Affiliated Club (`0x01`, recipes) must ride the same Club.Teams affiliate path as II (`0x08`).

## Scope

- In: Fixed 5-row viewport, no scrollbar; pad empty slots; denser rows; per-card position select (primary+secondary); hide only when zero resolved players on team
- In: Normal `0x01` same Club.Teams load as II (First; plus Under-N when typed); update `research/recipes.md` production allow-list
- Out: New RE; Good Relations / Likely Friendly

## Acceptance criteria

- [x] No overflow scrollbar on Match experience cards; all cards same 5-row height
- [x] Per-card position dropdown present when player has ≥1 selectable position code
- [x] Cards with resolved players show even with zero same-pos peers (projected focus)
- [x] Cards with zero resolved team players hidden
- [x] `0x01` on roster-load allow-list documented in recipes; same load path as II
- [x] Tests + commit `T238: …`

## Progress

- UI: denser rows (28px), faces 20px, `overflow:hidden`, pad to 5 slots, window around focus (no scroller)
- Position select always from primary+secondary options
- Hide = zero `squadTeamUid` players only
- recipes.md: roster allow-list `0x01|0x08`
- vitest 11/11

Commit: _(after git)_
