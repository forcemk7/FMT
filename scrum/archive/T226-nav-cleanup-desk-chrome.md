---
id: T226
title: Nav cleanup — drop Tactic/TD; desk chrome without titles
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T03:05:00+02:00"
started_at: "2026-09-06T03:05:00+02:00"
completed_at: "2026-09-06T03:20:00+02:00"
depends_on: []
---

# T226 — Nav cleanup — drop Tactic/TD; desk chrome without titles

## Why

Tactic/TD have no live data or recipes — empty Later stubs. Role desks still show redundant page titles under shell tabs. Order should be Squad → Loans → HoYD → GM.

## Scope

**In:**

- Remove Tactic + TD from shell nav / Screen routing; drop LaterRole stub path
- Nav order: Dashboard · Squad · Loans · HoYD · GM (+ Settings)
- Loans / HoYD / GM: no page title+subtitle when connected; compact desk chrome like Squad
- Team selectors stay Squad-only; Filters on HoYD/GM (club-wide status); Loans needs no status filter
- Sync SCOPE nav line to match

**Out:** Building Tactic/TD; Dashboard title rewrite; new RE

## Acceptance criteria

- [x] Tactic/TD gone from nav; order Squad, Loans, HoYD, GM
- [x] Connected Loans/HoYD/GM have no redundant h1/subtitle; Squad keeps team tabs + filter
- [x] SCOPE nav matches; one commit `T226: …`

## Progress

Shipped: nav order + drop stubs; role desks compact without titles; HoYD/GM club-wide Filter; Loans titleless when connected; LaterRoleScreen deleted; SCOPE updated.

Verified: ReadLints clean on touched components. Commit `cfc2cd6`.
