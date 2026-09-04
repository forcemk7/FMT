# Status

Last updated: 2026-09-04 (T213 done — Diagnostics + in-game date; T212 still in_progress)

## Now

**T212** Load managed affiliate squads (II / NPL) — cursor-agent. Filter = Main+Permanent+Players Move Freely (Melbourne confirms same pattern). Wire into production Club.Teams path.

**Human:** Melbourne NPL **PASS** (total 55). Load Schalke FM24Continue — expect First + U19 + II. NPL/II tab labels later.

**T208** Five-band attr tones — Super deferred; await archive confirm.

**T190 parked** — Save ID in RAM before save-copy CA path.

**Deferred:** T210 Squad card/list density. T139 theme. T162 trophy cabinet. T124 quiet dev launch. Empty Youth(0) tab. Loop D full-world load parked.

## Board

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| T212 | Load managed affiliate squads (II / NPL) | in_progress | 1 | cursor-agent — Main+Permanent+PMF |
| T208 | Five-band attr tones + hot-amber super | in_progress | 2 | cursor-agent — Super deferred; await archive confirm |
| T190 | Development all-time from Progress Report CA strip | blocked | 2 | **parked** |
| T209 | Squad — roster status as single select | ready | 5 | after T208; multi→single |
| T124 | Quiet dev launch | ready | 9 | behind Loop A |
| T210 | Squad — card / list density toggle | deferred | — | not now; after T209 if unfrozen |
| T139 | FMT visual theme | deferred | — | overlapped |
| T162 | Player trophy cabinet | deferred | — | backlog |

## Cancelled / superseded

- **T199** Reserves — B-team affiliate rosters — **cancelled**. Separate-club II = T203+.

## Recently done

- **T213** Diagnostics — rename, game date, load-order fields
- **T211** Club.Teams — map TeamType 21 (Youth; Melbourne Youths 15)
- **T206** Club.Teams — in-game team display names (TeamType when name equals club; keep real `… U19`)
- **T207** Roster — load all First Team Players slots (UID floor; Liverpool 39=39)
- **T205** Roster — FSS person-class/PLAO resolve
- **T204** Squad — status filters + rosterLen in Settings
- **T203** RE — affiliate squad-tab flag bytes (probe; unwired)
- **T202** Squad face-cache freshness
- **T201** Production load — Club.Teams only
- **T200** Lock Club.Teams + TeamType
- **T198** Club affiliate graph RE
- **T196** U19 squad live read
- **T194** GM Sell vs Loan
- **T193** Loans club logo pill
- **T192** GM desk move-on
- **T191** Loans age + loan club
- **T189** Loans desk
- **T188** Attr deltas in load pipeline
- **T187** Invalidate attr history poisoned by old rounding (v2 store)
- **T186** Development plot color match, hover values, all-time Δ layout fix
- **T185** Development content = plot + desk only (zero chrome)
- **T182** Live Squad = at-club match squad only (`loanedOut` via person loan agreement)
- **T184** Development desk compact single-page (all-time Δ desk + plot)

## Loop

FM → FMT Dashboard/Squad → player Attributes / Development → Loans (outgoing) → GM (Sell / Loan vs avg CA) → HoYD (high-PA groom) → (later) Tactic / TD / world.
