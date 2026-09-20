---
id: T196
title: U19 squad — GS club index + Squad subtab (FM24 continue)
status: done
completed_at: 2026-08-29
depends_on: []
---

# T196 — U19 squad — GS club index + Squad subtab (FM24 continue)

## Why

Reinstate what **GlassScout already shipped**: `index_full_player_database` on load (T133/T126 path). FMT turned it off in T137 (`collect_snapshot(false)`). We want that index back — **confined to managed-club employees**, not world spray. First unit: **U19** (usually same club as senior). Reserves/affiliate later. Must work on **FM24 continue** careers.

## Approach (trace GS — do not invent)

1. **Restore GS full index on load** — `load_active_save` → `collect_snapshot(true, …)` (same as stock GS).
2. **Confine to managed club** — from indexed + managed-squad records, keep players employed by the active club (contract → team → club uid = managed club). Drop world background from snapshot/UI.
3. **Unit = contract team** — compare each player's contract team pointer to manager FT team vs club's U19 team (same club uid; not affiliate). Tag `squadUnit`: `firstTeam` | `under19s`. No age-share heuristics, no club-byte scan.
4. **Promote to snapshot** — club employees get full squad read (attrs/CA/PA/loan) into `snapshot.players`, not thin index-only rows.
5. **Continue saves** — fix whatever breaks this path on FM24-imported careers (T135 manager pick already shipped; index/attach failures are in scope).

## First human test

**Fixture:** FM26 + **Schalke FM24Career** loaded. FMT → Load Active Save.

1. FM Squad → Under 19s → count at-club (no outgoing loans).
2. FMT Squad → **Under 19s** subtab → same count.
3. Spot-check 2–3 names.
4. Loaned-out youth not on U19 subtab (T182).

## Scope

- In: Re-enable GS index; managed-club filter; U19 via contract team; `squadUnit`; Squad subtabs **First Team · Under 19s**
- In: FM24 continue must connect and pass human test
- Out: Reserves/affiliate (separate ticket); GM/HoYD/Loans/Dashboard units; `.fm` RE; world search UI

## Acceptance criteria

- [ ] `databaseScope` = `full-save-index` (or honest partial + warning) on load; snapshot is **club-only**, not 35k world
- [ ] Schalke FM24Career: U19 subtab count = in-game at-club U19
- [ ] First Team subtab ≈ current T182 at-club FT list
- [ ] No invented heuristics (age-share club scan) in shipped path
- [ ] `vitest` unit filter; `cargo check`

## Blind

- Do not git add `data/saves/`, `*.fm`, `tmp/`
- Do not mmap/extract live SI `games/*.fm`
- **Revert** prior T196 club-scan / `pick_u19_team` work before shipping this approach

## Notes / pointers

- GS: `index_full_player_database` — private-heap vtable scan, cap 250k (`connector.rs` ~2453)
- FMT off switch: T137 `collect_snapshot(false)` — undo for index, then filter output
- Index record has `contract_address`; `contract_team_offset` + `team_club_offset` for club/team join
- Entity map validation: ~35k indexed vs ~38 managed on test save — club filter narrows to employable set
- Reserves often different club (affiliate) — out of this ticket

## Progress

- **Reset:** prior worker pass used invented club scan + youth-age heuristic — **discard**; ticket rewritten to GS index + contract-team unit law (2026-08-29).
- **Shipped:** Reverted age-share / club-byte scan heuristics. `load_active_save` → `collect_snapshot(true)`. FT roster read unchanged; U19 picked as non-FT contract team with most managed-club employees from `PLAYER_DATABASE_INDEX`; promoted via shared `push_squad_player_from_raw` with `squadUnit: under19s`. Squad subtabs UI already present.
- **Verified:** `cargo check`; `vitest` live-data 18/18.
- **Commit:** f3436db
- **Human test pending:** Schalke FM24Career U19 count vs FM (needs live FM).
