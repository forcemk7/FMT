---
id: T158
title: Honest profile facts + badge layout
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T17:30:00Z
started_at: 2026-08-26T17:30:00Z
completed_at: 2026-08-26T17:35:00Z
depends_on: [T156]
---

# T158 — Honest profile facts + badge layout

## Why

Fact row showed Value/Wage/Contract as Unknown. Nation/club badges sat beside labels and overflowed into Age.

## Scope

- In: omit null facts; label on top, equal badge + name below; overflow-hidden cells
- Out: map wage/value/contract; T157

## Acceptance criteria

- [x] No Value / Wage / Contract cells when null
- [x] Nationality and Club headers align with other fact headers
- [x] Club name cannot paint over Age / DOB
- [x] Equal square PNG slots retained

## Progress

Honest conditional facts. Badge under label via `player-fact-identity`. Auto-fill grid + overflow hidden.
