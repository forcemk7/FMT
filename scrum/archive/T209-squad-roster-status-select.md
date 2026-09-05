---
id: T209
title: Squad — roster status Filter dropdown
status: done
priority: 5
owner: cursor-agent
claimed_at: "2026-09-06T00:14:00+02:00"
started_at: "2026-09-06T00:14:00+02:00"
completed_at: "2026-09-06T00:31:00+02:00"
depends_on: []
---

# T209 — Squad — roster status Filter dropdown

## Why

T204 put At club / On loan / Loaned out as three checkboxes. Crowds the toolbar. Owner wants an in-game-style **Filter** control (pill + chevron → panel).

## Scope (from FM Filter screenshot — what we keep)

Steal only the **Hide players**-class status slice. Map to existing roster statuses: `atClub` / `loanedIn` / `loanedOut`.

**Out:** Squads (team tabs), Positions, Quick Pick, density (T210).

## Acceptance criteria

- [x] Squad toolbar shows one Filter control, not three always-visible checkboxes
- [x] Menu lists available statuses with counts; **multi-select** toggles (menu stays open)
- [x] Default selection is At club when available for the team
- [x] Domain helpers remain source of truth; session remembers the set per team
- [x] Commits `T209: …`

## Progress

Filter pill → Status menu. Multi-select checkboxes; cannot clear last option. Default At club. Commits `9f816c2` (initial), `e081f25` (multi-select).
