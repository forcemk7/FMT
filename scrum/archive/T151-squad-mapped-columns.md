---
id: T151
title: Squad — mapped columns only; foot digits; CA/PA rings
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T151 — Squad — mapped columns only; foot digits; CA/PA rings

## Why

Loop A: Squad must show only fields we actually read. Empty unmapped columns are noise. Foot and Ability/Potential are already in the attr/CA blob — surface them honestly.

## Scope

- In: Preferred foot → Left/Right foot as **1–20** digits; label **Either** only when left == right; otherwise **Left** or **Right** by which is greater (no ±20 threshold)
- In: Drop Squad columns with no validated/candidate map path (form, contract/wage, value, condition, status/personality string, best-role while deferred)
- In: Keep mapped identity/position/foot; replace Rating proxy with dual rings **Ability** + **Potential** (CA/PA **1–200**); tone like attrs but on `/10` (160 tones as 16)
- Out: New RE for wage/form/value; HA column; re-enable full role catalogue on load; theme polish

## Acceptance criteria

- [x] Squad header/rows only show columns backed by mapped reads (plus Ability/Potential)
- [x] Foot cell shows Either | Left | Right per equality rule; left/right strengths available as 1–20
- [x] Ability and Potential rings use 1–200 values with attribute-style tones on tenths
- [x] No fake Unknown spam for deliberately unmapped fields

## Notes / pointers

- Foot: `attribute_bytes[24]/[25]` + `preferred_foot_label` in `fm26/parser.rs`; Squad UI `my-team-screen.tsx`
- CA/PA: already on player JSON (`currentAbility` / `potentialAbility`); entity-map candidate @ 612/614
- Tone: `attribute-tone.ts` — apply to `value/10` for CA/PA

## Progress

- Foot: display 1–20 via `display_attribute`; label Either/Left/Right by equality; emit `leftFoot`/`rightFoot`
- Squad: Player | Position (+ foot) | Ability | Potential | Details only
- Ability/Potential rings: 1–200, conic fill ×1.8°, attr tones on /10
- Verified: `cargo test preferred_foot`, `tsc --noEmit`
- Commit: _(filled after git)_
