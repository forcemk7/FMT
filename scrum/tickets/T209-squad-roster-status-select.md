---
id: T209
title: Squad — roster status Filter dropdown
status: ready
priority: 5
owner: null
claimed_at: null
started_at: null
completed_at: null
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

- [ ] Squad toolbar shows one Filter control, not three always-visible checkboxes
- [ ] Menu lists only available statuses with counts; choosing one filters the matrix
- [ ] Default selection is At club when available for the team
- [ ] Domain helpers remain source of truth; adjust multi-select tests
- [ ] One commit `T209: …`

## Notes / pointers

- UI: `desktop/src/components/my-team-screen.tsx`
- Domain: `playerMatchesSquadRosterFilters`, `countSquadTeamRoster`, `squadRosterStatus` in `live-data.ts`
- Behavior vs T204: multi → single

## Progress

_(worker fills)_
