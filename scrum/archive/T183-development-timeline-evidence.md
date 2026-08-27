---
id: T183
title: Development desk = player timeline evidence
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-08-27T16:01:00+02:00"
started_at: "2026-08-27T16:05:00+02:00"
completed_at: "2026-08-27T16:10:00+02:00"
depends_on: []
---

# T183 done — Development desk = player timeline evidence

## Why

Loop A Development tab was a chart plus literacy caption. Reframed as this player’s observation notebook: what the save timeline moved, no mentoring folk physics.

## Acceptance criteria

- [x] Development tab lists history newest-first with game date (else wall-clock) and signed Δ vs prior
- [x] No Det/Pro mentoring doctrine caption
- [x] Empty / single-point states explain load→append loop
- [x] Chart/presets still work when ≥2 observations

## Progress

- Shipped: `movedFieldsBetween` / `buildAttrTimeline` / `factualHistorySummary` + Development panel timeline; vitest `attribute-history.test.ts` green
- Out of scope held: mentoring-match, claims, cohorts
- Commit: `bdb89a33000c564cf82824ffd96245efd621e9e5`
