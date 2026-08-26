---
id: T173
title: Best-position squad labels and groups
status: done
priority: 3
owner: cursor-agent
claimed_at: 2026-08-26T22:15:00+02:00
started_at: 2026-08-26T22:15:00+02:00
completed_at: 2026-08-26T22:28:00+02:00
depends_on: []
---

# T173 — Best-position squad labels and groups

## Why

Squad desk should show the player’s **best** pitch slot at a glance (`DC (DM / MC)`), and group rows by that best slot — not by “any listed position.”

## Scope

- In:
  - From the 15-byte familiarity map: primary = max familiarity (ties kept); secondary = familiarity ≥ 15 and &lt; max
  - `positions` = primary only; `secondaryPositions` = secondary
  - Squad desk label: `DC (DM / MC)` (no scores)
  - Squad groups (GK / CBs / …) keyed off primary only
- Out:
  - Role catalogue / recruitment filter redesign
  - Changing familiarity thresholds in FM itself

## Acceptance criteria

- [x] Squad Position column shows best slot(s); secondaries (≥15, below max) in parentheses when present
- [x] Tied max familiarity shows multiple primaries (e.g. `DC / DR`)
- [x] Squad section grouping uses primary position only
- [x] Unit test covers format + grouping by best vs secondary

## Notes / pointers

- Bytes: `player + 336`, `u8[15]`, `POSITION_NAMES` in `fm26/structs.rs`
- Extract: `connector.rs` + `classify_player_positions` in `fm26/parser.rs`
- UI: `formatPlayerPositions` / `groupPlayerPosition` in `live-data.ts`

## Progress

- Shipped: primary/secondary split from familiarity bytes; squad/dashboard/profile labels; groups by best only.
- Verified: `cargo test classify_positions` (2 ok); `vitest` `product.test.ts` (8 ok).
- Commit: _(filled after git)_
