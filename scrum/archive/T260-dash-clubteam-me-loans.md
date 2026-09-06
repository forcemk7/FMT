---
id: T260
title: Dash clubTeam spellout + ME count loans at destination
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T01:08:00+02:00"
started_at: "2026-09-07T01:08:00+02:00"
completed_at: "2026-09-07T01:12:00+02:00"
depends_on: [T259]
---

# T260 — Dash clubTeam spellout + ME count loans at destination

## Why

Best players/talent must show the real clubTeam (`{clubName} {teamType}`), including loans. ME #1–2 ranks omit loaned-out owned players at the destination First Team (still keyed only by parent `squadTeamUid`).

## Scope

- In: Ability peeks spell `{clubName} {teamType}` for actual/current clubTeam (loan → destination First when loaded)
- In: ME same-pos pool includes loaned-out players competing at loan club First Team (not parent roster)
- Out: Loan team-uid RE; division order

## Acceptance

- [x] Best players/talent extras use clubName + teamType (loan destination when loanedOut)
- [x] Loaned GK at Legia-style First raises max CA / demotes weaker ME #1 suggestion
- [x] Commit `T260: …`

## Progress

- `dashClubTeamSpellout` → `{clubName} {teamType}`; loans → destination First
- ME competing pool scans all players; loans only on destination band-0 First
- recipes.md T260 note
- Verified: match-experience + opportunities + squad-ability-rank tests
- Commit: `dffba05`
