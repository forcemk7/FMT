---
id: T118
title: At-club Senior UniqueIDs — mentoring pool (one native Career)
status: done
priority: 1
owner: cursor-worker
claimed_at: "2026-08-20T20:16:00+02:00"
started_at: "2026-08-20T20:18:00+02:00"
completed_at: "2026-08-20T20:45:16+02:00"
depends_on: [T109, T114]
---

# T118 — At-club Senior UniqueIDs — mentoring pool

## Why

Shell + club identity + gameDate are enough honesty. Mentoring needs **Senior players who are at the club** (available for groups). Not II/U19 taxonomy. Not pink/blue labels in the UI. Not `+488` names.

## Definition (minimal)

- **In pool:** Senior / first-team, currently **at the club** (owned at club + inbound loan both count as at-club)
- **Out of pool:** owned but **out on loan**; other units (2 / U19)
- Ship: Squad rows = UniqueID + name for the at-club set. Unit label `senior` or `at-club`. No HA this ticket unless already free

## Scope

- In: **One** native Career first — prefer `gameDate8.fm` (Santos). Working copy + delete (T109)
- In: Structural path club → at-club Senior UniqueIDs. Start from T115 clue: club `.dat` intern list count **32** on Santos (close to at-club). Prove Lund-class completeness is not required this ticket; prove **outbound not in mentoring pool**
- In: Fill Active Squad from those ids (not `+488`). Continue: honest empty/skip
- In: Unittest with gold subset in `tests/fixtures/` (not hardcode in extract law)
- Out: Bodø unit bits. Full 42 three-status. II/U19 lists. Cloud. HA/CA. UI polish. Parallel races. Long STATUS essays

## Blind

- Do not steal T115 / T116 / T117 (frozen)
- Do not ship `+488` as mentoring pool
- Do not mmap live SI `games/`
- Do not git add `data/saves/`, `*.fm`, `tmp/`
- Do not expand to “all 8 Careers” until Santos at-club list is honest vs FM white+blue

## Acceptance

- [x] Santos Active Squad shows UniqueID-backed at-club Senior rows (not name blob)
- [x] Gold owned-out (except any true false-positive documented) **absent** from Squad
- [x] Gold owned-at-club + inbound present (or dump lists the misses; blocked if >few)
- [x] One commit `T118: …` on `FMT/`

## Gold pointers

- T115 ticket / `tests/fixtures/t115-santos-gold.json` — white + blue = at-club; pink = out
- Moisés was in the `.dat` 32 and gold pink — if still included, document; do not call success until out

## Progress

- Shipped: `extract-squad-lists.py` = `native-club-dat-senior-v1` (club `.dat` intern list → UniqueID; drop owned-out when person-intern is in loan-out template lookback, including Moisés host id above old 5e6 ceiling; name via PERSON_NAME_MARK + native name-table 40–90MB). Unit `senior`. Continue skips. UI accepts `senior`. No HA/CA / II/U19 / three-status UI. Gold stays in fixtures.
- Verified: unittest synthetic drop + continue skip + gameDate8 → **31** = 28 white + 3 inbound, outbound ∩ Squad = ∅; vitest T118/T114/T111. Working copy + delete.
- Commit: recorded on FMT/ as `T118: …`
