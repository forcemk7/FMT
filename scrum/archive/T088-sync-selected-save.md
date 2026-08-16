---
id: T088
title: Sync belongs to the selected save
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-16T05:29:00+02:00
started_at: 2026-08-16T05:31:00+02:00
completed_at: 2026-08-16T05:42:00+02:00
depends_on: []
---

# T088 — Sync belongs to the selected save

## Why

Loaded save and in-flight extract are detached. Start sync on save A, select save B in Manage saves, extract finishes → UI jumps back to A. Cross-save is dishonest: you think you are looking at B. Sync is a **per-save** activity; the dropdown is the tree.

## Scope

- In: `web/main.ts` (`refreshSaveFromDisk`, `persistExtractResult`, `maybeRefreshActiveSaveFromDisk`, `setRosterSyncing`, Manage saves menu) + `web/roster-store.ts` `upsertRoster` (today always sets `activeSaveName` to the upserted save)
- In: **Start** sync only for the save that is **Active** in Manage saves. One extract at a time (T072). If A is syncing, do not start B
- In: once started, **let it finish**. Persist into **that** save’s slot. If the user has selected another save, **do not** call `applyActiveRosterFromStore` / steal `activeSaveName`
- In: move sync chrome into the Manage saves dropdown (row for the save that is extracting: Syncing + progress). Global status strip is not the owner
- Out: extract Python. T085 HA/CA. T086 loans. New extract. Abort-on-switch. Two Pythons. Suggest

## Acceptance criteria

- [x] Selecting another save while A is syncing keeps the Squad view on the selected save; when A finishes, slot A updates in the menu, Active does not jump back to A
- [x] Auto-sync / poll / Update only **starts** for the current Active save. `rosterBackgroundSyncQueued` must re-check Active before starting the next extract
- [x] In-flight extract is allowed to finish (no abort because the dropdown changed)
- [x] Syncing state is visible on that save’s row in Manage saves, not as a detached header sync
- [x] One git commit `T088: …` on FMT/

## Notes / pointers

- `upsertRoster` sets `activeSaveName: entry.saveName` — that is the steal
- `persistExtractResult` → `applyActiveRosterFromStore` always reapplies the extracted save
- `setRosterControlsDisabled` / `is-syncing` live on `#roster-save-controller`; menu is `#roster-saves-menu`
- Pattern: a download continues in the background; the page you switched to stays on screen

## Progress

Shipped: `upsertRoster` keeps the current Active save. Disk extract starts only for Active (one Python). In-flight extract finishes into that slot; if the user selected another save, persist does not call `applyActiveRosterFromStore` / steal Active. Manage saves row shows Syncing + progress; header strip is not the owner. Queued auto-sync re-checks Active before the next extract. Update on a non-Active row does not start B.

Verified: `npx vitest run tests/roster-store-ingest.test.ts tests/t088-sync-selected-save.test.ts tests/squad-chrome-t075.test.ts tests/loans-roster.test.ts tests/squad-ha-table.test.ts` (14 + chrome/HA/loans). No extract Python change. No committed `.fm`.
