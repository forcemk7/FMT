---
id: T061
title: Progress HA deltas compound across extracts
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T048]
---

# T061 — Det/Lea + pack HA accumulate by gameDate

## Why

After groups exist in FM, the check is extract again → see whether HA moved. Pack Pro–Con already snapshot by in-game date. Det/Lea (the mentoring HA) do not: they stay on the CA strip, which compact keeps as one tip, so chips show a value and no running delta. II/U19 kids are worse (tip-only on ingest).

## Scope

- In: Each Career Save extract upserts Det/Lea onto the same `ha-history-store` snapshot as the pack (club + gameDate; same date replaces)
- In: Progress chips `mental.determination` / `mental.leadership` read that series, not `attributeHistory`
- In: Chart treats Det/Lea as HA (with pack), not as CA — selecting Det must not swap the chart to the tip strip
- In: Default Progress chips = HA table keys (Det, Lea, Pro, Amb, Spo, Pressure, Loyalty, Tem, Con) when those snapshots exist
- Out: New charts. CA/tech/physical compounding. Changing Recent vs All time math (Recent = last two dates, All time = first finite vs latest). Suggest. Rebuilding the pane. Talent tab

## Acceptance criteria

- [x] Two extracts, same player, gameDates D1 then D2, Det 14 → 16: All time Det delta is **+2**; Recent is **+2** (only two points)
- [x] Three dates 14 → 15 → 17: Recent Det **+2**, All time **+3**
- [x] Same gameDate re-extract replaces that point (no duplicate date); series length unchanged
- [x] II/U19 player with no CA strip still gets Det/Lea deltas from extract snapshots
- [x] Pro–Con still use the existing pack series (do not fork a second store)
- [x] CA/tech chips still use the in-save strip; they stay one-tip after compact (unchanged)

## Notes / pointers

- `web/ha-history-store.ts` — `HA_PACK_KEYS` / `packValuesFromGeneral` / `haSnapshotsToHistoryPoints` (put Det/Lea under `mental` on the point so `historyPointValue` keeps `mental.determination`)
- `historyForAttrId` / `chartHistoryAndAttrs` in `web/main.ts` — today `general.*` → HA store, anything else → CA strip; Det is `mental.*` so it misses
- `roleDefaultEvolutionAttrs` still uses `defaultEvolutionAttrIds` (CA). Prefer pack + Det/Lea
- Tests: `tests/ha-history-store.test.ts`, `tests/attribute-evolution.test.ts`
- Needs two different in-game dates to show a delta; one extract → value, empty delta (correct)

## Progress

Shipped: extract upserts Det/Lea onto the same club+gameDate snapshot as the pack (`mental` nest). Progress chips `mental.determination` / `mental.leadership` read that series; chart stays on HA when only Det/Lea/pack are selected. Default chips = HA table keys when snapshots exist. CA/tech still use the in-save strip.

Verified: `npx vitest run tests/ha-history-store.test.ts tests/attribute-evolution.test.ts` (20 passed). Residual: one extract still shows value and empty delta; existing localStorage points pick up Det/Lea on next backfill from stored rosters.
