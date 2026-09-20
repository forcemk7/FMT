---
id: T121
title: Squad table v1 — dense readable club list
status: ready
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T120]
---

# T121 — Squad table v1 — dense readable club list

## Why

Owner needs a Live-Editor-style **list**, not cards and pulses. Old FMT Squad was a table. Make the managed squad scannable for development decisions (even before hidden attrs).

## Scope

- In: One dense table for managed-squad players from the live snapshot
- In: Columns (minimum): Name, Age, Position(s), Preferred foot, plus a small set of **visible** attrs already in the snapshot (e.g. Determination if present, or top role fit / abilityScore if already computed)
- In: Sort by column click; simple text filter by name
- In: Show skipped-slot warning from connector if present
- Out: CA/PA/HA columns (blocked until T122), mentor filters, loans split, staff, world DB index

## Acceptance criteria

- [ ] Squad screen is primarily a **table**, not a dashboard of cards
- [ ] Owner can sort and find a player by name in one screen
- [ ] Empty/error states stay honest (no fake players)

## Notes / pointers

- Data: `snapshot.players` from live connector
- Prefer reuse of existing table primitives in the UI kit; strip MyTeam card chrome if it fights density
- Modular: table component under `src/components/squad/` (or similar) so mentor desk can reuse later

## Progress

_(worker fills)_
