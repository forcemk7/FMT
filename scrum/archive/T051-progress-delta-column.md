---
id: T051
title: Progress — fixed delta column; Show/Hide is the next action
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T050]
---

# T051 — Name | delta slot | value; visibility pill says what click does

## Why

T050 prepends delta only when it exists, so `+2` sits on the tens digit of `15`. User: dedicated slot **{name}{delta}{value}**. Visibility pill currently names the **current** mode; they want the **next** mode (Hide all state → label Show all). Window pill stays **current** window: Recent on the button ↔ recent deltas.

## Scope

- In: Every attribute chip is `label | delta | value`. Delta column is always there (empty if 0/missing), fixed width so +12 / −3 / blank share one column — not shrinking into the value
- In: Visibility pill label = **what you get after click**. Hide-all → **Show all**. Show-all (and default mixed) → **Hide all**
- In: Window pill label = **what deltas show now**. **Recent** ↔ last two points. **All time** ↔ first finite vs latest. Do not invert this pill
- Out: New charts. Third visibility mode in the label. Suggest

## Acceptance criteria

- [x] Chips with and without deltas keep the value in the same column (1-digit and 2-digit values still align)
- [x] Order is name, then delta slot, then value
- [x] While all attrs are hidden, pill reads Show all; click shows all and pill reads Hide all
- [x] Button text Recent → chip deltas are recent; All time → all-time

## Notes / pointers

- `applyToggleDeltaMeta` in `web/main.ts` **removes** the delta node when empty (`meta.prepend` when present) — keep the node, clear text
- `syncEvoPills`: visibility is currently `none ? 'Hide all' : 'Show all'` — invert that one only
- CSS: `.squad-evo-toggle-delta` needs a reserved width (tabular-nums); `.squad-evo-toggle-meta` = delta then value

## Progress

- Chip meta is a two-column grid (delta | value). Empty/0 delta keeps the slot and clears text; values stay right-aligned with tabular-nums.
- Visibility pill is next action: hidden → Show all; mixed/show-all → Hide all. Window pill still names the current window (Recent / All time).
- Verified: `npx vitest run tests/attribute-evolution.test.ts tests/ha-history-store.test.ts tests/squad-route.test.ts` (14 passed). Chart path unchanged.
