---
id: T227
title: Role desks no filter; Dashboard chrome; live load pulse
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T03:13:00+02:00"
started_at: "2026-09-06T03:13:00+02:00"
completed_at: "2026-09-06T03:18:00+02:00"
depends_on: []
---

# T227 â€” Role desks no filter; Dashboard chrome; live load pulse

## Why

HoYD/GM don't need roster Status filters. Dashboard title/subtitle is redundant with shell tabs. Connected Load pill used a gold/yellow dot â€” should read as live (mint + pulse).

## Scope

**In:** HoYD/GM back to at-club pool, no Filter UI; Dashboard drop heading; shell load live-dot = mint pulse when connected

**Out:** Dash widget content; Tactic/TD; new RE

## Acceptance criteria

- [x] Connected HoYD/GM have no Filter; Loans/Squad unchanged
- [x] Dashboard has no title+subtitle row
- [x] Connected Load pill shows animated live indicator (not gold)
- [x] One commit `T227: â€¦`

## Progress

Shipped. Commit `93bb683`.

