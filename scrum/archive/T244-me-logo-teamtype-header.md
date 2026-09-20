---
id: T244
title: ME cards — club logo + TeamType header
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T21:43:00+02:00"
started_at: "2026-09-06T21:44:00+02:00"
completed_at: "2026-09-06T21:47:00+02:00"
depends_on: [T242]
---

# T244 — ME cards — club logo + TeamType header

## Why

Long `{clubName} {TeamType}` titles truncate and confuse duplicate affiliates. Identity = badge + TeamType (e.g. Legia crest · First Team).

## Scope

- In: Match experience card header = `ClubLogo` + TeamType label; tooltip/aria keeps full club name
- In: Pass club UniqueID on ME card (from roster players; managedClubId fallback for own teams)
- Out: shortName RE; loan-agreement filter (T245); Squad desk labels

## Acceptance criteria

- [x] ME header shows logo + TeamType (not long club string as title)
- [x] Distinct affiliates still readable (same crest, different TeamType)
- [x] Tests updated; Squad desk unchanged
- [x] Commit `T244: …`

## Progress

Shipped: `matchExperienceTeamLabel` = TeamType only; card carries `clubId` + `clubName` (tooltip); panel header `ClubLogo` + TeamType. Verified vitest match-experience (10).

Commit: `8c460e5`
