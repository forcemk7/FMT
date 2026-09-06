---
id: T232
title: Drop FC prefix string hacks for shortName
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T04:33:00+02:00"
started_at: "2026-09-06T04:33:00+02:00"
completed_at: "2026-09-06T04:35:00+02:00"
depends_on: [T231]
---

# T232 — Drop FC prefix string hacks for shortName

## Why

T231 invented shortNames by stripping `FC` / legal-form prefixes. That is not club-agnostic. Profile Club must use memory `team+0x20` shortName only — no string rewrite rules.

## Scope

**In:**

- Remove `strip_team_name_legal_prefix` / `resolve_populated_short_name` / TS strip helpers
- Profile: prefer memory `shortName`; reject TeamType labels; fall back to unmodified FM full name / club name only
- Recipes: remove strip note

**Out:** New RE for shortName if memory field empty (separate if still broken after rebuild)

## Acceptance criteria

- [x] No legal-form / `FC` strip logic in Rust or TS
- [x] Profile still prefers `shortName` when present; never TeamType labels
- [x] Tests updated; one commit `T232: …`

## Progress

Removed all legal-form strip invent paths. Profile uses memory shortName as-is; unmodified full FM name only if short empty. Vitest 44 ok.

Commit SHA after commit.
