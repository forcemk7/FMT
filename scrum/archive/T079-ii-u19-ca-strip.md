---
id: T079
title: II/U19 Progress keeps in-save CA history
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-08-16
started_at: 2026-08-16
completed_at: 2026-08-16
depends_on: []
---

# T079 — II/U19 CA strip is the in-save history, not one tip

## Why

Used Progress on II/U19: pack HA has **2** extract points, but player attributes collapse to **1** even though FM shows a long Progress Report strip. T066/T068 tip-only’d subunit CA to save localStorage. That lie is now the used screen.

## Scope

- In: Extract + persist keep II/U19 `attributeHistory` the same way as FT (in-save CA strip)
- In: Quota compact may **trim** points (24 then 8) like FT. Tip-only II/U19 only if trim still overflows
- Out: T077 www. Inventing dates. Mixing pack HA onto the CA x-axis. Changing FT strip routing

## Acceptance criteria

- [x] After extract + persist, an II or U19 player with an in-save strip has **more than one** CA point on Progress (same as Strength/Det), not a single tip
- [x] Pack HA still uses extract snapshots (`fmt.ha-history.v1`)
- [x] Quota path does not wipe FT strips; II/U19 stay >1 unless last-resort overflow
- [x] One git commit `T079: …` on FMT/

## Notes / pointers

- `tip_only_attribute_history` on II/U19 in `scripts/extract-first-team-fast.py`
- `tipOnlyAttributeHistory` in `persistExtractResult` (`web/main.ts`) and `compactSubunitsForStorage` (`web/roster-store.ts`)
- Tests: `tests/roster-store-ingest.test.ts` (T068 expected II/U19 length 1)

## Progress

- Extract no longer tip-onlys II/U19. Persist stores the in-save CA strip like FT.
- Quota: trim all squads to 24 then 8; tip-only II/U19 only if that still overflows. FT never collapses to 1.
- Pack HA unchanged (`fmt.ha-history.v1`).
- Verified: `npx vitest run tests/roster-store-ingest.test.ts` (9 passed). Re-extract after restart `npm run dev`.
