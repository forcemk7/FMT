---
id: T123
title: Mentor desk — club HA mentor/mentee lists
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T122]
---

# T123 — Mentor desk — club HA mentor/mentee lists

## Why

Owner tabs to Live Editor to filter club players by HA for mentors (≥) and mentees (≤). Old FMT Mentoring was a reminder stack; first live value is **two lists from one load**.

## Scope

- In: Only if T122 **passed** with HA (or personality pack usable as mentor signal)
- In: Screen or Squad mode: Mentors / Mentees with editable thresholds (defaults from owner habit: mentee younger + lower HA floors; mentor higher)
- In: Uses managed-club players only
- Out: Suggest seating AI, write to FM, world search, staff TD desk

## Acceptance criteria

- [ ] Owner can set ≥ / ≤ thresholds and see two filtered club lists update
- [ ] Lists use live managed-squad data from FMT load (no `.fm` extract)
- [ ] If T122 failed: this ticket stays **blocked** (do not implement with visible-attr proxies unless HQ rewrites SCOPE)

## Notes / pointers

- Old FMT: age + HAS filters on Squad; Mentoring capture without Suggest
- Keep modular: `src/components/mentor-desk/` 

## Progress

_(worker fills)_
