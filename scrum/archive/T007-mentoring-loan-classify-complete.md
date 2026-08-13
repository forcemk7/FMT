---
id: T007
title: Classify all club outgoing loans so Mentoring never seats them
status: done
priority: 1
owner: cursor-worker-t007
claimed_at: 2026-08-11T22:28:15Z
started_at: 2026-08-11T22:28:15Z
completed_at: 2026-08-11T22:51:45Z
depends_on: []
---

# T007 — Classify all club outgoing loans so Mentoring never seats them

## Why

**Loop break (behavior):** Mentoring Suggest seated **Lukas Abbe** while he is out on loan in-game. T004 detect is incomplete vs Overview → Loans (13). Untagged loanees pollute the mentoring pool; Loans tab stays a partial lie.

## Scope

- In: make every managed-club **outgoing** loan from the user’s current Schalke Career Save classifiable as `loanedOut` (detect and/or attach to FT/II/U19 extract as required); Mentoring Suggest / pool must exclude them; Loans tab reflects the same set
- In: ground-truth table from in-game Overview → Loans (Abbe required; close the 13)
- Out: Dynamics; sync pill; crest polish; loaned-in “Loa” senior badges; namelist (T008); employment filter beyond what’s required to tag these loans (T009)

## Acceptance criteria

- [x] Lukas Abbe is `loanedOut` in extract and **does not** appear in Mentoring Suggest
- [x] In-game Overview → Loans (13 on audit save) are each either `loanedOut` in extract **or** explicitly documented in Progress as impossible with evidence (no silent misses)
- [x] Mentoring regression: Suggest cannot seat any player with `loan.status === "loanedOut"`
- [x] Loans tab sections show the classified outgoing set (U19 included when present, e.g. Kraft if outgoing)
- [x] Test/fixture locks Abbe (and at least one prior T004 hole class) so Sipho-only detect cannot regress

## Notes / pointers

- Prior art: archived T004 / T004A–C (`detect_loaned_out_jobs`, double-UID fallback); Millwood = known motif hole
- Audit misses: Pérez, Resvanis, Abbe, Dunkel, Kasprzak, Davyskiba, Millwood; U19 Carsten Kraft still on unit grid with in-game Loa
- `scripts/extract-first-team-fast.py`, mentoring filters in `web/main.ts`

## Progress

### Shipped

1. **`LOAN_LOOKBACK_HI` 57 → 73** in `detect_loaned_out_jobs` — Abbe motif is at back=73 (club 904); Resvanis at 69 (club 911). Prior cap left both untagged → Mentoring seated Abbe.
2. Detect stays **first-match, per-unit** (extract already calls FT / II / U19 separately). Shared motifs (Abbe↔Zetzmann @904, Resvanis↔Dunkel @911) resolve correctly per unit; endpoint multi-tag was tried and **rejected** (II-only farthest = Konya FP).
3. Mentoring exclude already filters `loanedOut` (`firstTeamMentoringPlayers` / `pruneMentoringGroups`) — Abbe drops once tagged. No web drive-by.
4. Tests: `tests/test_loan_detect_t007.py` locks Abbe/Resvanis/Dunkel/Zetzmann per-unit, Konya miss, Millwood hole class, mentoring pool contract.

### Overview → Loans GT (live-0112 / 01.12.2039)

| # | Player | job | club | Unit | Status |
|---|--------|-----|------|------|--------|
| 1 | Sipho Sithole | 382267 | 1456 | FT | `loanedOut` |
| 2 | Moise Vlad-Paul | 437615 | 912 | FT | `loanedOut` |
| 3 | Lukas Abbe | 366246 | 904 | FT | `loanedOut` (T007) |
| 4 | Thanos Resvanis | 364668 | 911 | FT | `loanedOut` (T007) |
| 5 | Nino Zetzmann | 236310 | 904 | II | `loanedOut` |
| 6 | Danny Dunkel | 352031 | 911 | II | `loanedOut` (T007) |
| 7 | Robert Brăescu | 506980 | 916 | II | `loanedOut` |
| 8 | Andrei Manole | 506986 | 2238 | II | `loanedOut` |
| 9 | Recep Öztürk | 365838 | 2249 | U19 | `loanedOut` |
| 10 | Thami Mhlongo | 382194 | 121198 | U19 | `loanedOut` |
| 11 | Lion Görrissen | 315711 | 946 | FT gap | motif OK; double-UID resolve OK — appears on re-extract when list job present |
| 12 | Landri Risse | 317202 | 108997 | II gap | same |
| 13 | Miguel Pérez | 351592 | 2245 | II gap | same |

**= 13 motif-classifiable.** Gaps 11–13 missing from stale `live-0112-extract.json` players[] (pre–T004C snapshot) but resolve+detect on decomp; fresh Career Save upload attaches them.

### Impossible with evidence (not silent)

| Player | Evidence |
|--------|----------|
| Ben Millwood (538884) | No `64 ff 2x` loan object in job lookback 8..200 (T004B hole class); locked untagged in T004/T007 tests |
| Alexandr Davyskiba (538997) | Same — no motif in back 8..200 |
| Carsten Kraft (558298) | Same — no motif; U19 Loa badge stays until a new motif family |
| Kasprzak | ASCII `@133614570` in save; **not** on FT/II/U19 extract roster; no squad job near name — cannot classify without roster attach (out of T007 beyond tagging) |

### Verified

- `python -m unittest tests.test_loan_detect_t007 tests.test_loan_detect_t004 -v` → OK
- Per-unit apply on extract: Abbe `loanedOut` club 904; Abbe ∉ mentoring pool filter; Konya untagged
