---
id: T150
title: Logos + flags via cache warm (TCM)
status: in_progress
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T16:19:00Z
started_at: 2026-08-26T16:20:00Z
completed_at: null
depends_on: []
---

# T150 — Logos + flags via cache warm (TCM)

## Why

Loop A/B desks render ClubLogo / NationFlag, and Settings lists TCM_Logos — but logo-cache and flag-cache stay empty. Faces work (O(1) on-demand). Logos/flags only serve disk cache and never warm; flag search also misses TCM’s `nation/{id}/logo` mappings. Zero badges feels broken.

## Scope

- In:
  - Hot path stays O(1) disk cache only (no pack walk from UI invoke)
  - One-shot background index + copy for logos (existing) and flags (align with logos; accept `nation/{id}/logo` and `…/flag`)
  - After connected load: queue unique squad club IDs + nationality IDs into warm (non-blocking; never block Load Active Save)
  - UI: miss → soft empty; on cache fill, retry via event (steal PlayerFace `fmt-*-updated` pattern) so early nulls don’t stick
  - Squad row + player desk show nation flag when `nationalityId` known; club logo where ClubLogo already mounts
- Out:
  - New Settings “Update logos” chrome (warm on load is enough)
  - Walking live SI packs on every row paint
  - Theme / T139
  - Competition logos

## Acceptance criteria

- [ ] With TCM_Logos installed and a connected squad: player profile shows club logo + nation badge when IDs map
- [ ] Squad overview shows nation flags (and club logo where the row already has a club cell / header)
- [ ] First paint / Load Active Save does not freeze; pack index runs off the UI thread once
- [ ] Repeat views hit `%LOCALAPPDATA%\com.fmt.fm26\logo-cache` / `flag-cache` only
- [ ] Early miss while warm runs later appears without remounting the whole screen
- [ ] `cargo check` in `desktop/src-tauri` passes

## Notes / pointers

- Pack: `…/graphics/TCM_Logos_Megapack_2026.02` — clubs `graphics/pictures/club/{id}/logo`; nations `graphics/pictures/nation/{id}/logo` (Federations)
- Simple model: nation/club UID → XML lookup → copy into cache path (same as loan club logos)

## Progress

In progress. Flags rewritten to logo-style index (TCM `nation/{id}/logo`). Soft UI retries + post-load warm. Next: cargo check.
