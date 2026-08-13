---
id: T009
title: Roster and Mentoring pool = club employees only
status: done
priority: 1
owner: auto
claimed_at: 2026-08-11T21:01:00Z
started_at: 2026-08-11T21:02:00Z
completed_at: 2026-08-11T21:17:00Z
depends_on: []
---

# T009 — Roster and Mentoring pool = club employees only

## Why

Mentoring only has value if the pool is people the managed club employs (at club or loaned out by the club). Foreign / non-employed bodies on FT/II/U19 or Suggest poison ranking and groups. T006 fixed wrong-club list join; residual employment edge cases still break trust.

## Scope

- In: filter/join so unit `players[]` and Mentoring pool contain only managed-club employees (contract/employment proof as used in extract); loaned-out employees stay classifiable (T007) but non-employees never appear as at-club roster
- Out: Dynamics; namelist completeness (T008); Loans tab chrome; scouting / fav clubs

## Acceptance criteria

- [x] Spot-check Schalke save: no clear non-employed / foreign-club stars on FT / Reserves / U19 at-club grids
- [x] Mentoring Suggest candidates are a subset of club employees (at-club); loaned-out excluded via T007 tagging
- [x] Document employment rule in Progress (which join/field defines “employed by managed club”)
- [x] Regression: fixture or test that a non-employee cannot win FT list membership / mentoring pool

## Notes / pointers

- T006: club-object → `7f02` FT join — start from that identity; extend employment check if list still admits junk
- User requirement: “not including players in roster not employed by club”
- Coordinate with T007 if a body is missing because it was wrongly dropped vs wrongly kept

## Progress

**Employment rule:** Employed by managed club = `jobId` on that club’s unit squad list:
- FT: club-object PRE_NAME → mid-file body → persist-tid `7f02` (`ft-club-squad-join-v1`)
- II: affiliate name → clubId/team body
- U19: mid-file namelist (before-name list only)
- Mentoring pool = FT employees ∩ ¬`loanedOut` (T007)

**Shipped:**
- `select_managed_ft_jobs` — when club short known, join miss → empty FT (`ft-club-squad-join-miss`); never `pick_tid` foreign lists
- Extract wires that gate; discovery emits `employmentRule`
- Mentoring comment documents pool = join employees minus loanedOut
- Fixture `ft-club-squad-join-locked.json` + `tests/test_roster_employees_only_t009.py`

**Verified:**
- Live bin: join persistTid 193616 / 33 jobs; decoy tid 15658 (45 jobs) overlap=0
- Spot-check fixture Schalke FT jobs present; U19 before-name count=25 (decoy after-name excluded)
- Mentoring pool ⊆ join jobs − loanedOut; decoy job samples ∉ pool
- `python -m unittest tests.test_roster_employees_only_t009 tests.test_ft_club_squad_join_t006 -v` OK (7 tests)

**Residual risk:** Stale roster store from pre-T006 `pick_tid` extracts still needs re-upload. Exotic saves without PRE_NAME club object get empty FT (fail closed) rather than foreign stars. Per-player parentClub/loanedIn contract proof not added — list membership is the employment proof.
