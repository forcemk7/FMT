---
id: T107
title: Standardize pane thead + identical drop well
status: done
priority: 1
owner: cursor-worker
claimed_at: "2026-08-16T18:00:00Z"
started_at: "2026-08-16T18:05:00Z"
completed_at: "2026-08-16T18:15:00Z"
depends_on: [T105, T106]
---

# T107 — Standardize pane thead + identical drop well

## Why

T105/T106 shipped the shell and continue dates. Owner still sees uneven empty panes: column header vertical alignment / font size differ by tab, and the Drop a Career Save well is not in the exact same place on Squad / Loans / Mentoring / Progress.

## Scope

Chrome only. One shared thead look + one drop geometry.

- In: Shared CSS for empty (and filled, where thead is the pane head) column headers across all four tabs — same font-size, weight, letter-spacing, padding, vertical alignment. Column *sets* stay per-tab (Squad HA vs Loans Name/Unit/At, etc.)
- In: `.table-pane-drop` (or one shared empty host) sits in the **identical** slot under the thead on every tab — same top offset after thead, same horizontal inset, same height behavior. Switching tabs must not jump the drop box
- In: Vitest chrome guard that empty panes share thead + drop classes / structure
- Out: Extract. Save cards. Filled Loans cards / Mentoring board / Progress chart redesign. New columns. Theme rewrite

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** change drop / + identity upload behavior

## Acceptance criteria

- [x] Empty Squad / Loans / Mentoring / Progress: thead typography + row height match; drop well same class and same place (owner eye-check OK; vitest structure)
- [x] One git commit `T107: …` on FMT/

## Notes / pointers

- `.table-pane` / `.table-pane-head` / `.table-pane-drop` in `web/styles.css`
- Squad may still render HA thead inside `#roster-body` while others use `.table-pane-head` — unify so empty layout does not fork
- Steal: one table chrome token set (FM / spreadsheet header row)

## Progress

Shipped: all four empty tabs use `.table-pane-empty` → `.table-pane-head` + `.table-pane-drop`. Squad empty no longer forks thead into `#roster-body`. Shared thead tokens (font-size/weight/letter-spacing/padding/vertical-align) for pane heads and filled Squad HA head. Mentoring empty hides mentee strip + status so the drop does not jump. Drop / + still `feedRosterUpload`. Dead absolute `.roster-empty` CSS removed.

Verified: `npx vitest run` t107 + t105 + t104 + t103 + t075 (16 passed); `tsc --noEmit`. Restart `npm run dev`. No committed `.fm`.
