---
id: T288
title: Core clubTeam resolution model — wire into Squad, Loans, Profile, Dashboard
status: done
priority: 1
owner: worker
claimed_at: 2026-09-18T00:00:00+02:00
started_at: 2026-09-18T00:00:00+02:00
completed_at: 2026-09-20T00:00:00+02:00
depends_on: []
---

# T288 — Core clubTeam resolution model — wire into Squad, Loans, Profile, Dashboard

## Why

Match Experience already solved "which clubTeam is a player actually placed in" (vs. the club they're contracted to as parent/loan club). That resolution never got wired back into the desks built before ME: Squad (Spain B-teams missing), Loans / Player Profile (a player loaned to Kaiserslautern shows as "Kaiserslautern" instead of the actual squad they're placed in, e.g. "Kaiserslautern II"), and the Dashboard ME widget (shows the contracted parent/loan club instead of the clubTeam they're actually playing in). Same underlying data, four desks quietly diverged. Owner's own diagnosis: "build a core model for data reading, then wire them back up to the existing features" — this ticket is that consolidation, not four separate patches.

## Scope

- In: One shared read/resolve function: given a player, return (a) the clubTeam they are actually placed in in-game, (b) their contracted parent club, (c) their contracted loan club if out on loan — extract and centralize ME's existing logic
- In: Squad desk consumes it for B-team / affiliate rosters (should fix Spain B-teams and any other affiliate club with the same gap, not just Spain)
- In: Loans / Player Profile consumes it for loan-club display (show the actual placed clubTeam, e.g. "Kaiserslautern II", not just the parent/loan club)
- In: Dashboard ME widget consumes it (clubTeam actually playing in, not loanClub/parentClub)
- Out: New affiliate/loan-agreement RE (that's T287); ME card ordering (T253); anything not already solved by ME's existing resolution logic
- Out: Reserves/B-team roster as a brand-new feature — T199 was cancelled as a standalone feature; this ticket only reuses ME's already-built resolution, it does not reopen T199

## Acceptance criteria

- [x] A player placed in an affiliate B-team (Spain or otherwise) shows correctly on Squad desk — live-confirmed (Barcelona B)
- [x] A loaned-out player's profile shows the correct active club — live-confirmed; showing the *specific sub-team* at the loan club is out, `squadTeamUid` proven unreliable there (see Progress)
- [x] Dashboard ME widget shows the actual clubTeam name, not parent/loan club name — implemented, awaiting live check
- [x] No second/parallel implementation of clubTeam resolution left in the codebase — converged onto one core model, `research/club-team-display.md`
- [ ] One commit `T288: …` — pending, see below

## Notes / pointers

- Source of the already-solved logic: Match Experience feature code (`desktop/src/domain/match-experience.ts` per repo grep)
- Cross-check against the B-team ages "--" bug (separate suspected cause: missing in-game date, tracked under T215) — this ticket does not claim to fix ages by itself

## Progress

**Root cause found, not what the ticket assumed.** ME's own resolution (`matchExperiencePlayerCompetesOnTeam` in `match-experience.ts`) does NOT actually know which specific clubTeam a loaned player is placed in — for loaned players it explicitly approximates "loan club's First Team" ("no loan team uid yet", per its own comment) purely for ladder-ranking purposes. So there was no existing "solved" resolver to extract — each symptom had its own real cause:

1. **Squad desk / Spain B-teams — fixed.** `isSquadDeskClubTeam` (`live-data.ts`) unconditionally excluded any team with `affiliationType` 0x01/0x03. Spanish B teams are modeled as an "affiliated" entity even though they belong to the managed club itself, so they were being dropped by the same filter meant to hide genuine third-party feeder clubs. Fix: only exclude when `team.clubId !== managedClubId`. Tested (`live-data.test.ts`): keeps the managed club's own affiliation-flagged B team, still hides a real third-party affiliate.
2. **Player Profile loan display — fixed.** `player.squadTeamUid` already resolves to the correct specific clubTeam (e.g. "Kaiserslautern II") via the existing `playerTeamDisplayName`, for both at-club and loaned players — the profile screen was just discarding that and forcing the generic `loanClubName` whenever `loanedOut` was true. Extracted a new shared `playerActiveTeamDisplayName` (`live-data.ts`) that prefers the resolved clubTeam and only falls back to the loan club name when `squadTeamUid` doesn't resolve to a loaded team; wired into `player-profile-screen.tsx`. Tested: at-club unchanged, loaned player shows the placed clubTeam, falls back correctly when unresolved.
3. **Dashboard ME widget — could not confirm as a live bug.** `DashMatchExperienceRow` (`dashboard-widgets.tsx`) sources `fromClubName`/`toClubName` from `MatchExperienceCard.clubName`, which `buildMatchExperienceCard` already resolves via the actual team/club (not `loanClubId`/parent club) — this looks like it was already fixed by the earlier T244/T246/T248 tickets. Did not find a code path matching "displays loanClub instead of clubTeam" for this widget. Need a live pointer (which screen/card, ideally a screenshot) before touching more code here — did not want to guess-and-patch without a confirmed target.

**Verification:** `npx vitest run` — 139/139 passing (15 files), including 5 new/updated cases for the two fixes above. `npx eslint` on the 3 touched files — 0 errors (3 pre-existing unrelated warnings). `npx tsc --noEmit` — 8 pre-existing errors elsewhere in the codebase (confirmed present in HEAD before this ticket via `git show`), none on the touched code. No live save available in this environment to verify against actual game data (e.g. a real Barcelona save or a real Kaiserslautern loan) — **items 1 and 2 need your own live-save check before I close this ticket.**

**2026-09-18 update, after live save testing:**

- **Squad B-team inclusion:** confirmed the real root cause is Rust-side, not the TS filter I fixed — Barcelona B's affiliation byte (0x04, confirmed "B Club" via the pre-game editor) isn't in `affiliation_types.rs`'s `is_roster_load_affiliation_type` list at all, so it never becomes a `LiveClubTeam`. My TS fix stays (harmless, correct for the 0x01/0x03 case) but doesn't fix Barcelona B by itself. Proposed Rust fix identified, not yet applied — awaiting go-ahead (Rust changes need the owner's own build+live-save test; can't verify from here).
- **Player Profile loan display — corrected.** Live testing showed my first fix was wrong: `squadTeamUid` is not reliable for loaned players (proven — three different players loaned to three different real clubs all resolved to the same wrong team). Reworked `playerActiveTeamDisplayName` to mirror the same `loanClubId` → club lookup that already drives the (correct) logo, instead of trusting `squadTeamUid`. Shows the loan club name, consistent with the logo again; showing the *specific* clubTeam within the loan club is deferred — that data isn't reliably available yet. Re-tested (3 cases, all passing).
- **Dashboard ME widget:** confirmed real, not a data bug — owner wants the exact same rule Squad desk already uses (`squadTeamDisplayName`'s `isAffiliate` check: affiliate → clubName, else → teamType label) applied to the ME widget's team-type labels. Not yet implemented.

**2026-09-18, item 1 implemented:** `0x04` → "B Club" locked in `affiliation_types.rs` (label + added to `is_roster_load_affiliation_type` and `is_squad_tab_affiliation_type`, same treatment as `0x08` II Club). `cargo test --lib fm26::affiliation_types::` — 6/6 passing including a new case. `research/recipes.md` updated (Type map table + Open list). Awaiting owner's live rebuild+test on the Barcelona save before this is considered confirmed.

**Parked per owner (2026-09-18), not yet investigated:** after the loan-display fix, at-club players (First Team *and* Under 19s alike) now show just "Barcelona" as their team name on Player Profile, instead of the specific squad. Not touched — owner asked to defer this to a later pass, don't lose it.

**2026-09-18, item 1 live-confirmed by owner:** Barcelona B now shows on Squad desk (29 vs in-game's 31 — 2-player gap explained by in-game "temporary players," not a bug). Byte `0x04` mapping stands.

**2026-09-18, item 2 live-confirmed by owner (loan case):** Player Profile loan-club display now matches the logo for loaned players (João Marcos/Legia, Paul Ahlbäumer/Kaiserslautern, Florin Dănănae/Sparta Praha all correct). **Residual, explicitly parked by owner, not part of this ticket's closure:** at-club players (First Team *and* Under 19s alike) now show generic "Barcelona" instead of their specific team name — root cause not yet investigated; owner: "map bytes as needs appear, solve bugs as they are discovered" rather than dwelling now. Tracked here so it isn't lost.

**2026-09-18, item 3 implemented (owner's exact spec):** `matchExperienceTeamLabel` (`match-experience.ts`) now names the club instead of showing bare "First Team" specifically for a feeder's II hop (`isIiClubAffiliate`, 0x08) — since that's internally still "First Team" and shares a crest family with the feeder's own real First Team card, the two were indistinguishable by text alone. A feeder's own direct First Team (0x01/0x03) keeps the bare "First Team" label — its own distinct crest already disambiguates it from the managed club. 2 new test cases added (`match-experience.test.ts`), all 140 tests passing, lint clean. **Not yet live-verified** — owner needs to check the Fretson Penha–style Dashboard ME card against a rebuild.

All 3 acceptance-criteria items now implemented; items 1 and 2 (loan case) live-confirmed, item 3 awaiting live check. Not committed yet — one commit at close, per `AGENTS.md`.

**2026-09-19, core model built and the at-club residual fixed.** Owner rejected the byte-specific `isIiClubAffiliate`/hop-depth approach as "soup logic" — correctly: it broke the moment a second affiliate byte (Barcelona's `0x04`) needed the same treatment as `0x08`. Traced the actual Rust read path (`affiliate_links.rs::read_team_display_name`) and found the real cause of the at-club "Barcelona"-only residual: raw `team.name` silently falls back to the bare club name when the team's own name string is empty on a save — not a display-logic bug, a data-reliability one.

Built an audit table of all 6 UI surfaces (`research/club-team-display.md`), owner corrected it live against a real Barcelona save (two full QA passes), and we converged on one gate used everywhere: `isAffiliateClubTeam` (any `affiliationType` byte, no hop-depth distinction, no hardcoded byte list) plus two shared building blocks (`managedTeamTypeLabel`, `clubTeamDisplayName`) in `live-data.ts`. Implemented across all 5 non-Squad-desk surfaces:

- `live-data.ts`: added `isAffiliateClubTeam`, `managedTeamTypeLabel`, `clubTeamDisplayName`; `squadTeamDisplayName` refactored onto the same helper (behavior unchanged); `playerActiveTeamDisplayName`'s at-club branch now uses `clubTeamDisplayName` instead of trusting raw `team.name` — fixes the at-club residual without touching Rust
- `match-experience.ts`: `matchExperienceTeamLabel` widened from the `0x08`-only gate to `isAffiliateClubTeam`; added `teamTypeLabel`/`isAffiliate` to `MatchExperienceCard` for the bold/subtitle swap
- `match-experience-panel.tsx`: Profile ME tab cards now swap bold/subtitle for affiliate teams (clubName primary) vs managed teams (teamType primary)
- `squad-ability-rank.ts` / `dashboard-widgets.tsx`: Dashboard Best/Talent cards now show `clubTeamDisplayName`'s output as the visible text instead of bare teamType; `teamType` field kept bare (via new `matchExperienceBareTeamTypeLabel`) for the hover tooltip, which would otherwise have become redundant with clubName

Verification: `npx vitest run` — 142/142 passing (15 files, several tests updated/added to match the new gate). `npx eslint` on all touched files — 0 errors, only pre-existing warnings. `npx tsc --noEmit` — only pre-existing errors remain (confirmed present before this ticket). Browser boot-check — no runtime error. **Cannot verify the actual live strings from here** (no save data in this environment) — owner's live QA on Barcelona covered Squad desk and the loan case; the at-club fix, ME tab card swap, and Dashboard Best/Talent card are new since the last live check and still need a pass.

Residual, correctly out of scope: showing a loaned player's *specific* sub-team at the loan club (e.g. "Kaiserslautern II") stays unresolved — needs new data (`squadTeamUid` proven unreliable for loans), tracked in `research/club-team-display.md`'s "Still open" section, not this ticket.

**2026-09-20, closed.** Owner ran the full QA pass across two live saves (Barcelona, and a second save) covering all 5 surfaces — "can't find any obvious errors across both saves." Ticket done.
