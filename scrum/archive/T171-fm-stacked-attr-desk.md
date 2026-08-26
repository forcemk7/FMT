---
id: T171
title: FM stacked attribute desk top row (outfield/GK)
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T171 — FM stacked attribute desk top row (outfield/GK)

## Why

In-game outfield desk is one band: Technical+Set Pieces | Mental | Physical+GK rating. GK: Goalkeeping | Mental | Physical+Technical. A second “secondary” row broke that composition.

## Scope

- In: Single primary 3-col band with column stacks; footer Hidden/Personality/General unchanged
- Out: Role key-attr highlighting; changing attribute lists

## Acceptance criteria

- [x] Outfield: Set Pieces under Technical; GK rating under Physical in same top band
- [x] GK: Technical under Physical; Goalkeeping is col 1
- [x] No orphan secondary play row

## Progress

- `attribute-column-stack` + stretch; outfield GK rating `margin-top: auto`
- Commit: _(filled after git)_
