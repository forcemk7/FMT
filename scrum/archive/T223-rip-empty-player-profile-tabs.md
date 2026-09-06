---
id: T223
title: Rip empty player profile tabs (keep Attributes + Development)
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T02:14:00+02:00"
started_at: "2026-09-06T02:14:00+02:00"
completed_at: "2026-09-06T02:16:00+02:00"
depends_on: []
---

# T223 — Rip empty player profile tabs (keep Attributes + Development)

## Why

Player profile still shipped GlassScout Overview / Tactical / Performance / Career chrome with mostly Unknown stubs. Loop A only needs Attributes + Development. Club page stays (improve later).

## Scope

**In:** Keep Attributes + Development only; default Attributes; delete empty-tab helpers/CSS. Club profile unchanged.

**Out:** Club redesign; theme; new RE for career/performance.

## Acceptance criteria

- [x] Player profile shows only Attributes + Development; default Attributes
- [x] Overview / Tactical / Performance / Career markup gone
- [x] Club profile still reachable / unchanged
- [x] Vitest smoke OK; one commit `T223: …`

## Progress

Ripped empty tabs + polygram/role-fit helpers. Stripped matching orphan CSS. Club page untouched. Commit `4bcd11d`.
