---
id: T104
title: Drop header Squad leftover; unified empty pane
status: done
priority: 1
owner: Auto
claimed_at: 2026-08-16T12:42:00Z
started_at: 2026-08-16T12:48:00Z
completed_at: 2026-08-16T13:05:00Z
depends_on: [T103]
---

# T104 — Drop header Squad leftover; unified empty pane

## Why

T103 shell is right. Owner still sees a leftover **Squad** pill in `.app-header` (duplicate of the tab). Empty panes disagree: Squad keeps column headers (good); Loans / Mentoring / Progress do not.

## Scope

- In: Remove the header **Squad** control (`#tool-nav` / `.tool-nav-btn`). FMT · club · date · + · saves · coffee. Tabs stay under the header
- In: When a tab has **no rows**, show that tab’s **column headers** and one shared empty body. Drop a `.fm` on the pane = the same identity upload as **+** (new save, not overwrite)

Empty headers (expectation, not a new filled layout):

| Tab | Thead |
|-----|--------|
| Squad | existing HA columns (keep) |
| Loans | Name, Unit, At |
| Mentoring | Group, Members |
| Progress | Name, CA, ΔCA, Det, ΔDet |

Shared body copy (one line, all four): `Drop a Career Save (.fm) here, or use +`

- In: Drop only while that pane is empty. Filled Loans cards / Mentoring groups / Progress chart stay as they are
- Out: Extract Python. HA column set. Save cards. Filled-tab redesign. Rank/checker delete. T087

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Drop / + is identity-only (same as today). Do not start a squad extract
- Drop does not overwrite a different Career (T101: different filename → new + slot)

## Acceptance criteria

- [x] Header has no Squad button (vitest chrome)
- [x] All four tabs, empty: thead visible + shared drop copy
- [x] Drop `.fm` on an empty pane uses the + upload path
- [x] One git commit `T104: …` on FMT/

## Notes / pointers

- `web/index.html` `#tool-nav` (HTML `hidden` but still on screen). `#roster-empty`, `#squad-loans-empty`, mentoring / progress empty
- `#roster-upload` already identity-only; pane `dragover` / `drop` should feed that input
- Owner: Schalke identity save, 0 players — this is the empty they are looking at

## Progress

Shipped: removed leftover header Squad (`#tool-nav` / `.tool-nav-btn`; `display:flex` had overridden HTML `hidden`). Empty panes keep that tab’s thead (Squad HA columns; Loans Name/Unit/At; Mentoring Group/Members; Progress Name/CA/ΔCA/Det/ΔDet) plus shared copy `Drop a Career Save (.fm) here, or use +`. Drop on an empty pane feeds `#roster-upload` via `feedRosterUpload` (clears amend → + identity upload, new save not overwrite). Filled Loans cards / Mentoring groups / Progress chart unchanged.

Verified: `npx vitest run` t104 + t103 + t075 + t070 + t102 + t101 + t100 + t095 + t088 + squad-route (32 passed); `tsc --noEmit`. Restart `npm run dev`. No committed `.fm`.
