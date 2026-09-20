---
id: T275
title: World player lookup — squeeze FMLE out of dual-monitor loop
status: deferred
priority: null
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T275 — World player lookup — squeeze FMLE out of dual-monitor loop

## Why

Proven owner habit: **club player → FMT**, **not-club player → FMLE**, play → FM. Loop A (club desk) already replaced in-game profile for managed players. Full-world lookup is the remaining FMLE wedge. That is **Loop D** — parked. Not funded while FMT is personal-use quality and download success is still unknown. On the board so the ask is tracked; **do not claim until HQ unfreezes Loop D.**

## Scope (when unfrozen)

- In: Search / open player profile for players outside the managed club (enough attrs/CA/PA/HA to replace FMLE lookup for that session)
- In: Reuse existing desk/profile path where possible — not a second product
- In: Stay on live-read contract; update `research/` if new locks
- Out: FMLE edit parity; transfer market; mentoring world search; cloud upload; beating FMLE load time as a vanity goal

## Acceptance criteria (when unfrozen)

- [ ] Owner can look up a non-club player in FMT without opening FMLE for that lookup
- [ ] Club Loop A path unchanged and still correct
- [ ] One commit `T275: …` (or HQ-approved split)

## Notes / pointers

- SCOPE Loop D: full-world live index; `research/live-read.md` + recipes
- HQ (2026-09-07): deferred — no funding; prefer signal that downloads actually run (diagnostics) before expanding beyond club desk

## Progress

Deferred — not ready to claim.

## HQ note (2026-09-15)

Not in FMT 1.28 — still parked. Clarification for whenever it's unfrozen: the app already pulls players across clubTeams and affiliate clubs (with loan agreements) as part of Match Experience / T288's consolidated resolution — that existing data can likely stay searchable without a new full Loop D world-table RE effort. Re-scope against T288's output before assuming this needs fresh RE.
