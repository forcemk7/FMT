---
id: T119
title: Rename glassscout folder to desktop (FMT-native path)
status: ready
priority: 1
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T119 — Rename glassscout folder to desktop (FMT-native path)

## Why

Owner wants zero `glassscout/` vanity path — FMT native tree only. Attribution stays in `NOTICE-GlassScout.md`.

## Scope

- In: Rename `glassscout/` → `desktop/` when no process has the folder locked
- In: Update root `Start FMT.cmd`, `README.md`, `scrum/SCOPE.md`, `.gitignore` paths
- In: Strip user-facing “GlassScout” strings left in product copy (connector messages already mostly FMT)
- Out: Deep Rust crate rename churn beyond `desktop/` path; UI redesign

## Acceptance criteria

- [ ] Repo has `desktop/` and no `glassscout/` directory
- [ ] Root `Start FMT.cmd` launches FMT from `desktop/`
- [ ] `npm run desktop:dev` / `desktop:stable` still works from `desktop/` after `vcvars`
- [ ] README/SCOPE path references say `desktop/`

## Notes / pointers

- **2026-08-25:** rename failed — folder in use. Close FMT window, stop `node`/`cargo`/`desktop:stable`, then claim this ticket and rename.
- Attribution stays in `NOTICE-GlassScout.md`

## Progress

_(worker fills)_
