---
id: T066
title: Progress Det/Lea from CA strip, not HA snapshots
status: done
priority: 1
owner: auto
claimed_at: 2026-08-15T01:16:00Z
started_at: 2026-08-15T01:16:30Z
completed_at: 2026-08-15T01:22:00Z
depends_on: [T061, T063]
---

# T066 — Det/Lea use the attributes-card strip; pack stays on extract snapshots

## Why

Jan Lundqvist: Det selected → flat line at **6**. T061/T063 put Det/Lea on the same extract-snapshot series as Pro–Con. Once that store has ≥2 dates, Det never reads the in-save Progress Report strip (the attributes card), which is what actually moved in FM. User: only pack HA (no in-save strip) should use our snapshots.

## Scope

- In: `mental.determination` / `mental.leadership` always use `attributeHistory` (CA strip), same as Strength. Not `ha-history-store`, even when that store has ≥2 dates
- In: `isHaProgressAttrId` = `general.*` pack only. Remove T063 Det/Lea fallback (`historyForHaProgressAttr` / `chartHistoryForHaSelection` special case)
- In: Default Progress chips = pack keys only (not Det/Lea). Click Det/Lea → CA chart
- Out: Un-compacting II/U19 CA (quota). New charts. Plotting pack and Det on one mixed x. Suggest. Rebuilding the pane

## Acceptance criteria

- [x] Lundqvist (or any FT with a Det strip): select Determination → plot is the CA series, not a flat extract-snapshot line at one value
- [x] Pack chips (Pro/Amb/…) still use `fmt.ha-history.v1` by gameDate
- [x] HA store with ≥2 dates does **not** steal Det/Lea off the CA strip
- [x] II/U19 tip-only Det stays one point (no quota blow-up)
- [x] Selecting only pack attrs still charts HA snapshots; selecting Det does not chart pack on the CA strip

## Notes / pointers

- `isHaProgressAttrId` / `historyForHaProgressAttr` / `chartHistoryForHaSelection` / `defaultHaEvolutionAttrIds` in `web/attribute-evolution.ts`
- `historyForAttrId` / `chartHistoryAndAttrs` in `web/main.ts`
- Tests: `tests/attribute-evolution.test.ts` (T061/T063 Det-as-HA cases invert)

## Progress

Shipped: `isHaProgressAttrId` is pack `general.*` only. Det/Lea always read `attributeHistory` (same as Strength). Removed T063 `historyForHaProgressAttr` / `chartHistoryForHaSelection`. Default Progress chips = pack keys; click Det/Lea → CA chart. Pack-only selection still uses `fmt.ha-history.v1`. Mixed Det+pack charts CA attrs only (no mixed x).

Verified: `npx vitest run tests/attribute-evolution.test.ts tests/ha-history-store.test.ts` — 25 passed. Inverted T061/T063 cases: HA ≥2 dates does not steal Det; II/U19 tip-only stays one CA point.
