---
id: T034
title: INCIDENT — squad filter ghost, missing DET/LEA floors, overlay
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T15:45:00Z
started_at: 2026-08-13T15:45:00Z
completed_at: 2026-08-13T15:55:00Z
depends_on: [T033]
---

# T034 — One-click filter must match the table

## Why

T033 shipped. Behavior: Filter badge stays at 1 after clearing; click Gabor (Det 18) still shows Radović (Det 16); filter popover covers PRE–HAS so floors cannot be checked against numbers.

## Scope

- In: Opening Filter with zero rows must not insert a ghost filter
- In: Clear / remove-last resets badge to 0 and shows the full unit
- In: One-click writes DET and LEA floors from the same numbers as the columns
- In: Filter editor docks above the table (not an overlay on cells)
- Out: Suggest; T014; new columns

## Acceptance criteria

- [x] Empty filters → badge hidden, full unit listed
- [x] Click Gabor-class kid hides Radović-class Det 16
- [x] Filter rows do not cover PRE–HAS cells
- [ ] User verifies on Schalke save

## Progress

Shipped: Filter open no longer inserts a ghost personality row. Clear / remove-last zeros the badge and selection. One-click still writes DET+LEA floors (Gabor 18 vs Radović 16 unit test). Filter editor is an in-flow panel above the table, not an overlay. `npx vitest run tests/squad-ha-table.test.ts` — 13 passed.

## Blockers

User verify on Schalke save.
