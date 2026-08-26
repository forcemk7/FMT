---
id: T154
title: Nation/club fact-row layout
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T17:18:00Z
started_at: 2026-08-26T17:18:00Z
completed_at: 2026-08-26T17:20:00Z
depends_on: [T150]
---

# T154 — Nation/club fact-row layout

## Why

On the player desk, the nation badge sits above “Nationality” and pushes the label down. Club stays badge-left. Cause: `.player-facts > span` forces column; nation is a `span`, club is a `button`.

## Scope

- In: same horizontal badge + label/value pattern for nation and club; contain-fit sizes; no wrap on names
- Out: pack re-encode / invent sharper pixels; T153 attr colors; Squad chrome

## Acceptance criteria

- [x] Nationality label sits beside the badge (not under it) — matches Club / Wage rhythm
- [x] Club + nation names don’t wrap awkwardly in the fact cell
- [x] Nation badge uses contain (not cover crop) at a readable fact-row size

## Progress

Fixed CSS: `.player-facts > .player-nation-fact` row override; contain-fit; md badges on profile facts; nowrap ellipsis on names. Verified by specificity analysis vs screenshot. Residual: pack resolution ceiling unchanged.
