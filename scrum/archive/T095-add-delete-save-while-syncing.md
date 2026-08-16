---
id: T095
title: Add or delete a save while another extract runs
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-16T08:40:00Z
started_at: 2026-08-16T08:45:00Z
completed_at: 2026-08-16T08:50:00+02:00
depends_on: [T088]
---

# T095 — Add or delete a save while another extract runs

## Why

Owner cannot smoke T094 (native Career) because König is **Syncing** and the app blocks the swap. **+** is disabled for the whole extract (`setRosterControlsDisabled`). **Delete** on that row is disabled (`deleteBtn.disabled = isSyncing`). T088 only stopped persist from stealing Active. It did **not** unlock Add/Delete. Poll can restart König the moment one extract idles, so there is no gap to click +.

Do not invent another extract recipe. This is chrome + one-Python queue.

## Scope

- In: **+ stays usable** while A is extracting. File picker opens. Chosen file **B** waits for the current Python, then extracts B. Auto-sync of A must **not** jump that queue (T088 re-check Active is not enough if Active is still A)
- In: **Delete** on the extracting row **aborts** that Python (existing leftover-pid kill) then removes the slot. Other rows already deletable
- In: owner does **not** have to delete A to add B. Two slots. T072 one Python. T088: A finishes into A; selecting B does not steal Active back to A
- Out: extract Python recipes. Two Pythons. Abort-on-switch without Delete. T087. www. Committing `*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`

## Acceptance criteria

- [x] While A shows Syncing: **+** opens the picker (not disabled / not “wait for extract”)
- [x] Choosing B while A is extracting: after A finishes, **B** starts — König auto-sync does not start first
- [x] Delete on the Syncing row: extract process gone, row gone, **+** works without a full wait
- [x] Vitest chrome guards (same style as T088). No extract Python change unless abort/kill already lives there
- [x] One git commit `T095: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- `web/main.ts`: `setRosterControlsDisabled` disables `#roster-upload-btn`; `syncRosterSavesMenu` sets `deleteBtn.disabled = isSyncing`; `uploadFirstTeamSave` awaits `whenRosterRefreshIdle` then extracts
- T072: Vite start already kills leftover extract pid — reuse for Delete-abort
- Pattern: a download can finish in the background; you can still add another file; cancel removes the in-flight one
- T087 stays frozen until a native extract writes a non-empty `players[]`

## Progress

Shipped: **+** stays usable while A extracts (picker not disabled). Chosen B waits for the current Python; König auto-sync does not start first if a + upload is queued or the picker is open. Delete on the Syncing row aborts the fetch, `killStaleExtractPid`, then removes the slot. T072 one Python. T088 persist unchanged.

Verified: `npx vitest run tests/t095-add-delete-save-while-syncing.test.ts tests/t088-sync-selected-save.test.ts tests/roster-store-ingest.test.ts tests/squad-chrome-t075.test.ts` (20). No extract Python recipe change. No committed `.fm`.
