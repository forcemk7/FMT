---
id: T233
title: Pure TeamType / shortName display rule
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T04:52:00+02:00"
started_at: "2026-09-06T04:52:00+02:00"
completed_at: "2026-09-06T04:56:00+02:00"
depends_on: [T232]
---

# T233 — Pure TeamType / shortName display rule

## Why

User rule is only:

- Managed club teams → TeamType labels (`First Team`, `Under 19s`, …)
- Affiliated teams → memory `shortName` (`Schalke 04 II`)
- Player profile Club → memory `shortName` (`Schalke 04` / `Schalke 04 U19` / `Schalke 04 II`)

No full-name fallbacks, no prefix invent, no clubName substitute. Prior tickets still fell back to full FM name / club name when short was empty — that is extra.

## Scope

**In:**

- `squadTeamDisplayName`: managed → TeamType (else map reminder); affiliate → shortName only (else map reminder)
- `playerTeamDisplayName`: shortName only via `squadTeamUid` (else null)
- Drop full-name / clubName / affiliation-label fallbacks used as display substitutes
- Tests match the pure rule

**Out:** New RE if `team+0x20` returns empty (surface empty honestly; do not invent)

## Acceptance criteria

- [x] Affiliate tab never shows full `FC …` when shortName missing — map reminder instead
- [x] Profile Club never falls back to full team/club name
- [x] Vitest; one commit `T233: …`

## Progress

Your understanding was complete. We were doing extras (full-name / clubName fallbacks). Display is now TeamType | shortName only. If `team+0x20` is empty in the snapshot, profile shows null / affiliate shows map reminder — that is a memory-read gap, not a display invent.

Commit SHA after commit.
