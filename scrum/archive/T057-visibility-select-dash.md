---
id: T057
title: Progress visibility select default is -
status: done
priority: 3
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T054]
---

# T057 — Visibility select idle is `-`; window stays Recent

## Why

Show all as the idle label lies: default chips are role-mixed, not all on. User: default option `-`. Recent stays the window default.

## Scope

- In: Visibility `<select>` options `-` | Show all | Hide all. Idle / role-default / mixed → `-`. Choosing `-` restores role-default chips
- In: Window `<select>` default remains Recent
- Out: New charts. Suggest. Third visibility *mode* beyond default / all / none

## Acceptance criteria

- [x] Fresh Progress player: visibility select reads `-`; window select reads Recent
- [x] Hide all → select reads Hide all; Show all → Show all; back to `-` restores mixed/default chips
- [x] Per-attribute click still exits Show/Hide override to `-`

## Notes / pointers

- `evoVisibilitySelectValue` / `#squad-evo-visibility-select` in `web/attribute-evolution.ts`, `web/index.html`, `web/main.ts`
- `squadEvolutionAttrOverride` already has `default`

## Progress

- Visibility select: `-` (default/mixed) | Show all | Hide all. Window unchanged (Recent).
- Choosing `-` sets override `default` (role chips). Chip clicks already drop override to default, so the select follows.
- Verified: `npx vitest run tests/attribute-evolution.test.ts` (6 passed).
