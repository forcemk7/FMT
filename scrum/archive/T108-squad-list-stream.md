---
id: T108
title: Squad list after identity — shortest path; stream if cheap
status: cancelled
priority: 1
owner: auto
claimed_at: "2026-08-16T20:38:00+02:00"
started_at: "2026-08-16T20:40:00+02:00"
completed_at: "2026-08-16T21:10:34+02:00"
cancelled_at: "2026-08-16T21:40:00+02:00"
depends_on: [T094, T107]
---

# T108 — CANCELLED (owner rejected)

## Why cancelled

Worker rewired the old `extract-first-team-fast` MVP (T093/T094). Owner smoke: counts wrong vs FM (agent 94 vs in-game 87; FT/II/U19 vs loans mismatched; name quality bad). Other Careers → 0 players. Treated as custom-fitted proof-of-concept, not first principles.

**Do not build on T108’s list path.** Identity shell (T096–T107) stays. Next: T109 (working copy hygiene), T110 (club_id → squads → names list from first principles). No HA/CA until lists are honest.

## Progress (historical)

- Wired POST to names-only `extract-first-team-fast.py`. Smoke continue Schalke FT 35 / II 29 / U19 30 — **rejected by owner**.
