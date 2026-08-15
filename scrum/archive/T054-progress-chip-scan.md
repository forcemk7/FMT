---
id: T054
title: Progress — HA tones, selection chrome, dropdowns
status: done
priority: 3
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T051]
---

# T054 — Scan chips like the HA table; selects instead of cycling pills

## Why

User is on Progress to read the same HA numbers as Personalities. T051 reserved delta is good but tight. Chip values are uncolored; selected chips use accent wash. Twin cycling pills still mix verb vs state.

## Scope

- In: More space in the delta column (gap / padding) so `+2` is readable next to the value
- In: Chip **values** use existing `attributeTone` rules (good >14, bad <6; CON inverted). Same classes as the HA table (`good` / `bad`). Non-HA 1–20 attrs use the same thresholds; CON invert only on controversy
- In: Selected chip chrome is **not** the accent fill. Neutral outline / ink border. Series **swatch** still matches the chart line. Numbers stay tone-colored
- In: Replace the two cycling pills with native `<select>`s (same control family as HA filters). Options show **current state**: Show all | Hide all; Recent | All time. Mixed/default visible chips display as Show all. No third option. Chart path unchanged
- Out: New color scale. New charts. Accent restyle of the whole app. Suggest. Personalities sorted-column highlight (different view — not this ticket)

## Acceptance criteria

- [x] Delta slot has more padding/gap than T051; empty delta still holds the column
- [x] Pro 18 is good-colored; CON 18 is bad-colored; 12 is uncolored — same as Personalities
- [x] On-chip (plotted) vs off-chip is visible without a colored wash over the numbers
- [x] Two `<select>`s: choosing Hide all hides chips and the select still reads Hide all; Recent vs All time still switches chip deltas as T050/T051

## Notes / pointers

- Tone: `attributeTone` in `src/domain/attributes.ts`; HA table applies `td.classList.add(tone)` in `web/main.ts`
- Chips: `appendAttrToggle` / `.squad-evo-toggle.is-on` in `web/main.ts` + `web/styles.css`
- Pills: `#squad-evo-visibility-pill` / `#squad-evo-window-pill` → `<select>`; steal `.ranker-filter-row select`
- Do not invent a new selected color. Selection = chrome; tone = data

## Progress

- Delta column gap/padding bumped; empty slot still reserved.
- Chip values use `attributeTone` (CON invert); other 1–20 attrs share the same floors.
- Selected chips: ink border, no accent wash. Swatch still matches the chart series.
- Cycling pills replaced with Show all | Hide all and Recent | All time `<select>`s (current state). Chart path unchanged.
- Verified: `npx vitest run tests/attribute-evolution.test.ts tests/ha-history-store.test.ts tests/squad-route.test.ts` (16 passed).
