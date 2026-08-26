---
id: T161
title: Squad Personality column (HAS ring)
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T161 — Squad Personality column (HAS ring)

## Why

Loop A glance: Ability/Potential alone miss development personality. HAS already computed — surface it beside CA/PA.

## Scope

- In: Personality column after Potential; ring + 1-decimal HAS; color via fixed attr bands on HAS (1–20 scale)
- Out: Squad-relative percentile coloring; renaming Dashboard HAS logic

## Acceptance criteria

- [x] Squad header/rows include Personality between Potential and Details
- [x] Missing HAS shows —; mapped shows score + FM band colors
- [x] Grid layout fits without horizontal crush

## Progress

- Color = `attributeBand(has)` — HAS is already ~1–20; percentiles reserved for Dashboard Top/Bottom lists
- Commit: _(filled after git)_
