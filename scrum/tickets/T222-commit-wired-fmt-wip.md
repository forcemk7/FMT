---
id: T222
title: Commit wired FMT WIP (desk / cosmetics / terminal)
status: ready
priority: 4
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on:
  - T221
---

# T222 — Commit wired FMT WIP (desk / cosmetics / terminal)

## Why

Pass 2 of cleanup: the app already imports domain/UI that never landed as commits. Working tree must match the Loop A product in use — not soft-deps on untracked files.

## Scope

**In — stage/commit only files that are already imported by live FMT paths:**

- `desktop/src/components/has-breakdown-grid.tsx` (+ any CSS it needs that is already live)
- `desktop/src/domain/attribute-desk.ts` + `attribute-desk.test.ts`
- `desktop/src/domain/cosmetics-ready.ts`
- `desktop/src/domain/fmt-terminal-log.ts` + `fmt-terminal-log.test.ts`
- Matching edits already in tree for importers (`attribute-desk.tsx`, `fmt-app.tsx`, `player-face.tsx`, `shell-header.tsx`, `dashboard-widgets.tsx`, `my-team-screen.tsx`, etc.) **only as required to make the above coherent** — no drive-by refactors

**Out:**

- T221 GS chrome strip (separate)
- New features, RE, Loop D, theme, density
- Probe dumps / orphan CSS (T221)
- Unrelated dirty tree (Cargo.lock noise, archive doc churn, untracked tickets)

## Acceptance criteria

- [ ] Listed modules are tracked and imported paths typecheck / vitest for those modules passes
- [ ] No new product behavior beyond what’s already running in the dirty tree
- [ ] One commit `T222: …` (or split only if importers force a tiny follow-up — prefer one)

## Notes / pointers

- After T221. Do not invent APIs — freeze what Squad/Dashboard/Profile already use.
- `git status` will be noisy; stage **only** this ticket’s files.

## Progress

_(worker fills)_
