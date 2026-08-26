---
id: T174
title: Hard-clip badge frames (no flag overflow)
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T20:25:00Z
started_at: 2026-08-26T20:25:00Z
completed_at: 2026-08-26T20:27:00Z
depends_on: [T168]
---

# T174 — Hard-clip badge frames (no flag overflow)

## Why

Tall nation crests still painted past the square frame.

## Acceptance criteria

- [x] Spain / Belgium / Uruguay crests never paint outside the badge border
- [x] Club logos keep the same frame treatment

## Progress

Relative frame + overflow:clip; img absolute inset with max-width/height contain; cover forced off.
