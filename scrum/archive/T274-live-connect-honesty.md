---
id: T274
title: Live connect — auto-refresh + honest load button/status UI
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T274 — Live connect — auto-refresh + honest load button/status UI

## Why

Unfrozen for FMT 1.28. The app is marketed as a live read, but today it is a manual snapshot: desks only refresh after the user clicks **Load Data**, and nothing tells them that. Owner's own words: "the current app isn't live reading for shit... having to manually click the load button is annoying and causing friction." For a personal daily driver an extra click is fine; for downloaders it reads as either broken or dishonest. Bundled with a related UI bug: the Load button currently changes width based on status text and truncates.

## Scope

- In: After the first successful **Load** / attach, keep desks current automatically on a bounded refresh policy (cheap interval or existing dirty/game-date signal — smallest path, must not cost noticeable performance)
- In: When the FM process exits or attach drops, clearly mark the app as disconnected — no stale "connected" squad left on screen
- In: Load button no longer changes width / truncates status text — move status into a footer-type indicator instead, button stays visually minimal
- In: Clear, unambiguous visual distinction between "not connected" and "live" states, since a user no longer needs to click Load repeatedly to see updates
- Out: Full-world index (Loop D / T275); installer telemetry (T290); redesign of Diagnostics beyond what T215 already covers

## Acceptance criteria

- [ ] After first successful attach, in-game club changes appear in FMT without a second Load click, within a bounded refresh policy
- [ ] Exiting FM leaves FMT in a clearly non-live state (empty or explicit disconnected) — no stale "connected" squad
- [ ] Load button width is stable and status text does not truncate
- [ ] Not-connected vs. live states are visually unambiguous at a glance
- [ ] One commit `T274: …`

## Notes / pointers

- Today: process scan ≠ auto load; `Load Data` drives connector snapshot
- Prior HQ note (2026-09-07, now superseded): "owner fine with extra click" — reversed now that the goal is downloader trust, not just personal convenience

## Progress

_(worker fills)_
