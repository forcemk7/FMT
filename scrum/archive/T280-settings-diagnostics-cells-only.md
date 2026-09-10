---
id: T280
title: Settings = diagnostics cells only
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-10
started_at: 2026-09-10
completed_at: 2026-09-10
depends_on: [T279]
---

# T280 — Settings = diagnostics cells only

## Why

Settings is a grind surface for finding flaws, not user preferences. Mixed display types (roster lists, graphics cards, score articles) fight the cell table that already works. Every section should be 100% title+status+tone cells.

## Scope

- In: Each Settings section body = diagnostics cell grid only
- In: Club.Teams → one cell per team; Graphics → one cell per pack; Scores → cells only (no card grid)
- In: Keep Load Active Save as the sole action (FM26 summary/actions), not a second content type in the grid
- Out: Editable preferences; new RE; live progressive fill

## Acceptance criteria

- [x] No roster-lens / graphics-pack / score-card grids inside section bodies
- [x] Teams, Graphics, Scores use the same cell structure as Affiliations
- [x] Section tones + optimistic floor still work
- [x] One commit `T280: …`

## Progress

Shipped: Settings bodies are cell grids only; one cell per Club.Teams entry and graphics pack; Scores as cells; Load Active Save remains the only non-cell action on FM26. Commit SHA after commit.
