---
id: T224
title: Player facts strip + Development plot polish
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T02:26:00+02:00"
started_at: "2026-09-06T02:26:00+02:00"
completed_at: "2026-09-06T02:31:00+02:00"
depends_on: []
---

# T224 — Player facts strip + Development plot polish

## Why

Loop A desk: facts strip misaligns club vs age; secondary positions should nest under primary like DOB. Development plot zooms Y to data, hides when nothing selected, over-smooths lines, and X often shows season because Load history was stamped with `season` not `gameDate`.

## Scope

**In:**

- Facts strip: vertical alignment consistency (identity + value stacks); Position = primary strong + secondary as `player-fact-sub`
- Development plot: fixed Y scale (attrs 1–20 / ability 1–200; mixed → normalize with fixed ends); always show plot frame; straighter FM-like lines (less/no cubic smooth)
- Stamp Load history with `snapshot.gameDate` (not season); X labels prefer `gameDate`, else short wall clock — not season string
- Note honesty: Progress Report pack all-time Δ still undated per point (no new RE)

**Out:** Club page redesign; packing CA-report calendar RE (T190); theme; density

## Acceptance criteria

- [x] Club/age/nation identity rows share the same vertical rhythm; secondary positions under primary
- [x] Development plot visible with empty selection; Y not auto-zoomed to series min/max
- [x] Plot lines are linear (or lightly smoothed); X uses game date when available
- [x] New Load observations store `gameDate` from snapshot; vitest if touched
- [x] One commit `T224: …`

## Progress

Shipped:

- Facts: `playerPositionParts`; position secondary as `player-fact-sub`; nation/club use value→identity stack; value `justify-content: flex-start` so age/club strong share top rhythm
- Development: fixed ATTR 1–20 / ABILITY 1–200 (mixed = per-series normalize); plot frame always; linear paths; X from `gameDate` else wall clock
- Load stamp: `deferRecordSnapshotPlayers(..., nextSnapshot.gameDate)` (was season)
- Honesty: pack/HA all-time Δ still undated point series (T190)

Verified: `vitest` product + attribute-history (22). Commit `2d8aa42`.
