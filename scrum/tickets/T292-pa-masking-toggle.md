---
id: T292
title: PA masking toggle — user preferences
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T215]
---

# T292 — PA masking toggle

## Why

A downloader asked for this directly (real signal, not a guess): optional masking of Potential Ability across the app. First item in the new Settings > User Preferences section T215 creates — future prefs (color customization, search-ownership masking) can land there later; this ticket is PA only.

## Scope

- In: Settings > User Preferences > "Hide PA" toggle
- In: When on, PA value displays as `?` (or equivalent) everywhere it's currently shown — including the Dashboard "biggest talent" card — rest of the UI/layout unchanged
- In: When off (default), behavior is unchanged from today
- Out: Masking CA/HAS; new preference categories beyond PA; persisting the preference anywhere but existing local settings storage

## Acceptance criteria

- [ ] Toggle in User Preferences masks PA everywhere it's displayed, including Dashboard's biggest-talent card
- [ ] Default (off) is unchanged behavior
- [ ] One commit `T292: …`

## Notes / pointers

- Requires T215's User Preferences section to exist first

## Progress

_(worker fills)_
