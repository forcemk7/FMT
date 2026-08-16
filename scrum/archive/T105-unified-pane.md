---
id: T105
title: One table pane shell; drop well in the same slot
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-16
started_at: 2026-08-16
completed_at: 2026-08-16
depends_on: [T104]
---

# T105 — One table pane shell; drop well in the same slot

## Why

T104 put copy on every tab, but each empty pane is a different box: Squad drop fills the body; Loans is a thin row; Mentoring has “Load a Career Save” + Add group; Progress is another well. Owner wants **one main table component**. Columns may differ. Padding, panel size, and the drop slot must not.

## Scope

One shared pane shell for Squad / Loans / Mentoring / Progress (empty and filled):

```
[ panel — same border, radius, padding, height ]
  [ table thead — tab columns ]
  [ drop well — same box, same place, only when empty ]
  [ filled rows / cards / chart — tab content, when not empty ]
```

- In: Same CSS shell (one class) on all four panes. Same outer padding around the table. Thead stays at the top; column sets stay T104’s
- In: Empty: **one** drop well **under the thead**, not a table row, not a skinny colspan strip. Centered in the remaining panel. Same size and offset on every tab. Copy stays `Drop a Career Save (.fm) here, or use +`
- In: Mentoring empty: hide “Load a Career Save” and **Add group**. Those return when the tab has groups
- Out: Extract. HA columns. Save cards. Redesigning filled Loans cards / Progress chart / Mentoring groups beyond fitting them in the shared panel. T087

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Drop / + stays identity-only (T104)

## Acceptance criteria

- [x] Four empty tabs: same panel padding/size; thead on top; drop well same class / same place (vitest chrome)
- [x] Mentoring empty has no Add group / “Load a Career Save”
- [x] Drop still feeds + upload
- [x] One git commit `T105: …` on FMT/

## Notes / pointers

- Today: Squad `#roster-empty` in `.squad-grid-wrap`; Loans/Progress `pane-empty-host` + `pane-drop-copy` as a `<td colspan>`; Mentoring `#mentoring-empty-host` plus leftover empty copy and footer Add group
- Steal: one panel, slot for thead, slot for empty well (Finder / Linear empty inbox)

## Progress

Shipped: Squad / Loans / Mentoring / Progress use one `.table-pane` shell. Empty panes keep T104 thead on top and a `.table-pane-drop` well under it (not a `<td colspan>`). Mentoring empty hides Add group and does not show “Load a Career Save”; both return when groups exist. Drop still feeds `#roster-upload` via `feedRosterUpload` (clears amend → + identity upload). Filled Loans cards / Mentoring groups / Progress chart stay, fitted in the same panel.

Verified: `npx vitest run` t105 + t104 + t103 + t075 (13 passed); `tsc --noEmit`. Restart `npm run dev`. No committed `.fm`.
