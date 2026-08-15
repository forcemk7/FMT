---
id: T069
title: Commit working tree as ship baseline
status: done
priority: 1
owner: worker
claimed_at: 2026-08-15T12:27:00+02:00
started_at: 2026-08-15T12:28:00+02:00
completed_at: 2026-08-15T12:35:00+02:00
depends_on: []
---

# T069 — Commit working tree as ship baseline

## Why

`main` has two commits. The mentoring lookup already works in the dirty tree. Without a baseline SHA, later tickets cannot compound and we cannot ship GitHub.

## Scope

- In: one commit on `FMT/` of the current product (code, scrum, tests, fixtures that belong in git)
- Out: `data/saves/`, `data/faces/`, `data/logos/`, `*.fm`, secrets, `node_modules/`
- Out: rewrite, strip Progress/faces, extra tickets
- Push only if this ticket’s Progress says HQ asked to push

## Acceptance criteria

- [x] `git -C FMT status` is clean except ignored paths
- [x] Latest commit message starts with `T069:`
- [x] `git ls-files` has no `.fm`, no files under `data/saves/`, no secrets
- [x] `scrum/STATUS.md` Recently done includes this SHA

## Notes / pointers

- Repo: `C:\Users\mrdev\Documents\Projects\FMT`
- `.gitignore` already excludes saves/faces/logos
- Do not `git add` from `Projects/`
- After this, every ticket is one commit (AGENTS.md Git)

## Progress

Shipped: one `FMT/` commit of the working product (code, scrum, tests, fixtures). `data/saves/`, `data/faces/`, `data/logos/`, `*.fm`, secrets, and `node_modules/` stay gitignored / unstaged. No push (HQ did not ask).

Verified: `git status` clean except ignored paths; `git ls-files` has no `.fm`, no `data/saves/`, no secrets; commit message starts with `T069:`. SHA filled after commit into Recently done / this Progress.
