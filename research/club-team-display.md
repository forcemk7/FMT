# Club / team display — core model

Every UI surface that shows "which club/team is this player on" grew its own resolution function at a different point in development. This file started as the audit the owner asked for (2026-09-18); the "current wiring" section below is now historical — **the target model section is what's actually implemented (2026-09-19).** Any new UI surface needing a club/team string reads from this model — do not add a seventh resolver without updating this file in the same change.

## Target model (implemented 2026-09-19)

**The one gate:** `isAffiliateClubTeam(team) = typeof team.affiliationType === "number"` (`live-data.ts`). Any affiliation byte at all — direct feeder, its II hop, a managed club's own B/II-style entity — is the same "not a plain managed squadUnit team" signal. No hop-depth distinction, no hardcoded byte list.

**Two core building blocks (`live-data.ts`), everything else composes from these:**
- `managedTeamTypeLabel(team)` — bare TeamType/squadUnit label ("First Team"/"Under 19s"/"Reserves"), never a club name. Also exported from `match-experience.ts` as `matchExperienceBareTeamTypeLabel` for that module's own Pick type.
- `clubTeamDisplayName(team, fallbackClubName)` — the single-string core: managed First Team → bare club name; managed non-First → `"{clubName} {teamType}"`; any affiliate → its own name alone.

**Per surface:**

| Surface | Function | Behavior |
|---|---|---|
| Squad tabs | `squadTeamDisplayName` | unchanged — affiliate → team name; managed → `managedTeamTypeLabel` alone (shell already shows club context) |
| Player Profile club fact | `playerActiveTeamDisplayName` → `clubTeamDisplayName` (at-club branch); loan branch unchanged (`loanClubId` lookup, T288) | "Barcelona" (FT), "Barcelona Under 19s" (U19), "Barcelona B" (affiliate) |
| Profile ME tab card | `MatchExperienceCard.teamLabel` + `.teamTypeLabel` + `.isAffiliate`, swapped in `match-experience-panel.tsx` | managed: bold=teamType, sub=clubName. affiliate: bold=clubName, sub=teamType |
| Dashboard ME row | `matchExperienceTeamLabel` (now the plain `isAffiliateClubTeam` gate, was hardcoded `0x08` only) | managed → teamType; affiliate → clubName |
| Dashboard Best/Talent card | `dashClubTeamChrome().displayLabel` → `clubTeamDisplayName`; loan branch always clubName (loan destination is never "managed") | same 3-way split as Profile club fact |

**Deliberately not touched:** `squadTeamDisplayName` (Squad desk was already correct — it's the one place `managedTeamTypeLabel` came from). Loan destination *specific sub-team* (e.g. "Kaiserslautern II" for a loaned player) stays unresolved — `squadTeamUid` is proven unreliable for loaned players (see prior section); loan surfaces show the club name alone until that data exists.

## Original audit (2026-09-18, kept for history)

## The raw data every resolver works from

- `LivePlayer.squadTeamUid` — which `LiveClubTeam` roster this player record was read from. Reliable for at-club players. **Not reliable for loaned-out players** (T288: proven live — resolved to the same wrong parent-side team for three different real loan destinations).
- `LivePlayer.clubId` / `clubName` — contracted (parent) club.
- `LivePlayer.loanClubId` / `loanClubName` — loan destination **club** (club-level only; no reliable pointer to the *specific team* within that club yet).
- `LiveClubTeam.name` — raw memory string at `team+0x18` (fallback `team+0x20`), **falls back further to the linked club's bare name when both are empty** (`affiliate_links.rs::read_team_display_name`). This is *why* Barcelona's U19 team currently reads back as plain "Barcelona" — its own name string is empty on that save, not a display-logic bug.
- `LiveClubTeam.clubId` / `clubName` — the club that actually owns this specific team (for an affiliate's own II/B side, this can differ from both the managed club and the parent affiliate's club).
- `LiveClubTeam.affiliationType` — `None` for a managed-club team (firstTeam/under19s/reserves); a byte (`0x01`/`0x03`/`0x04`/`0x08`/…) for anything reached via the affiliate walk. This is the one **reliable, non-hardcoded** signal for "is this actually a different club's team."
- `LiveClubTeam.teamType` / `squadUnit` — classification (firstTeam/under19s/reserves), independent of the (sometimes-empty) name string. **Squad desk's tab label already proves this classification is reliable even when `.name` is not** — it never uses `.name` for a managed team.

## Current wiring (audit — correct this)

| UI element | File | Function(s) | What it shows today | Logic in one line |
|---|---|---|---|---|
| Squad desk tab label | `my-team-screen.tsx` → `live-data.ts` | `squadTeamTabLabel` → `squadTeamDisplayName` | "First Team (31)", "Under 19s (49)", "Barcelona B (29)" | `affiliationType` set → raw `team.name`; else → teamType/squadUnit label only (**no club name** — correct here, since the shell already shows managed-club context) |
| Settings / Diagnostics club-team list | `settings-screen.tsx` | `squadTeamDisplayName` | same convention as Squad desk | same function, reused correctly |
| Player Profile "Club" fact | `player-profile-screen.tsx` → `live-data.ts` | `playerActiveTeamDisplayName` → `playerTeamDisplayName` | At-club: raw `team.name` (so "Barcelona" for FT — fine; "Barcelona" for U19 — **wrong**, should be "Barcelona U19"). Loaned: loan club name via `loanClubId` lookup (correct, T288) | At-club trusts raw name (inherits the empty-name-U19 bug); loaned bypasses `squadTeamUid` entirely (deliberate, post-regression) |
| Player Profile "Match experience" tab cards | `match-experience-panel.tsx` | `card.teamLabel` + `card.clubName` (two separate fields, both lines always shown) | Two-line card: bold teamType ("First Team") + subtitle club name ("1. FC Kaiserslautern II") | Sidesteps the single-string ambiguity entirely by always showing both — **this is the one surface with no reported bug** |
| Dashboard "Match experience opportunities" row | `dashboard-widgets.tsx` → `match-experience-opportunities.ts` → `match-experience.ts` | `matchExperienceTeamLabel` (feeds `fromTeamLabel`/`toTeamLabel`) | Single text label next to the crest. Currently: `affiliationType === 0x08` only → clubName; everything else → bare teamType | **Byte-hardcoded (0x08 only)** — confirmed broken for Barcelona B (`0x04`) on live save, same bug class the owner flagged |
| Dashboard "Best players" / "Best talent" cards | `dashboard-screen.tsx` → `squad-ability-rank.ts` | `dashClubTeamChrome` / `dashClubTeamSpellout` (deprecated) → own local `resolveClubName` + `matchExperienceTeamLabel` | "{clubName} {teamType}" combined string/chrome object | **A fourth independent resolver** — own `resolveClubName` helper, not shared with any of the above |
| Squad desk player card loan badge | `my-team-screen.tsx` (`faceBadge`) | direct field access, no shared function | "Parent club: X" / "Loan club: X" | Reads `player.loanClubName` / `player.employerClubName` straight off the player record — **no team resolution at all, by design** (club-level badge, not meant to name a specific team) |

## What's actually wrong vs. what's fine

- **Not wrong:** club-level badges (Squad card loan badge) and any surface that shows teamType + clubName as two separate, always-visible pieces (ME tab cards). Ambiguity only exists where a single string has to carry both club identity and squad type.
- **Wrong, one root cause each:**
  1. Player Profile "Club" fact for at-club youth/reserve players — inherits `LiveClubTeam.name`'s empty-string-falls-back-to-bare-club-name behavior. Fix belongs in `read_team_display_name` (Rust), not TS — build `{clubName} {teamType label}` there when the team's own name string is genuinely empty, using the classification data (`teamType`) already available at that point, not a literal string this save doesn't have.
  2. Dashboard ME single-line labels — hardcodes `0x08`. Should use `affiliationType is a number` (any byte) as the "not the managed club's own team" gate — no byte list — same predicate `squadTeamDisplayName` already uses.
- **Structurally wrong regardless of the two bugs above:** four independent resolvers (`squadTeamDisplayName`, `playerTeamDisplayName`, `matchExperienceTeamLabel`, `resolveClubName` in `squad-ability-rank.ts`) each reimplement "is this an affiliate, what do I call it" slightly differently. Owner's ask: converge on one core resolver future UI wiring reads from, instead of a fifth reimplementation next time a new desk needs this.

## Resolved (2026-09-19, via owner's own QA pass on the Barcelona save)

- **Direct feeder vs its II hop:** no distinction — both are "affiliate," both show the full club name. Confirmed live: Barcelona B (`0x04`, a *direct* affiliate of the managed club, not a "II hop" at all) needed the exact same treatment as Kaiserslautern II, which is what killed the earlier hop-depth-based design.
- **Single function vs building blocks:** building blocks. `isAffiliateClubTeam` + `managedTeamTypeLabel` + `clubTeamDisplayName` compose differently per surface (single string vs bold/subtitle pair) — see target model above.
- **Not fixed at the Rust source after all:** the `read_team_display_name` fallback-improvement proposed in the original audit became unnecessary — `clubTeamDisplayName` never trusts raw `team.name` for managed teams now, so the empty-string-on-some-saves problem is sidestepped at the TS layer instead. Rust `read_team_display_name` is untouched.

## Still open

- Loaned player's *specific* sub-team at the loan club (e.g. "Kaiserslautern II" instead of just "Kaiserslautern") — needs new data, `squadTeamUid` is unreliable there. Not attempted.
- Owner's live QA pass covered one save (Barcelona) — a second save hasn't been checked against this model yet.
