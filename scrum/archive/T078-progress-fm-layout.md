---
id: T078
title: Progress starts with no chip; FM attribute columns; HA below
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-08-15
started_at: 2026-08-15
completed_at: 2026-08-15
depends_on: []
---

# T078 — Progress: empty chart until click; in-game column layout; hidden attrs below

## Why

Used Progress on Sipho: **Controversy** is pre-selected (blue chip + line). That highlight is what they look at, not CA/HA movement. Layout is five columns (Technical | Set Pieces | Mental | Physical | Personality). In-game is **three** columns; Personality is not on that screen.

## Scope

- In: Progress default = **no** attribute selected (empty chart). Click still selects for the plot. Hide all / Show all / `-` stay; idle start is none, not role-default HA chips
- In: Chip columns match FM screenshots:
  - **Outfield:** left = Technical then Set Pieces under it; middle = Mental; right = Physical
  - **GK:** left = Goalkeeping; middle = Mental; right = Physical, then the in-game Technical extras (Free Kick / Penalty / Technique)
- In: Pack HA + Controversy (hidden in FM) sit in a **separate band below** the three columns — extra, not a fifth FM column
- Out: New extract / GK–outfield 1–10 ratings unless already in the payload. T077 www. Suggest. Changing Squad HA table columns

## Acceptance criteria

- [x] Fresh Progress player: no chip selected; chart has no attribute line until a click
- [x] Outfield Progress: three columns as FM (Set Pieces under Technical, not its own column)
- [x] GK Progress: three columns as FM (Goalkeeping | Mental | Physical + short Technical)
- [x] Personality / hidden HA block is below that grid, visually separate
- [x] One git commit `T078: …` on FMT/

## Notes / pointers

- `roleDefaultEvolutionAttrs` / `squadEvolutionAttrOverride` / Hide all (`none`) in `web/main.ts`
- `evolutionCategories` in `web/attribute-evolution.ts` (today Set Pieces is its own column)
- T057: `-` restored role-default chips — start view must not restore those highlights
- Tests: `tests/attribute-evolution.test.ts`

## Progress

- Fresh player: visibility Hide all, no chips, empty chart until a click. `-` still restores role-default HA chips (T057).
- Outfield chips: Technical + Set Pieces stacked left, Mental, Physical. GK: Goalkeeping | Mental | Physical + Technical (FK/Pen/Technique).
- Pack Personality sits in a dashed extra band below the three columns (`Personality (extra)`). No GK/outfield 1–10 ratings (not in extract).
- Verified: `npx vitest run tests/attribute-evolution.test.ts` (19 passed).
