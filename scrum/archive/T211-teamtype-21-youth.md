---
id: T211
title: Club.Teams — map TeamType 21 (Youth)
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-09-04T08:40:00+02:00"
started_at: "2026-09-04T08:40:00+02:00"
completed_at: "2026-09-04T08:45:00+02:00"
depends_on: [T200, T206]
---

# T211 — Club.Teams — map TeamType 21 (Youth)

## Why

Loop A: Melbourne Victory FM shows **Youths** (15) under Club.Teams; FMT kept First only (21). Live probe: second row `teamType: 21`, roster 15, name = club → `classifiedUnit: null`, **dropped**. Unknown TeamType must not hide same-club youth.

## Scope

- In: Map `teamType` **21** → squad unit + display label **Youth** (same product role as existing 22)
- In: Unit test for 21
- Out: Melbourne NPL / Schalke II affiliates; T206 label polish; inventing other unknown enum values without live evidence

## Acceptance criteria

- [x] `squad_unit_from_team_type(21)` is `Some` (not dropped)
- [x] `team_type_display_label(21)` is `Youth` (tab when name equals club)
- [x] Live `probe:club-teams` on Melbourne: second team kept, rosterLen 15, label Youth
- [x] Vitest/cargo test for the map

## Progress

- Live dump: First `teamType:0` kept; Youth `teamType:21` roster 15 was dropped.
- Mapped `21|22` → `under19s` + label `Youth` (22 moved from `reserves` so Youth shells share the youth unit).
- Probe instrumentation: `rawClubTeamsBeforeClassify` on club-teams debug path.
- Verified: `cargo test --lib team_type_` (3 ok); live Melbourne probe → kept Youth 15 `under19s`.
- Commit: `8a1d6bd`
