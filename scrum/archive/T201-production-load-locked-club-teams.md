---
id: T201
title: Production load — locked Club.Teams only
status: done
priority: 1
owner: auto
claimed_at: "2026-09-04T04:00:00+02:00"
started_at: "2026-09-04T04:00:00+02:00"
completed_at: "2026-09-04T04:15:00+02:00"
depends_on: [T200]
---

# T201 — Production load — locked Club.Teams only

## Why

After T200, production still ran unfinished B-team affiliate heuristics and a heap-window team fallback on every load. Load must be honest and fast: only locked Club.Teams + TeamType for same-club sides. Separate-club reserves (German II etc.) wait on affiliate flag RE (Main + Permanent + Players Move Freely) — not production.

## Scope

- In: Reorder extract: manager → Club.Teams vector → first-team roster → other same-club rosters
- In: Drop production calls to B-team affiliate discover/load; drop heap fallback in `discover_teams_for_club`
- In: Classify squad units from TeamType + managed first team only (no `" ii"` / roster-band heuristics)
- Out: Implementing affiliate Main/Permanent/Move Freely lock (future ticket); deleting probe helpers; UI redesign

## Acceptance criteria

- [x] Production `extract_live_data` does not call `discover_bteam_affiliate_clubs` / `load_bteam_affiliate_rosters`
- [x] Same-club teams come only from Club.Teams vector (empty vector → no heap scan)
- [x] First-team roster loads before other same-club rosters
- [x] Classification uses TeamType / first-team identity only
- [x] Unit tests updated; one commit `T201: …`

## Progress

**Load order now**
1. Resolve human manager → managed club
2. `loading_club_teams` — Club.Teams vector only
3. `loading_managed_squad` — first-team roster
4. `loading_youth_squads` — other same-club teams (TeamType-classified)
5. No B-team affiliate discover/load; no heap team scan; no full-save index

**Removed from production**
- `discover_bteam_affiliate_clubs` / `load_bteam_affiliate_rosters` / merge satellite helpers
- Heap-window fallback in `teams_for_club`
- Name / roster-band classification heuristics

**Residual / next RE (not this ticket)**
- Separate-club reserves: discover affiliates → Main + Permanent → Players Move Freely (FMLE-visible flags) → then Club.Teams on that club. Probe helpers in `affiliate_links` remain for that work.

**Verify:** `classify_club_team_by_uid`, `team_type_maps`, `club_teams_and_team_type` — ok.

Commit: `79c09c4c6ef9316b7a7fb32d32cd802b6721a3f2`
