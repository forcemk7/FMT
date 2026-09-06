---
id: T231
title: U19 profile Club shows team shortName
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T04:20:00+02:00"
started_at: "2026-09-06T04:20:00+02:00"
completed_at: "2026-09-06T04:32:00+02:00"
depends_on: [T230]
---

# T231 — U19 profile Club shows team shortName

## Why

After T229/T230, U19 player profiles still do not show expected team shortName (`Schalke 04 U19`). Loop A desk Club fact must distinguish FT / U19 / II.

## Scope

**In:**

- Ensure load populates `clubTeams.shortName` (read `team+0x20`; if empty, derive from full team name by stripping legal-form prefix only)
- Profile `playerTeamDisplayName` always returns short-form (never `FC …`, never TeamType labels)
- Vitest covering U19 full→short derivation

**Out:** Club-level nickname RE; changing squad tab TeamType labels

## Acceptance criteria

- [x] U19 profile Club prefers `Schalke 04 U19`-style short form when team full/short is available
- [x] Never shows `First Team` / `U19` / `Under 19s` as Club fact
- [x] Tests + one commit `T231: …`

## Progress

Shipped: load fills `shortName` via `team+0x20` or derive from full name by stripping one legal-form prefix (`FC …` → short). Profile normalizes the same way so U19 shows `Schalke 04 U19` even when memory short is empty/full-form. Load labels log `short=`. Vitest 45 + Rust strip/resolve ok.

Commit SHA after commit.
