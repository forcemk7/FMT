---
id: T216
title: Live isRegen from origin flag (not UID band)
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-09-05
started_at: 2026-09-05
completed_at: 2026-09-05
depends_on: []
---

# T216 — Live isRegen from origin flag (not UID band)

## Why

Personality × media labels mismatch in-game when regen-only personalities (Unambitious, Mercenary, …) should win. `livePersonalityLabels` hardcodes `isRegen: false`. UID ≥ 1.9B is **not** law — DB wonderkids (Yamal `2000256231`, …) share that band with regens. Face `r-{uid}` is graphics only. Need a durable person/player **origin signal** (flag/bit preferred), then feed the **one** existing matcher.

## Scope

- In: Resolve known **DB** UIDs in live RAM + managed **U19** players as regen ground truth; byte-diff person (+ player if needed) for a uniform split
- In: Map validated signal → `LivePlayer.isRegen` (or equivalent) → `MatchableAttrs.isRegen`; **remove** the `false` hardcode
- In: Keep a single label path (`livePersonalityLabels` → `matchBestPersonalityCombo`)
- In: Update `scrum/FM-ECOSYSTEM.md` / entity-map note if a field locks
- Out: UID-band as product law; second personality algo; staff-as-control; face-pack `r-` as regen truth; Loop D full-world UI

## Acceptance criteria

- [x] Probe (or equivalent) can locate the five DB UIDs below and U19 regen samples on a loaded save, and report candidate origin offset(s) that uniformly split DB vs regen
- [x] Production live load sets `isRegen` from the validated signal (not hardcoded false, not UID band)
- [x] Unit/regression: regen attrs → Unambitious/Mercenary class when `isRegen: true`; non-regen path unchanged for Gilson-class fixture
- [x] One commit `T216: …`

## Notes / pointers

**Lock:** `person+0xD5` — database players read `1`, game-generated read `0`. `isRegen = (byte == 0)`.

Reject: UID band; face `r-`; FSS `person+0x18` bit `0x08` (youth team, not newgen).

## Progress

- Probe resolved all 5 DB UIDs + 8 U19; first-team×16 also `0` at `0xD5`.
- Wired live `isRegen` + personality-labels; vitest 8/8; cargo check ok.
- Commit SHA filled after git commit.
