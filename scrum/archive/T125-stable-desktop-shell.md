---
id: T125
title: Stable desktop shell (no surprise exit)
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-25T16:10:00Z
started_at: 2026-08-25T16:10:00Z
completed_at: 2026-08-25T16:15:00Z
depends_on: []
---

# T125 — Stable desktop shell (no surprise exit)

## Why

Owner’s FMT window/`npm run desktop:dev` drops back to the prompt without an intentional quit. Daily use needs the shell to stay up until they close the FMT window.

## Scope

- In: Find why the process exits early under `desktop:dev`; fix or provide a **stable launch** that does not file-watch-restart the window
- In: Shell stays running until the user closes the FMT window (normal close → exit OK)
- Out: Installer polish, tray icon, performance work

## Acceptance criteria

- [x] Documented/stable way to open FMT for daily use that does not die on unrelated file saves
- [x] Closing the FMT window is the normal quit path; no silent crash on first paint when Next is up
- [x] Owner can leave FMT open beside FM without the prompt returning by itself

## Progress

Root cause: `tauri dev` **file-watches** `src-tauri`. Cursor/agent saves restart/kill the window → console returns to the prompt looking like a surprise exit.

Shipped:
- `npm run desktop:stable` → `tauri dev --no-watch`
- `Start FMT.cmd` uses stable launch + short explanation
- Keep `desktop:dev` for real Rust iteration (watch on)

Closing the FMT window or Ctrl+C still quits (intentional).
