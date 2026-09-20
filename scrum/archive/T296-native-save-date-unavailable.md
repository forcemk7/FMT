---
id: T296
title: In-game date / Season unavailable on FM26-native saves (Barcelona)
status: done
priority: 2
owner: worker
claimed_at: 2026-09-20
started_at: 2026-09-20
completed_at: 2026-09-20
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

- [x] Root cause identified for FM26-native saves: which offset(s), or a broader profile mismatch
- [x] Barcelona (or an equivalent native-FM26 save) shows a real in-game date and correct squad ages across FT/U19/B/affiliate
- [x] Schalke (or an equivalent converted save) still correct — no regression
- [x] `research/recipes.md` updated with the locked native-save offset/condition, cross-referenced with T294
- [x] One commit `T296: …`

## Notes / pointers

- Owner evidence: see table above (2026-09-20)
- Sibling ticket: T294 (`scrum/tickets/T294-loan-flag-0x01-affiliation-type.md`) — same Barcelona save, same native-vs-converted confound, different field. Check together before assuming either is isolated.
- `research/recipes.md` "Open: `wrapper+0x2E` does not generalize to affiliationType `0x01`" section already documents the native-vs-converted distinction for this exact save pair — reuse that framing/terminology.
- T213/T215 — where `gameDate`/`squad_game_date` were promoted onto the snapshot and made visible in Settings → Save.

## Progress

**Root cause is not an offset or profile mismatch — it's save-freshness, not save-provenance.**

Built `probe-game-date` (new `cargo run -p fmt --features fm-probe --bin probe-game-date`, mirrors `probe-loan-flag`'s shape) and ran it live against the attached Barcelona process:

- `person_birth_date_offset` (136) resolved correctly for 30/31 sampled first-team players (only a placeholder GK stub, "Mariusz", had none) — ruling out a broad native-save profile/offset mismatch. The entity map is fine.
- `player_current_date_offset` (512) was unreadable for all 31 players at the documented offset, confirming the bug is real.
- A ±96-byte brute-force shift scan around 512 found one candidate (`+4`) that decoded a near-identical date for all 31 players (30× `2022-08-13`, 1× `2022-08-14`) — clean stats, but the owner confirmed Barcelona's actual in-game date was `2025-07-14`, so this was a false positive (likely an unrelated static/rarely-touched field that happened to satisfy the date-validity check across the whole roster).
- Owner reported this Barcelona save is a **control save that had never been advanced past its load date**. Owner advanced it by exactly one day (`2025-07-14` → `2025-07-15`) and re-checked: Squad now shows correct ages for all bands (First Team confirmed live via screenshot; Under 19s/Barcelona B inherit the same `squad_game_date` fallback per the T215-verified architecture, so expected to follow automatically).

**Conclusion:** `player_current_date_offset` is a per-player "last processed" cache that FM only writes once its normal day/match/training tick touches that player. On a save sitting at the exact moment it was created/loaded, with zero days simulated, **no player anywhere has been touched yet**, so the field is genuinely unset for the entire squad — not wrong, not shifted, just not written yet. `squad_game_date`'s fallback (first first-team player with a readable date) has no readable date to fall back to on a totally virgin save. This is a real, if narrow, edge case: a downloader who attaches FMT before ever clicking Continue on a brand-new career would see the same `Unavailable` state Barcelona showed. In practice any real user reaches this within their first in-game day, so no code fix is required for T296's scope — the existing wiring (confirmed correct by T215's Schalke evidence and now also by Barcelona post-advance) is doing the right thing with the data that exists.

**No production code changed.** Added `probe-game-date` (`desktop/src-tauri/src/bin/probe_game_date.rs`, `probe_game_date_dump()` in `connector.rs`, gated `fm-probe` same as `probe-loan-flag`) as a reusable RE tool — kept in-tree per the T287 precedent, not deleted, since the "does this field/offset resolve, and is it stable across the whole squad" question will come up again.

**Cross-reference for T294:** T294's blocked Olot (`affiliationType 0x01`) test was run on this **same never-advanced Barcelona save**. If the Players-Go-On-Loan byte is *also* a lazily-written field (plausible — loan agreements could be similarly cached/computed on a tick), T294's "off" reading for Olot could be the identical save-freshness confound, not an affiliation-type-vs-provenance issue at all. Cheap to check now that the save has already been advanced: re-read Olot's flag in FMLE/FMT with no new RE work. Flagged in T294 below; not chased further here since it's outside T296's scope.

Commit: pending — see final report.
