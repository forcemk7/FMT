---
id: T230
title: Profile Club fact must use team shortName only
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T04:07:00+02:00"
started_at: "2026-09-06T04:07:00+02:00"
completed_at: "2026-09-06T04:12:00+02:00"
depends_on: [T229]
---

# T230 — Profile Club fact must use team shortName only

## Why

User expected profile Club = team shortName (`Schalke 04`, `Schalke 04 U19`, `Schalke 04 II`). T229 fell back to `team.name`, which was historically polluted with TeamType tab labels (`First Team`, `U19`), so profiles showed the wrong vocabulary.

## Scope

**In:**

- Confirm shortName meaning: team+0x20 short display (not full `FC …`)
- `playerTeamDisplayName`: shortName only; never TeamType labels; reject type-like `name` fallbacks
- Keep tabs: managed → TeamType (`Under 19s`); affiliate → shortName

**Out:** Club-level nickname RE; inventing nicknames by stripping FC

## Acceptance criteria

- [x] Profile Club never shows `First Team` / `U19` / `Under 19s` as the club line when shortName exists
- [x] Profile prefers shortName; does not fall back to TeamType-looking strings
- [x] Vitest; one commit `T230: …`

## Progress

User understanding of shortName is correct (entity-map: `Schalke 04 U19`). Bug was profile falling back to polluted `name` (TeamType strings). Hardened `playerTeamDisplayName` + tests.

Commit SHA after commit.
