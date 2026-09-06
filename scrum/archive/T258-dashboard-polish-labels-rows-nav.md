---
id: T258
title: Dashboard polish — labels, rows, profile tabs, back
status: done
priority: 2
owner: auto
claimed_at: "2026-09-07T00:42:00+02:00"
started_at: "2026-09-07T00:42:00+02:00"
completed_at: "2026-09-07T00:47:00+02:00"
depends_on: [T254, T255]
---

# T258 — Dashboard polish — labels, rows, profile tabs, back

## Why

Widget names/display/navigation should match purpose; dash→player must open the right profile tab; back must restore prior screen (not a hardcoded home).

## Scope

- In: Rename Development → **Attribute changes**; Best talent → **First-team path** (non-First players); keep Match experience / Top / Worst personalities
- In: Row chrome — movers ≥3 attrs +N; path CA/PA + clubTeam on right; ME logos+TeamType→…+rank+pos on right; HAS top/bottom 3 personality abbrs
- In: Clicks open Attributes (or ME for ME widget); dash full-view Back = `goBack`
- Out: Division RE; full scroll-memory app-wide (later ticket); renaming Worst personalities

## Acceptance

- [x] Titles/blurbs match above
- [x] First-team path excludes First Team squadUnit
- [x] Profile tabs + dash view back via history
- [x] Commit `T258: …`

## Progress

- Titles: Attribute changes / First-team path / Match experience / Top & Worst personalities
- `rankSquadProspects` skips First Team (default missing unit → First)
- Row chrome: mover chips (3 +N), prospect CA/PA + team right, ME logo rail, HAS personality abbr chips
- Peeks + full views open profile via `dashViewProfileTab`; DashboardViewScreen `onBack={goBack}`
- Verified: `vitest` squad-prospects + match-experience-opportunities
- Commit: (see git)
