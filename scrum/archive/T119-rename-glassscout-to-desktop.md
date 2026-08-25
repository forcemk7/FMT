---
id: T119
title: Rename glassscout folder to desktop (FMT-native path)
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-25T16:45:00Z
started_at: 2026-08-25T16:45:00Z
completed_at: 2026-08-25T16:55:00Z
depends_on: []
---

# T119 — Rename glassscout folder to desktop (FMT-native path)

## Why

Owner wants zero `glassscout/` vanity path — FMT native tree only. Attribution stays in `NOTICE-GlassScout.md`.

## Scope

- In: Rename `glassscout/` → `desktop/` when no process has the folder locked
- In: Update root `Start FMT.cmd`, `README.md`, `scrum/SCOPE.md`, `.gitignore` paths
- In: Strip user-facing “GlassScout” strings left in product copy
- Out: Deep Rust crate rename churn beyond `desktop/` path; UI redesign

## Acceptance criteria

- [x] Repo has `desktop/` and no meaningful `glassscout/` app tree
- [x] Root `Start FMT.cmd` launches FMT from `desktop/`
- [x] `npm run desktop:dev` / `desktop:stable` still works from `desktop/` after `vcvars`
- [x] README/SCOPE path references say `desktop/`

## Progress

Whole-folder rename stayed locked (Cursor/old shells). Moved all children into `desktop/` instead. Root launcher, README, SCOPE, `.gitignore` updated. Favorites key → `fmt-favorites-v1` (reads legacy key). Scout room state key → `fmt-scout-room-view-v1`.

Residual: empty `glassscout/` directory may remain if Windows still holds a handle — delete it after restarting Cursor if present. App code lives only under `desktop/`.
