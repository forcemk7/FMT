---
id: T222
title: Commit wired FMT WIP (desk / cosmetics / terminal)
status: done
priority: 4
owner: cursor-agent
claimed_at: "2026-09-06T01:56:00+02:00"
started_at: "2026-09-06T01:56:00+02:00"
completed_at: "2026-09-06T01:59:00+02:00"
depends_on:
  - T221
---

# T222 — Commit wired FMT WIP (desk / cosmetics / terminal)

## Why

Pass 2 of cleanup: the app already imports domain/UI that never landed as commits. Working tree must match the Loop A product in use — not soft-deps on untracked files.

## Scope

**In — stage/commit only files that are already imported by live FMT paths:**

- `desktop/src/components/has-breakdown-grid.tsx`
- `desktop/src/domain/attribute-desk.ts` + `attribute-desk.test.ts`
- `desktop/src/domain/cosmetics-ready.ts`
- `desktop/src/domain/fmt-terminal-log.ts` + `fmt-terminal-log.test.ts`
- Matching importer edits: `attribute-desk.tsx`, `player-face.tsx`

**Out:** unrelated dirty tree (dashboard-screen rename, attribute-history WIP, Cargo, etc.)

## Acceptance criteria

- [x] Listed modules tracked; vitest attribute-desk + fmt-terminal-log passed
- [x] No new product behavior beyond dirty-tree freeze
- [x] One commit `T222: …`

## Progress

Landed has-breakdown grid, attribute-desk domain, cosmetics-ready gate for faces, fmt-terminal-log labels. Vitest 9 tests OK. Commit `bf4e14a`.
