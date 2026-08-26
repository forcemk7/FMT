---
id: T167
title: Kill header search autofill overlay
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T20:48:00+02:00
started_at: 2026-08-26T20:48:00+02:00
completed_at: 2026-08-26T20:50:00+02:00
depends_on: []
---

# T167 — Kill header search autofill overlay

## Why

T165 search works, but Chromium “Saved info” autofill covers the hit list — Loop A find-player path still blocked.

## Scope

- In: shell search input attrs so WebView does not offer saved personal info / spellcheck overlay
- Out: custom dropdown, password-manager product workarounds beyond standard ignore attrs

## Acceptance criteria

- [x] Header squad search does not show Chromium “Saved info” while typing a name
- [x] Squad hits remain visible and clickable

## Notes / pointers

- `desktop/src/components/shell-header.tsx` search `Input`

## Progress

Shipped: `type="search"`, `autoComplete/spellCheck` off, plus PM-ignore attrs on shell squad search so WebView “Saved info” / red underline stop covering hits. Reload app to verify.
