---
id: T292
title: PA masking toggle — user preferences
status: done
priority: 2
owner: worker
claimed_at: 2026-09-22
started_at: 2026-09-22
completed_at: 2026-09-22
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

- [x] Toggle in User Preferences masks PA everywhere it's displayed, including Dashboard's biggest-talent card
- [x] ~~Default (off) is unchanged behavior~~ — superseded 2026-09-22: owner explicitly flipped the default to **on** (see Progress below). Deliberate reversal of this criterion, not a regression.
- [x] One commit `T292: …` — plus one direct follow-up commit same day (see Progress)

## Notes / pointers

- Requires T215's User Preferences section to exist first

## Progress

Investigated first (per owner's standing preference): no preferences store existed, and the whole Settings screen was read-only diagnostics (`DiagnosticCellView`, no interactive controls anywhere). Owner confirmed more preferences are coming (UI density/theme in T293/T139, possibly non-club-player attribute masking later), so built this generically rather than PA-only:

- New `domain/preferences.ts`: a tiny external store (`useSyncExternalStore`, no new deps) backed by `localStorage` (`fmt-preferences-v1`, merge-onto-defaults so future keys don't need a version bump). Exports `usePreferences()` + `setPreference(key, value)`. `hidePA` is the first key; future prefs are just new keys on the same type.
- `SettingsGroup` (settings-screen.tsx) now accepts `children` as an alternative to `cells`, so the User Preferences section can render a real control instead of being forced through the read-only diagnostic-cell shape. Added `PreferenceToggleCell` (label + a real toggle button, `role="switch"`) and matching CSS (`.settings-pref-cell`/`.settings-pref-toggle`, reusing `var(--mint)`/`var(--border)` tokens) — first interactive control in Settings.
- Masked PA at all 4 display sites (CA/HAS left untouched, matching ticket scope): `DashAbilityStat` (dashboard-widgets.tsx, covers all 3 Dashboard call sites incl. biggest-talent card), Player Profile's Potential stat, Squad's `AbilityRing` (new `masked` prop, still shared with CA), and the attribute-desk General column (also suppresses the PA recent-delta badge while masked, since a nonzero delta would leak that PA changed). Sorting by real `potentialAbility` (my-team-screen.tsx) is untouched by design.

Verified: `tsc --noEmit` and `eslint` clean on every touched file (pre-existing unrelated errors in `*.test.ts` and two effect-setState lint errors elsewhere in my-team-screen.tsx confirmed via `git diff` to predate this change). Full `vitest run` — 142/142 pass. Live-clicked in the dev preview (`next dev`, no FM26 save attached): toggle flips visually, section meta updates to "1 Active", persists across a full page reload with no hydration warnings, `localStorage["fmt-preferences-v1"]` holds `{"hidePA":true}`. Left the preview in its default (off) state after testing.

Not verified live: the 4 masked value/tone/delta call sites against a real loaded save (dev preview had no FM26 process attached, so PA fields showed placeholder/"Unavailable" states throughout — masking logic is unconditional on `kind === "PA"` so it doesn't depend on real data, but owner should eyeball Dashboard/Squad/Profile with a save loaded and the toggle on before considering this fully closed).

Commit: T292: PA masking toggle + generic user-preferences store (see git log).

## Follow-up (same day, 2026-09-22)

Owner kept iterating on the Settings screen and the preferences store directly after close — recorded here rather than as a new ticket since it's a direct continuation of this store/UI, not new independently-scoped work:

- **Settings layout**: User Preferences moved to its own panel above the diagnostics list (was the last diagnostic-style section) with a visible gap (`globals.css` `.settings-list + .settings-list`), since it's actionable rather than read-only. Affiliations moved above Teams (Teams includes affiliated-club rosters, so Affiliations reads first). Affiliations' summary now shows an actual count (parsed from the existing `Affiliate clubs loaded` backend diagnostic string) instead of the static word "loaded", matching Teams' `"N teams"` pattern.
- **User Preferences header**: dropped the tone dot and the meta text (`"—"` / `"1 active"`) — owner's call that a diagnostic-style status indicator doesn't belong on an actionable-settings section. `SettingsGroup`'s `tone`/`meta` props are now both optional.
- **Height display** ([player-profile-screen.tsx](../../desktop/src/components/player-profile-screen.tsx)): dropped the cm→m reformatting (`"186 cm"` → was `"1.86 m"`). Investigated first — confirmed the raw read (`player_height_offset`, range-filtered 140–220 in `connector.rs`) is genuinely centimeters already; the `/100` was our own reformatting on top of an already-correct value, not a real unit conversion, so nothing to make configurable.
- **New preference: `autoLoadOnStartup`** (default **on**, preserves shipped T274 behavior until toggled off). Implemented in `fmt-app.tsx`: a new `hasConnectedOnceRef` gates *only* the very first auto-load of a session — once any load succeeds (manual or automatic), disconnect/reconnect and save-switch auto-refresh proceed exactly as T274 shipped regardless of this preference. Turning it off just means FMT sits at "detected, click Load" on open instead of pulling data immediately.
- **Defaults flipped**: owner's final call — both `hidePA` and `autoLoadOnStartup` now default **on** (`DEFAULT_PREFERENCES` in `preferences.ts`). People who want to see PA, or who don't want auto-load, turn the relevant toggle off themselves. This directly supersedes this ticket's original "default off, unchanged behavior" acceptance criterion — a deliberate owner decision, not scope drift.

Verified: `tsc --noEmit` clean, `eslint` clean on every touched file (one pre-existing unrelated error at `fmt-app.tsx:387`, confirmed via `git diff` to predate this session), `vitest run` 142/142. Live-clicked both toggles in the dev preview with `localStorage` cleared (fresh-install simulation) — both default on, flip/persist correctly, no console errors. Not verified against a real loaded save (dev preview has no FM26 process) — owner was running the real desktop app in parallel (visible via shared terminal output, real `FM26 pid=1996` heartbeat/load activity) and can confirm end-to-end behavior there directly, which is more authoritative than anything achievable from the detached browser preview.

Commit: T292-followup: settings polish, auto-load-on-startup preference, defaults flipped to on (see git log).
