---
id: T207
title: Squad — restore team tab + scroll on profile back
status: done
priority: 1
owner: auto
claimed_at: 2026-09-04
started_at: 2026-09-04
completed_at: 2026-09-04
depends_on: []
---

# T207 — Squad — restore team tab + scroll on profile back

## Why

Loop A: browse a non-senior club team → open player → Back. Today Back drops to senior squad and top of list, breaking the desk loop.

## Scope

- In: remember active club-team tab across Squad ↔ Player Profile; restore `.app-main` scroll when returning to Squad
- Out: Loans/GM/HoYD desks; permanent localStorage; filter chips (unless free with same session)

## Acceptance criteria

- [x] Open player from a non-manager club team tab → Back returns to that same team tab (not senior/manager default)
- [x] Scroll position in Squad is restored after profile Back (not jumped to top)
- [x] Switching team tabs still works; invalid/missing team uid falls back to manager/default

## Notes / pointers

- `MyTeamScreen` unmounts when `screen` changes (`fmt-app.tsx` AnimatePresence `key={screen}`), so local `useState` for `selectedTeamUid` resets
- Scroll lives on `.app-main` (`overflow:auto` in shell-single-header)

## Progress

- Root cause: Squad remount wiped `selectedTeamUid` + `.app-main` scroll.
- Shipped in-memory `squad-desk-session` (team uid + scroll); stash scroll on player open before profile clamps main; restore on layout; tab switch resets scroll.
- Verified: `npx vitest run src/domain/squad-desk-session.test.ts` (2 pass). Manual: U19/B-team → player → Back should keep tab + scroll.
- Commit: `405a0c4`
