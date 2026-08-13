---
id: T013
title: Personality combo must not label Born Leader without Det/Lea=20
status: done
priority: 1
owner: worker
claimed_at: "2026-08-12T22:08:00+02:00"
started_at: "2026-08-12T22:09:00+02:00"
completed_at: "2026-08-12T22:11:00+02:00"
depends_on: []
---

# T013 — Personality combo must not label Born Leader without Det/Lea=20

## Why

**Loop break (behavior):** Domenico Gilson (UID `2002200653`) card shows **Born Leader / Evasive, Reserved** (HAS 15.71). In-game Det=**14**, Lea=**16** — Born Leader catalog requires Det=20 and Lea=20. Ranking the wrong personality breaks Mentoring and squad HAS trust.

Likely cause: `comboFeasibleForAttrs` only **pins known** attrs. When Det/Lea are missing from `rosterPersonalitySignals` (Attributes UI shows HA pack only for Gilson — no Det/Lea), Born Leader stays “feasible,” then wins on tight bands vs Light Hearted / others. Alternate: `attributeHistory` tip overrides with foreign Det=20 decoy (see `rosterPersonalitySignals` comment).

## Scope

- In: squad personality match must **refuse** personalities whose required Det/Lea (or other pinned bands) are unmet **or unknown** when the catalog band is non-full (esp. Born Leader, Leader, Charismatic Leader class)
- In: Gilson must not show Born Leader given FM Det 14 / Lea 16 (or missing Det/Lea must show incomplete / non-Born-Leader inference)
- In: document whether tip vs live mental caused the mislabel
- Out: Dynamics; reading FM personality string from save (still inferred); U19 loans (T012); media 2-row card polish

## Acceptance criteria

- [x] Gilson (or fixture with Det≠20/Lea≠20 + HA matching Evasive/Reserved) is **not** labeled Born Leader
- [x] Missing Det or Lea cannot make a Det=20/Lea=20-only personality the winning combo
- [x] Regression test: Born Leader requires known Det=20 and Lea=20
- [x] Progress notes root cause (missing pin vs tip decoy vs other)

## Notes / pointers

- `web/roster-data.ts` `rosterPersonalitySignals` (tip mental preferred)
- `web/main.ts` `matchPersonalityComboFromAttrs` / `comboFeasibleForAttrs` in `src/inference/match-combo.ts`
- Catalog: `src/data/personalities.ts` Born Leader bands 20/20; Light Hearted fits Gilson HA pack better once Det≤17
- **FM GT (Personal tab):** Domenico Gilson = **Light-Hearted** / **Evasive, Reserved** — confirms card label is wrong, not user guess
- User: Attributes PERSONALITY pack Amb15 Loy15 Pre18 Pro16 Spo16 Tem13 Con5 — plausible; Det/Lea not shown there
- Reading FM personality/media **strings** from the save is **not** in this ticket (open RE; product today never extracts them)

## Progress

**Root cause:** missing-pin, not tip decoy. `comboFeasibleForAttrs` → `pinKnownAttrs` only constrained attrs that were present; null Det/Lea left Born Leader’s 20/20 bands open. Tight-band tie-break then preferred Born Leader over Light Hearted for Gilson’s HA pack × Evasive, Reserved.

**Shipped:** After personality×media band apply + pin, refuse any combo whose non-full band still lacks a known finite attr (`src/inference/match-combo.ts`).

**Verified:** `npm test -- tests/match-combo.test.ts` — 12/12 pass, including T013 cases (missing Det/Lea → not Born Leader; Gilson Det14/Lea16 → Light Hearted × Evasive, Reserved only).
