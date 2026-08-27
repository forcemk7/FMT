---
id: T188
title: Attr deltas in load pipeline for both desks
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-08-27T21:30:00+02:00"
started_at: "2026-08-27T21:30:00+02:00"
completed_at: "2026-08-27T21:36:00+02:00"
depends_on: []
---

# T188 done — Attr deltas in load pipeline for both desks

## Acceptance criteria

- [x] Load stamps `recentAttrDeltas` / `allTimeAttrDeltas` on players after history append
- [x] Attributes desk prefers recent maps; Development prefers all-time
- [x] Primary path is ingest on Load, not desk-only localStorage read
- [x] Unit tests for attach from two-point / one-point stores

## Progress

- `ingestSnapshotPlayers` in fmt-app; LivePlayer delta fields; AttributeDesk reads attached maps
- Commit: (filled after git)
