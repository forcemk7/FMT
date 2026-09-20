---
id: T296
title: In-game date / Season unavailable on FM26-native saves (Barcelona)
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T296 — In-game date / Season unavailable on FM26-native saves (Barcelona)

## Why

T215's owner-verification (2026-09-20) tested two saves in Settings → Save:

| Save | Provenance | In-game date | Season | Squad ages (FT/U19/B/Affiliate) |
|------|------------|--------------|--------|----------------------------------|
| Schalke | FM24→26-converted | `2046-07-11` | `2046/47` | all present |
| Barcelona | FM26-native | `Unavailable` | `Unavailable` | all missing (expected fallout, not a separate bug) |

T215's own investigation already confirmed the age/date-fallback wiring (`squad_game_date` threading through `load_team_roster` → `load_bteam_affiliate_rosters` → `push_squad_player_from_raw`) is architecturally correct — Schalke proves it works end-to-end across every squad band. Barcelona's failure is that `squad_game_date` never resolves *at all* (no player in the whole first team has a readable current-date), not a downstream wiring gap.

This is very likely the same root cause as **T294** (Players Go On Loan flag doesn't generalize to affiliationType `0x01`): that ticket already flagged an unresolved confound between affiliation type and **save provenance (FM26-native vs FM24→26-converted)** — Barcelona is the exact save both issues live on. Two independent fields now failing along the same native/converted line makes "FM26-native saves need different offsets (or a different EntityMapProfile) for at least these fields" the leading hypothesis, not a coincidence.

## Scope

- In: Confirm whether `player_current_date_offset` (and/or `person_birth_date_offset`) is wrong/shifted specifically on FM26-native saves — same falsifiable separator-search methodology T287 used for the loan byte, applied here
- In: Check Barcelona's `status.gameBuild` / other FM26-section diagnostics (now easy to find post-T215) for a detectable build/version signal that could gate a native-save offset variant, rather than guessing blind
- In: If isolated, lock the correct native-FM26 offset(s) the same way T287 locked `wrapper+0x2E`, and update `research/recipes.md`
- In: Coordinate with T294 — if root cause is "native-FM26 saves need a different EntityMapProfile entirely," that likely resolves both tickets together; if it's field-by-field, keep them separate and say so explicitly in both tickets
- Out: Reworking the `squad_game_date` fallback logic itself in `push_squad_player_from_raw` — already confirmed correct by T215's Schalke evidence; don't touch unless this investigation actually disproves that
- Out: Any Settings/UI work — T215 already made this diagnosable

## Acceptance criteria

- [ ] Root cause identified for FM26-native saves: which offset(s), or a broader profile mismatch
- [ ] Barcelona (or an equivalent native-FM26 save) shows a real in-game date and correct squad ages across FT/U19/B/affiliate
- [ ] Schalke (or an equivalent converted save) still correct — no regression
- [ ] `research/recipes.md` updated with the locked native-save offset/condition, cross-referenced with T294
- [ ] One commit `T296: …`

## Notes / pointers

- Owner evidence: see table above (2026-09-20)
- Sibling ticket: T294 (`scrum/tickets/T294-loan-flag-0x01-affiliation-type.md`) — same Barcelona save, same native-vs-converted confound, different field. Check together before assuming either is isolated.
- `research/recipes.md` "Open: `wrapper+0x2E` does not generalize to affiliationType `0x01`" section already documents the native-vs-converted distinction for this exact save pair — reuse that framing/terminology.
- T213/T215 — where `gameDate`/`squad_game_date` were promoted onto the snapshot and made visible in Settings → Save.

## Progress

_(worker fills)_
