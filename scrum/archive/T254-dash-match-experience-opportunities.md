---
id: T254
title: Dashboard widget — Match experience opportunities
status: done
priority: 2
owner: auto
claimed_at: "2026-09-06T23:46:00+02:00"
started_at: "2026-09-06T23:46:00+02:00"
completed_at: "2026-09-06T23:52:00+02:00"
depends_on: [T250]
---

# T254 — Dashboard widget — Match experience opportunities

## Why

Match experience lives on the player desk. Dashboard should surface **upward** playing-time moves worth opening (Loop B → Loop A).

## Scope

- In: Dashboard peek + full view listing simple opportunities
- In: Rule v1 — player currently on a non-First ladder step (Reserves / Under N / Youth band); at least one **First Team** ME card where projected same-pos rank is **1 or 2**; not already current on that team; skip loaned-out
- Out: Division-difficulty ranking (T253); downward First→U19 suggestions; complex loan recommender

## Acceptance

- [x] Dashboard widget lists opportunities; click opens player
- [x] Full dash view lists the same set (capped reasonably)
- [x] Unit tests for the v1 rule
- [x] Commit `T254: …`

## Progress

- Shipped: `rankMatchExperienceOpportunities` + Dashboard peek/view; prefer managed First when ranks tie
- Verified: vitest opportunities (2) passed
- Commit: (this ticket)
