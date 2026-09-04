---
id: T213
title: Diagnostics — rename, game date, load-order fields
status: done
priority: 3
owner: cursor-agent
claimed_at: 2026-09-04
started_at: 2026-09-04
completed_at: 2026-09-04
depends_on: []
---

# T213 — Diagnostics — rename, game date, load-order fields

## Why

Squad cards show `—` for age when DOB is present because in-game current date failed. Diagnostics still say “Advanced” (GlassScout) and omit the calendar date used for ages. Show every value we already collect, sorted by load order, plus an explicit in-game date.

## Scope

- In: Rename **Advanced diagnostics** → **Diagnostics**
- In: Promote live **in-game date** (`YYYY-MM-DD`) onto the snapshot (alongside existing `season`) and show it in Diagnostics
- In: Surface **all collected** connector status / snapshot diagnostic values (no cull of collected fields); order by approximate collection / load time
- Out: New RE for a save-root calendar; age-coverage invent unless already collected; redesign of pipeline / frontend-calc panels

## Acceptance criteria

- [x] Settings shows **Diagnostics** (not Advanced diagnostics)
- [x] Connected load with a readable squad current-date shows **In-game date** as `YYYY-MM-DD` (or Unavailable when missing)
- [x] Diagnostics lists collected status fields in load-order grouping; no collected status field is silently omitted
- [x] One commit `T213: …`

## Notes / pointers

- UI: `desktop/src/components/settings-screen.tsx`
- Connector: `squad_game_date` / `player_current_date` → format via `format_fm_date`; snapshot `season` already derived nearby
- CSS class renamed `advanced-diagnostics` → `diagnostics`

## Progress

- Promoted `gameDate` (YYYY-MM-DD) from player/squad current-date onto the live snapshot alongside `season`
- Renamed Advanced diagnostics → Diagnostics; ordered fields by load time; surfaced collected status/snapshot values previously missing from the panel
- Verified: `cargo check` (connector), vitest `fmt-terminal-log` (types); UI field present in Settings
- Commit: `0db0fa6`
