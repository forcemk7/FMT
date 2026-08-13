---
id: T006
title: First Team extract must be managed club squad (not foreign list)
status: done
priority: 1
owner: auto
claimed_at: "2026-08-11T21:05:00+02:00"
started_at: "2026-08-11T21:15:00+02:00"
completed_at: "2026-08-11T21:25:00+02:00"
depends_on: []
---

# T006 — First Team extract must be managed club squad

## Why

**Loop break (behavior):** UI shows **FC Schalke 04** but First Team personality cards are a foreign roster (e.g. João Fonseca, Fabián Hidalgo, Portuguese names — not Schalke). Livelihood loop ranks / mentors the wrong players. Blocks T005 and any mentoring work on this save.

## Scope

- In: fix FT team/list selection so `players[]` belong to the managed club from `discover_managed_club` (clubId/teamId join); prove on the user’s current Career Save; keep II/U19 discovery consistent with the same club
- Out: Loans tab (T005 paused); Dynamics; cosmetic UI; loan detect changes unless required for identity

## Acceptance criteria

- [x] On Schalke save: FT names match in-game Schalke First Team (spot-check ≥5 known players; zero clear foreign-club stars as the whole list)
- [x] `clubId` / `teamId` / `listAbs` in extract refer to the managed club’s FT list
- [x] Regression: test or fixture locking “managed club id → FT list” (wrong-list ranking cannot win)
- [x] Document root cause in Progress (identity OK + wrong ranked squad vs stale store vs other)

## Notes / pointers

- `scripts/extract-first-team-fast.py` — `discover_managed_club`, squad `score` / `ranked` pick near ~1203–1371, result `teamId`/`listAbs`/`players`
- UI only displays `entry.players` + `entry.clubName` — if clubName is Schalke and players are foreign, extract (or wrong save bound in store) is lying
- Screenshot 2026-08-11: Schalke label + non-Schalke FT grid + “Out on loan” strip still present

## Progress

**Root cause:** Identity OK (`discover_managed_club` → clubId 920 / Schalke 04) but FT list came from `pick_tid` (manager-hit ranking among all 7f02 squad lists). Ranking can prefer a foreign persist-tid while clubName stays Schalke — identity and FT list were never joined.

**Shipped:**
- `scripts/ft_squad_discovery.py` — parent short → PRE_NAME club-object teamId/dup → mid-file body → persist-tid `7f02` job-list (`ft-club-squad-join-v1`)
- `extract-first-team-fast.py` resolves identity first, prefers FT join over `pick_tid` (fallback only if join misses)
- Lock fixture `data/fixtures/ft-club-squad-join-locked.json`
- Regression `tests/test_ft_club_squad_join_t006.py`

**Verified** on `tmp/live-0112-decomp.bin`: clubId 920 → bodyTeamId 580 / dup 919 → persistTid 193616 / listAbs 56324023; spot-check jobs Seimen/Bandeira/Paco/Kizza/Jones present; poisoned `pick_tid`→15658 cannot override join. `python -m unittest tests.test_ft_club_squad_join_t006 -v` OK (3 tests).

**Residual risk:** Join assumes II-style mid-file body layout + FT count band [15,45]; exotic saves without PRE_NAME club object still fall back to manager ranking.
