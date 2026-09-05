---
id: T209
title: Squad — roster status Filter dropdown
status: done
priority: 5
owner: cursor-agent
claimed_at: "2026-09-06T00:14:00+02:00"
started_at: "2026-09-06T00:14:00+02:00"
completed_at: "2026-09-06T00:18:00+02:00"
depends_on: []
---

# T209 — Squad — roster status Filter dropdown

## Why

T204 put At club / On loan / Loaned out as three checkboxes. Crowds the toolbar. Owner wants an in-game-style **Filter** control (pill + chevron → panel) — not a native bare `<select>` if we can keep chrome light.

## Scope (from FM Filter screenshot — what we keep)

Steal only the **Hide players**-class status slice from FM’s Filter panel. Map to existing roster statuses:

| FM-ish label | FMT status |
|--------------|------------|
| At club (not “Not at club”) | `atClub` |
| On loan / trial (loaned in) | `loanedIn` |
| Loaned out | `loanedOut` |

**Out of this ticket** (already covered or creep):

- **Squads** (Senior / U19 / 2nd) → already team tabs
- **Positions** / sides → not now
- **Quick Pick**, registration, home-grown, match squad, long-term deals → not now
- Card/list density (T210)

## In

- Replace multi-checkbox `squad-roster-filters` with one **Filter** trigger (label + chevron) opening a small menu of the available statuses for the selected team
- Each row: checkbox or radio-style single pick with live count (`At club (28)`, …)
- **Single status** selection (not multi). Default = `atClub` when available, else first available. Zero-count options hidden as today
- Filtering still via `playerMatchesSquadRosterFilters` / one-element set
- Visual: dark panel, section optional (“Hide players” / “Status”) — match FMT desk chrome, not a full FM clone

## Acceptance criteria

- [x] Squad toolbar shows one Filter control, not three always-visible checkboxes
- [x] Menu lists only available statuses with counts; choosing one filters the matrix
- [x] Default selection is At club when available for the team
- [x] Domain helpers remain source of truth; adjust multi-select tests
- [x] One commit `T209: …`

## Notes / pointers

- UI: `desktop/src/components/my-team-screen.tsx`
- Domain: `playerMatchesSquadRosterFilters`, `countSquadTeamRoster`, `squadRosterStatus` in `live-data.ts`
- Behavior vs T204: multi → single

## Progress

Shipped FM-style Filter pill → Status menu (At club / On loan / Loaned out with counts). Single status; default At club; session remembers one status per team. Vitest session + live-data OK. Commit `9f816c2`.
