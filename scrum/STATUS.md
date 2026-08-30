# Status

Last updated: 2026-08-30 (T198 done — affiliate graph RAM probe)

## Now

**Human verify T198** — Schalke save: invoke `debug_scan_club_affiliates`, compare `backLinksToManagedClub` vs FM Board → Affiliated Clubs (B Team vs Feeder types → `relationshipCandidates` u32).

**T199 ready** — load reserve rosters from typed B-team affiliates (blocked on T198 human compare).

**T190 parked** — blocked on RAM lock for Live Editor Save ID before save-copy CA path.

**Deferred:** T139 theme. T162 trophy cabinet. T124 quiet dev launch.

## Board

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| T199 | Reserves — B-team affiliate rosters | ready | 1 | after T198 human RE lock |
| T190 | Development all-time from Progress Report CA strip | blocked | 2 | **parked** — need Save ID in RAM before `.fm` pick |
| T124 | Quiet dev launch | ready | 9 | behind Loop A |
| T139 | FMT visual theme | deferred | — | overlapped |
| T162 | Player trophy cabinet | deferred | — | backlog |

## Recently done

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
