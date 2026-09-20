---
id: T190
title: Development all-time from Progress Report CA strip
status: blocked
priority: 1
owner: null
claimed_at: "2026-08-27T21:50:00+02:00"
started_at: "2026-08-27T21:50:00+02:00"
completed_at: null
depends_on: []
---

# T190 — Development all-time from Progress Report CA strip

## Why

FM Progress Report (Player Report → Individual Training) shows complete attr development. Development desk must show **current − first Progress Report pack point**, not FMT Load history. Attributes recent stays on Load (frozen).

## Model

| Desk | Source |
|------|--------|
| **Attributes** recent | `fmt.attr-history.v2` Load change-points (**frozen**) |
| **Development** all-time | Save-copy CA strip (69-byte cards before `uid\|\|uid`) |

## Scope

- In: Copy selected career into `data/saves` → decompress (cached `.ca.bin`) → `build_ca_history` → stamp `allTimeAttrDeltas` / `caPackPointCount`
- In: Development desk reads those stamps only (no Load all-time fallback)
- Out: Changing Attributes recent; Mentoring; Loans

## Acceptance criteria

- [ ] Development Δ match Progress Report direction for a youth with known in-game movement (compare to FM arrows / first→now)
- [x] Attributes recent still from Load history (untouched)
- [x] Load ingest does not overwrite pack all-time with Load clock
- [ ] When save copy / strip missing: Development honest empty

## Progress

- RE: Progress Report = same 69-byte CA strip as `extract-first-team-fast.py` / `ca_history.rs` (proven on `dynamics-b.fm`: e.g. uid with 43 pack points)
- Live RAM person−20k lookback does **not** hold the strip; save-copy does
- Shipped: `fm26/save_ca.rs` — copy club-matched career → zstd cache → per-uid lookback → all-time stamp (unwired)
- Shipped: AttributeDesk recent=Load; allTime=pack only; `attachAttrDeltas` preserves pack all-time
- **Parked 2026-08-29:** Live RAM CA join + Game Details hunts = 0 hits. Save-copy blocked until **active save locked in RAM** (Live Editor Save ID `6770653` + metadata cluster), not mtime/club-name guess.

## Blockers

- **Parked:** need RAM lock on Live Editor save metadata (Save ID, club/player/staff counts) → then pick matching `.fm` for CA extract
- Do not ship save-copy path until save identity is proven

## HQ note (2026-09-15)

Not in FMT 1.28. Current cached-attribute-history approach (from Load Data onward) works well enough to ship; the current Attributes-desk display is not blocked on this. Locking the exact live-memory CA-progress-card offset is real, not speculative RE (owner has solved the equivalent for `.fm` save-file parsing before) — but the live-memory offset itself is still unknown and may be expensive to find. Revisit as a **community-fundable** item for a later version if there's appetite/funding for it post-1.28.
