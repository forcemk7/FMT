---
id: T124
title: Quiet dev launch — no browser tab
status: done
priority: 6
owner: cursor-agent
claimed_at: "2026-09-06T00:32:00+02:00"
started_at: "2026-09-06T00:32:00+02:00"
completed_at: "2026-09-06T00:33:00+02:00"
depends_on: []
---

# T124 — Quiet dev launch — no browser tab

## Why

`tauri dev` leaves owners staring at `localhost:3000` installer/hydration noise while the real app is the desktop shell. Reduce confusion until an installed build exists.

## Scope

- In: Stop auto-opening an external browser for the Next dev URL (Tauri config / env / script)
- In: `Start FMT.cmd` prints one line: “Wait for the FMT desktop window — ignore any browser”
- Out: Full NSIS installer polish (optional later ticket), changing load performance

## Acceptance criteria

- [x] `Start FMT.cmd` / `npm run desktop:dev` does not steal focus to a browser tab as the primary UX
- [x] Desktop window titled FMT still loads against the local dev server

## Notes / pointers

- Tauri 2 `beforeDevCommand` / `devUrl`; Next may still bind :3000 — that is fine if unused by humans
- Installed `desktop:build` remains the long-term fix

## Progress

`dev` script sets `BROWSER=none` before `next dev` (used by Tauri `beforeDevCommand`). `Start FMT.cmd` prints the wait one-liner. `devUrl` unchanged.
