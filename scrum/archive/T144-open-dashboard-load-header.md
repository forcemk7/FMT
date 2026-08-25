---
id: T144
title: Open on Dashboard; unify Load Data in header
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25T20:25:00Z
completed_at: 2026-08-25T20:30:00Z
depends_on: []
---

# T144 — Open on Dashboard; unify Load Data in header

## Why

Loop A friction: every launch hits the GS intro card before the desk. Load already lives in the header — the splash is redundant.

## Scope

- In:
  - Skip `StartupScreen`; open workspace on **Dashboard** with empty/not-synced state
  - Merge club status chip + reload into **one** control: when not connected / no FM data → label **Load Data** (or equivalent), visually highlighted; click runs the same load as today
  - When connected → show club name + squad count (current chip content); click reloads
  - Drop the separate adjacent reload icon if the unified control covers it (Settings stays)
  - Empty Dashboard/Squad copy must still point at that header control (no second splash)
- Out: auto-connect on launch; theme redesign; Settings load duplicate removal (optional if trivial)

## Acceptance criteria

- [x] Cold start shows shell + Dashboard with no intro card
- [x] Disconnected: one highlighted header control says Load Data (or clear equivalent) and loads on click
- [x] Connected: same control shows club + squad detail; click reloads
- [x] No duplicate reload icon next to Settings unless it does a different job

## Notes / pointers

- `desktop/src/components/fmt-app.tsx` (`mode === null` → StartupScreen)
- `desktop/src/components/shell-header.tsx` (`.shell-context` + Reload button)
- Also fix UTF-8 in `globals.css` if still dirty (Turbopack panic on CP1252 dash) — stage that file if touched

## Progress

Shipped: removed StartupScreen gate; default Dashboard; unified `.shell-load` button (Load Data highlight / club+reload); LiveDataState points at header. Verified `tsc --noEmit` + globals.css UTF-8. Residual: empty-state still has a secondary Load Data button in-canvas (same action).
