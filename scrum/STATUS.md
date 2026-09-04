# Status

Last updated: 2026-09-04 (T207 done — Squad back restore)

## Now

**T205 in_progress (auto)** — fix roster `person_unresolved` drops via FSS person-class / PLAO on Club.Teams path.

**T206 ready (P2)** — tab labels as in-game; TeamType + known team name fields when club-name collision.

**Human FMLE A/B** — affiliate flags for separate-club II (after T205/T206).

**T190 parked** — Save ID in RAM before save-copy CA path.

**Deferred:** T139 theme. T162 trophy cabinet. T124 quiet dev launch. Loop D full-world **load** still parked; archive `.cursor/rules/fm-live-read.mdc` is the knowledge store for T205/T206.

## Board

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| T205 | Roster — fix person_unresolved drops (First XI) | in_progress | 1 | owner: auto |
| T206 | Club.Teams — in-game team display names | ready | 2 | TeamType / name collision; no world index |
| T190 | Development all-time from Progress Report CA strip | blocked | 2 | **parked** — need Save ID in RAM before `.fm` pick |
| T124 | Quiet dev launch | ready | 9 | behind Loop A |
| T139 | FMT visual theme | deferred | — | overlapped |
| T162 | Player trophy cabinet | deferred | — | backlog |

## Cancelled / superseded

- **T199** Reserves — B-team affiliate rosters — **cancelled** (never filed). Controllable teams = Club.Teams + TeamType (T200). Separate-club II = T203+.

## Recently done

- **T207** Squad — restore team tab + scroll on profile Back
- **T204** Squad — status filters + rosterLen in Settings (tab paren counts → filter row)
- **T203** RE — affiliate squad-tab flag bytes (FMLE A/B probe + diff; production unwired)
- **T202** Squad face-cache freshness — remap `from=` / source mtime revalidation on warm
- **T201** Production load — Club.Teams only; drop B-team heuristic + heap fallback; first-team-first order
- **T200** Lock Club.Teams (`club+0x18/+0x20`) + TeamType (`team+0x28`); production vector-first team discovery
- **T198** Club affiliate graph RE — `debug_scan_club_affiliates` forward/back links + relationship u32 candidates
- **T196** U19 squad — GS full index on load + contract-team U19 promote + Squad subtabs
- **T194** GM advises Sell vs Loan from squad avg CA
- **T193** Loans club logo pill + profile logo = active (loan) club
- **T192** GM desk = Squad twin filtered to move-on (PA≤140, headroom≤8)
- **T191** Loans age + loan club honesty (game-date fallback + Loan club on desk/profile)
- **T189** Loans desk = outgoing `loanedOut` players (Squad twin)
- **T188** Attr deltas in load pipeline (recent → Attributes, all-time → Development)
- **T187** Invalidate attr history poisoned by old rounding (v2 store)
- **T186** Development plot color match, hover values, all-time Δ layout fix
- **T185** Development content = plot + desk only (zero chrome)
- **T182** Live Squad = at-club match squad only (`loanedOut` via person loan agreement)
- **T184** Development desk compact single-page (all-time Δ desk + plot)

## Loop

FM → FMT Dashboard/Squad → player Attributes / Development → Loans (outgoing) → GM (Sell / Loan vs avg CA) → HoYD (high-PA groom) → (later) Tactic / TD / world.
