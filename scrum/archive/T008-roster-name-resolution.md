---
id: T008
title: Resolve real names for club roster and Mentoring pool
status: done
priority: 1
owner: auto
claimed_at: 2026-08-11T21:25:35Z
started_at: 2026-08-11T21:26:00Z
completed_at: 2026-08-11T22:10:51Z
depends_on: []
---

# T008 — Resolve real names for club roster and Mentoring pool

## Why

**Loop break (behavior):** Mentoring Suggest shows **Landri Risse** as `uid:…` instead of a name. Personality / Loans cards also show raw UIDs. Mentoring groups are unusable without human-readable identity.

## Scope

- In: name join for managed-club players who appear on FT / Reserves / U19 / Loans / Mentoring so UI shows the in-game name (Risse required)
- Out: Dynamics; loan detect (T007); employment filter (T009) except as needed for the name join; cosmetic UI

## Acceptance criteria

- [x] Landri Risse displays as **Landri Risse** (not `uid:`) in Mentoring Suggest and on any unit/Loans card he appears on
- [x] No Mentoring pool entry for the managed club uses a `uid:` fallback when the namelist (or proven join) has a name
- [x] Spot-check: prior audit `uid:` Loans/FT cards (e.g. Görrissen / Kirsch class) resolve when names exist in save
- [x] Regression test or fixture: Risse UID → name join cannot silently regress
- [x] Document root cause in Progress (which namelist/path failed)

## Notes / pointers

- T004C: Landri Risse UID `2002217460` (II / job `317202` historically)
- ROADMAP previously deferred “II namelist holes” — **reopened** because Mentoring pool is blocked
- Extract name resolution path in `extract-first-team-fast.py` / person records

## Progress

### Root cause

Gap UIDs (Risse / Görrissen / Pérez) have **zero** `\x00\x02`+uid inline name records in the employment tail — the path `resolve_name` used for Seimen/Vlad. Names exist only as first/surname **name-table IDs** on the person stub.

### Fix (shipped)

1. Prefer existing `\x00\x02`+uid inline names.
2. Fallback: closest person MARK `01006c07` before `uid||uid` → `firstNameId` @+25, `secondNameId` @+30.
3. Resolve IDs in mid-file name-table band (100–160MB): hits[0]=first, hits[1]=surname (parallel tables collide on id space).

### Verified

- `tests/test_roster_name_resolution_t008.py` — 4 OK (Risse + fixture gap UIDs + mark path).
- Fixture: `data/fixtures/person-name-mark-locked.json`.
- Regression: T009/T007/T006/T004 — 21 OK.
- Spot: Risse → Landri Risse; Görrissen → Lion Görrissen; Pérez → Miguel Pérez.

### Residual

- Re-upload Career Save so Mentoring/Loans cards pick up new extract names.
- Name-table band is soft (100–160MB); exotic saves may need band retune.
