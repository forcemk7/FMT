---
id: T283
title: Settings preview row visible when collapsed
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-11
started_at: 2026-09-11
completed_at: 2026-09-11
depends_on: [T282]
---

# T283 — Settings preview row visible when collapsed

## Why

Preview cells lived outside `<summary>` inside `<details>`, so the browser hid them when collapsed. Sections looked empty.

## Scope

- In: Put the 3-cell preview inside `<summary>` so it stays visible when collapsed
- In: Always fill up to 3 peeks when the section has cells (not only red/yellow)
- Out: New RE

## Acceptance criteria

- [x] Collapsed sections show a 1-row diagnostics preview
- [x] Preview uses the same cell visuals as expand
- [x] One commit `T283: …`

## Progress

Shipped. Commit after git.
