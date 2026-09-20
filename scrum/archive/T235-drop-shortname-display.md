---
id: T235
title: Drop shortName display; TeamType + full team name
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T05:09:00+02:00"
started_at: "2026-09-06T05:09:00+02:00"
completed_at: "2026-09-06T05:11:00+02:00"
depends_on: [T234]
---

# T235 — Drop shortName display; TeamType + full team name

## Why

`team+0x20` shortName only works for U19 in live evidence. FT/II empty → broken tabs/profiles. Either lock a general short field (RE) or drop shortName as the display contract. Ship functional labels from fields we already read for every team.

## Scope

**In:**

- Managed tabs → TeamType (unchanged)
- Affiliate tabs → memory full team name (`team.name` / `team+0x18` chain)
- Profile Club → memory full team name via `squadTeamUid` (same `name` field load already fills, including club fallback for empty FT)
- Stop using `shortName` for any UI label (field may remain on JSON for diagnostics)
- Recipes honesty: shortName is optional youth diagnostic, not product display law

**Out:** Club shortName RE; inventing nicknames

## Acceptance criteria

- [x] II tab shows full team name (e.g. `FC Schalke 04 II`), not `Map shortName`
- [x] FT / U19 / II profiles show full team name from load, not `—` / short-only
- [x] Vitest; one commit `T235: …`

## Progress

Dropped shortName as UI contract. Managed = TeamType; affiliate + profile = full FM team name. Entity-map shortName demoted to candidate/diagnostic. Vitest 41 ok.

Commit SHA: `feb8790`.
