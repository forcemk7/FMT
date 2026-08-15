---
id: T050
title: Progress pills — delta left; Show/Hide; All time/Recent
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T048]
---

# T050 — Compact deltas; two cycling pills

## Why

User is on Progress to see HA shift. Attribute chips reserve empty space on the **right** for missing deltas. Show all / Hide all are two buttons. They want **{delta}{value}**, and one pill each for visibility and delta window.

## Scope

- In: Chip meta order is **delta then current value**. No reserved gap when delta is 0/missing (don’t keep a transparent min-width column)
- In: **One pill** cycles **Show all ↔ Hide all** (replace the two buttons). Label = active mode. Click flips. Drop the third “default” bounce if it fights a two-state pill
- In: **One pill** next to it cycles **All time ↔ Recent**. Label = active mode. Default **Recent** = current `attrValueAndDelta` (last two finite points). **All time** = first finite history point vs latest (`progress 0`, or `1` if 0 is empty)
- In: Deltas on the chips follow that window. Chart path stays; don’t rebuild axes
- Out: New charts. Suggest. CA zoo. Extra modes (custom range)

## Acceptance criteria

- [x] A chip with no change shows only the number, flush — no empty +/− slot on the right
- [x] A chip with +2 shows `+2` immediately left of the value
- [x] One visibility pill: Show all → click → Hide all → click → Show all
- [x] One window pill: Recent (two latest) vs All time (first vs latest); Yoan-class pack with 3+ snapshots differs between modes
- [x] Per-attribute on/off still works

## Notes / pointers

- `attrValueAndDelta` in `web/attribute-evolution.ts` — add a `window: "recent" | "allTime"` (or sibling). Tests there / `tests/` if an evolution spec exists
- Chip DOM: `appendAttrToggle` / `.squad-evo-toggle-meta` — delta `min-width` + `color: transparent` in `web/styles.css` is the empty-right bug
- Tools: `#squad-evo-show-all` / `#squad-evo-hide-all` in `web/index.html`

## Progress

- Chip meta is delta then value; missing/0 delta is omitted (no transparent min-width slot).
- One visibility pill cycles Show all ↔ Hide all (no bounce back to role-default). Per-attribute chips still exit the override.
- One window pill cycles Recent (last two finite) ↔ All time (first finite vs latest). Default Recent. Chart path unchanged.
- Verified: `npx vitest run tests/attribute-evolution.test.ts tests/ha-history-store.test.ts tests/squad-route.test.ts` (13 passed). Yoan-class 12/14/18 pack: Recent +4, All time +6.
