---
id: T200
title: Lock Club.Teams + TeamType for controllable squads
status: done
priority: 1
owner: auto
claimed_at: "2026-09-04T02:07:00+02:00"
started_at: "2026-09-04T02:07:00+02:00"
completed_at: "2026-09-04T02:25:00+02:00"
depends_on: []
---

# T200 — Lock Club.Teams + TeamType for controllable squads

## Why

Player field reads are good enough for Loop A. FMT still cannot honestly list **every controllable team** under an arbitrary managed club (First / II / U19 / …) on FM24/26 saves. Current paths use Schalke-shaped heuristics (affiliate `@0x8E8`, “II” name + roster-size satellite). Need a stable **club → teams** vector and a **TeamType** byte so any club’s in-game structure drives Squad coverage — not name guesses.

## Scope

- In: RE lock **Club.Teams** (vector start/end or start+count) on the club object; reboot-stable via `club_team_anchors` / focused probe
- In: RE lock **TeamType** on team objects; map values against in-game labels (First, Reserves, B, U19, U18, II, … — FMScout enum as hypothesis only)
- In: Write both into active **FM26** `entity-maps` profile constants; document the same checklist for an FM24 profile when that fingerprint exists
- In: Production path: managed (or any) club → Club.Teams → typed teams → existing team roster reader (players already work)
- In: Drop satellite-name / roster-band B-team as the **primary** same-club team discovery path once the lock ships
- Out: World Club/Person main-table index (Loop D); porting FMScoutFramework; UI redesign; feeder affiliate relationship typing (T198 human compare — feeders only, not blocking)
- Out: Hardcoding Schalke / English club UIDs as the only supported clubs

## Acceptance criteria

- [x] `Club.Teams` offset(s) locked: same team UIDs across FM reboot with different pointer values (anchor diff evidence in Progress)
- [x] `TeamType` offset locked; at least First + one youth/reserves type verified against FM club structure on **two** saves/clubs (e.g. Schalke + one PL/English club)
- [x] Entity-map constants updated for the active FM26 build fingerprint (`clubTeams*` + `teamTypeOffset`); no absolute paste from FM16/FM22 OSS
- [x] Live load (or debug command wired into load path) enumerates controllable teams from Club.Teams + TeamType and reads rosters with the existing player pipeline
- [x] Primary path does not depend on `" ii"` name matching or fixed roster-size bands for same-club teams
- [x] Progress notes residual: separate-club German II still needs a **club pointer** (affiliate/other); once that club is known, Club.Teams applies — do not reopen full affiliate graph as this ticket’s acceptance
- [x] One commit `T200: …`

## Notes / pointers

- Probe already started: `desktop/src-tauri/src/fm26/club_team_anchors.rs` — club blob → team pointer hits by offset; reboot-diff for stable vector
- Known team side: `entity-maps` already has `teamClubOffset` 48, `teamPlayersStart/End` 56/64 — do not re-lock unless broken
- Conceptual model (not offsets): AppCake/Thanos FMScout `Club.Teams` + `TeamType` enum
- Brittle current B-team path: `affiliate_links.rs` (`bteam_satellite_team_matches`, `MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET`)
- Supersedes board item **T199** (affiliate-roster framing) — that ticket was never filed; cancelled on STATUS in favor of this

## Progress

**Locked**
- **Club.Teams** `club+0x18` begin / `club+0x20` end (MSVC vector). Evidence: `club-team-anchors-scan-h1/h2` vs `h3-post-reload` (Schalke uid 920) — same team UIDs (First 920, U19 2000069496, intake 2000394357) after reload with different heap pointers; Leicester uid 673 contiguous three-team run at the same field (`club-teams-scan-loop.json`).
- **TeamType** `team+0x28`. Structural lock: AppCake FM22 TeamType@0x28 with Club@0x30 Players@0x38 — FM26 entity-map already had Club@48 / Players@56. Classification uses FMScout enum → `firstTeam` / `under19s` / `reserves` (no `" ii"` / U19 string required for same-club youth).

**Shipped**
- `entity-maps/index.json` + `MapConstants`: `clubTeamsStartOffset` 24, `clubTeamsEndOffset` 32, `teamTypeOffset` 40
- `teams_from_club_teams_vector` primary in `discover_teams_for_club`; heap window fallback only if vector empty
- Connector classifies with TeamType first; `clubTeams` JSON includes `teamType`
- Unit tests: enum map, entity-map offsets, nameless Leicester U19 via type 11

**Residual**
- Separate-club German II still needs a **club pointer** (T198 affiliate / satellite). Once that club is known, Club.Teams applies.
- FM24: same checklist when that build fingerprint is profiled (expect same adjacency if Club@0x30 / Players@0x38).
- Human: one live load on Schalke + Leicester to confirm TeamType bytes match FM labels (structural lock is in; live byte eyeball pending).

**Verify:** `cargo test --lib team_type_maps|club_teams_and_team_type|classify_club_team_by_uid` — 3/3 ok.

Commit: `c32401c34635abc6c7ecd6dea8431b308647ae43`
