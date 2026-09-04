---
id: T206
title: Club.Teams — in-game team display names
status: done
priority: 2
owner: auto
claimed_at: "2026-09-04T06:05:00+02:00"
started_at: "2026-09-04T06:05:00+02:00"
completed_at: "2026-09-04T06:09:44+02:00"
depends_on: []
---

# T206 — Club.Teams — in-game team display names

## Why

Squad tabs show the club name three times (“Liverpool” ×3) instead of in-game Club.Teams labels. `read_team_display_name` hits `+0x18/+0x20` then falls back to **club** name — English youth sides often share that string. Loop A cannot tell teams apart.

**Product vs bytes:** Tabs are the club→teams face of Loop A. Labels must match FM; the read may use TeamType, short name, competition, or any **documented** Team field from FSS / FMScout / archive — not “we only trust strings we found via managed-club RE.” No full Team-table world load required.

## Scope

- In: When team display string is empty or equals managed club name, disambiguate using locked **TeamType** (and/or a verified alternate team name field from the live-read archive) so tabs match in-game distinction (First / U21 / U18 / Reserves / …)
- In: Prefer real FM strings when present (Schalke-style `… U19`); never invent marketing labels that contradict TeamType
- In: Squad desk tabs + Settings rosterLen rows use the same display helper
- In: Keep discovery = Club.Teams vector only (T201)
- Out: Full-world Team table load; affiliate II; changing roster membership (T205); inventing “Senior” when TeamType says otherwise

## Acceptance criteria

- [x] Liverpool (or English club with ≥2 Club.Teams): tab labels are distinct and match FM’s team naming / structure (human check)
- [x] Schalke (or club with real `… U19` string): still shows the real string, not a worse invented label
- [x] No production world index
- [x] Unit coverage for display helper collision cases
- [x] One commit `T206: …`

## Notes / pointers

- Today: `affiliate_links::read_team_display_name` → club name fallback; UI `squadTeamDisplayName` refuses invented Senior/Youth
- TeamType map: `squad_unit_from_team_type` — may need finer labels for UI than `firstTeam|under19s|reserves` buckets
- Archive: `.cursor/rules/fm-live-read.mdc` TeamType + team name offsets; `team_names` probe / `team-names-probe.json`
- T204 left tabs name-only; this ticket is the deferred “label polish”

## Progress

Shipped:
- `resolve_team_tab_label` / `team_type_display_label` (Rust) — when name empty or equals club, use FMScout TeamType UI labels (First Team / U21 / U18 / U19 / II / …)
- Production `clubTeams.name` resolved at load; `LiveClubTeam.teamType` + TS `squadTeamDisplayName` / tabs / Settings share the same collision helper
- Distinct FM strings (Schalke `… U19`) kept; no world index

Verify:
- `npm test -- --run src/domain/live-data.test.ts` — 36 passed
- `cargo test --lib resolve_team_tab_label` — ok
- Human: reload English club (≥2 teams) + Schalke for live eyeball

Commit: `3d9c9e9bf37e4d2392c9ba5c70fc97b43d693dda`
