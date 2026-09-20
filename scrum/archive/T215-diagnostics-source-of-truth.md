---
id: T215
title: Settings restructure — sections, per-cell status, restore missing fields
status: done
priority: 1
owner: worker
claimed_at: 2026-09-20T00:00:00+02:00
started_at: 2026-09-20T00:00:00+02:00
completed_at: 2026-09-20T00:00:00+02:00
depends_on: []
---

# T215 — Settings restructure — sections, per-cell status, restore missing fields

## Why

Unfrozen for FMT 1.28. Settings today is the closest thing FMT has to a diagnostics view, but it's not structured well enough to trust or to build on: fields the app used to surface (in-game date, DOB) appear to have gone missing along the way, which is the owner's leading suspect for the Squad B-team "ages show `--`" bug (see T288 for the related clubTeam-display half of that bug). This ticket is the concrete, scoped version of the old "Diagnostics = source-of-truth skeleton" doctrine below — get Settings right first, then T290 (telemetry) and T292 (PA toggle) build on top of it.

## Doctrine (kept from prior scope — still the guide, not gold-plated)

- One source of truth — connector/snapshot fundamentals. Diagnostics and the desks both consume it; neither invents a parallel copy.
- Diagnostics = precise raw / first-principles representation. Desks = humanized presentation of the same data.
- If a desk value is wrong, it's either (1) a UI/conversion problem or (2) a source problem — Diagnostics should make it possible to tell which.

## Scope

- In: Restructure Settings into clear, separated sections (e.g. FM26 process, Save meta, Manager, Club, Teams, Affiliations, Players — per owner's own proposed order in FMT 1.28 notes), each with proper per-cell status indicators (not the old warning-soup)
- In: Audit and restore diagnostic fields that used to exist and are now missing — **in-game date** first (leading suspect for the age "--" bug); confirm DOB is present and correctly sourced
- In: Add an empty **User Preferences** section shell (no content required beyond the section existing) — T292 (PA toggle) and future prefs land here
- In: Verify in-game date ↔ player age is provably correct for at least one at-club and one affiliate/B-team player once restored
- Out: Full live-fill-during-load streaming, graph-walk ordering as a hard requirement, or any other piece of the original architecture doctrine beyond what's needed to ship a trustworthy Settings page
- Out: Implementing telemetry itself (T290) or the PA toggle itself (T292) — this ticket only builds the section they'll live in / depend on

## Acceptance criteria

- [x] Settings is organized into named sections matching the FM26 → Save → Manager → Club → Teams → Affiliations → Players read order (plus Graphics first, per the owner's fuller note in `FMT 1.28.txt`)
- [x] Every cell shows a clear status indicator (present/correct, missing, error) — no undifferentiated warning text (reused the existing tone-cell system, no change needed here)
- [x] In-game date is visibly present again in Settings (own **Save** section, no longer buried in Players); DOB confirmed present in code (`dateOfBirth` emitted on every player, connector.rs:2484) — not surfaced as its own Settings cell since it's not a Settings-shaped diagnostic on its own, only feeds age
- [x] A player age computed from (in-game date, DOB) is demonstrably correct for one at-club and one affiliate/B-team player — **confirmed by owner (2026-09-20) on the Schalke save (FM24→26-converted)**: In-game date `2046-07-11`, Season `2046/47`, and ages present across **FT, U19, B, and affiliate players** — every squad band, not just one sample. Satisfies this criterion on a save where the underlying data is readable at all.
- [x] Empty User Preferences section exists in the new structure (placeholder cell pointing at T292)
- [x] One commit `T215: …`

## Owner verification (2026-09-20)

| Save | Provenance | Settings → Save | Squad ages |
|------|------------|------------------|------------|
| Schalke | FM24→26-converted | In-game date `2046-07-11`, Season `2046/47` | FT/U19/B/Affiliate all **present** |
| Barcelona | FM26-native | In-game date `Unavailable`, Season `Unavailable` | FT/U19/B all **missing** (expected fallout of no game date, not a separate bug) |

This confirms the investigation note below: the age/date architecture itself is correct — B-team and affiliate players get ages exactly like at-club players do, on a save where the game date is readable at all. Barcelona's failure is `squad_game_date` never resolving in the first place, which lines up with T294's already-tracked native-FM26-vs-FM24-converted confound (there, on the Players Go On Loan byte). Spun off as **T296** rather than reopening this ticket, since it's real RE work (offset investigation), not a Settings/UI fix. Repo-hygiene finding from this ticket's `git stash` check spun off as **T295**.

Investigation note (unchanged from during-ticket): read through `connector.rs`, the `squad_game_date` fallback (first readable current-date found across *any* first-team player, incl. loaned) is already threaded through `load_team_roster` → `load_bteam_affiliate_rosters` → `push_squad_player_from_raw`, so B-team/affiliate players aren't structurally excluded from getting a date — now confirmed correct end-to-end by the Schalke evidence above.

## Notes / pointers

- Today: `desktop/src/components/settings-screen.tsx` (Diagnostics), `desktop/src-tauri/src/connector.rs` (load + `fmt-load-progress`), T213 renamed/ordered fields + `gameDate`
- Owner's proposed section order (from FMT 1.28 notes): graphics, FM26 process, save meta-data, manager, club, teams, affiliations, players
- This ticket is a prerequisite for T290 (telemetry) and T292 (PA masking toggle)

## Progress

- Reordered Settings into Graphics → FM26 → Save → Manager → Club → Teams → Affiliations → Players → User Preferences (`settings-screen.tsx`)
- Split out new **Save** section (In-game date, Season — was buried inside Players) and new **Manager** section (Manager name, Manager pick, Name fallback — was inside Club)
- Added empty **User Preferences** section shell (placeholder cell, T292 lands its content here)
- Dropped the **Scores** section per owner's own note in `FMT 1.28.txt` ("not sure we need the scores, it's not that useful") — removed `FRONTEND_CALCULATION_CARDS`/`FrontendCalculationCard` from `has-score.ts` since it had no other consumer; incidentally removed a pre-existing TS2367 type error that lived in that dead code path
- No changes to `connector.rs` / age-DOB computation logic — confirmed by reading (not live-testing) that `squad_game_date` already threads through the B-team/affiliate roster path, so the "ages show `--`" bug isn't an obvious missing-wiring issue; see Blockers
- Verified: `npx tsc --noEmit` (no new errors vs. pre-existing baseline — confirmed via `git stash`/`git stash pop` diff, which also surfaced that the repo has substantial unrelated pre-existing uncommitted work outside this ticket's files — worth the owner's attention separately), `npx eslint` clean on both changed files, `vitest run has-score.test.ts` (5/5 passed), browser-verified section order/content/collapse behavior at `localhost:3000` (dev server, no live FM26 process — In-game date/Season correctly show "Unavailable" in that state)
- Owner verified live on two saves (2026-09-20) — see table above. All acceptance criteria met.
- Spun off T296 (in-game date unavailable on FM26-native saves — real RE, root cause likely shared with T294) and T295 (repo git hygiene + workflow guardrail, found via this ticket's own `git stash` check) — both included in this commit per the T287→T294 precedent.
- Commit: `3de655e`
