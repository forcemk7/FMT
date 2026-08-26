---
id: T152
title: Warm squad faces on load (mirror logos)
status: done
priority: 3
owner: cursor-agent
claimed_at: 2026-08-26T17:00:00Z
started_at: 2026-08-26T17:00:00Z
completed_at: 2026-08-26T17:05:00Z
depends_on: []
---

# T152 — Warm squad faces on load (mirror logos)

## Why

Loop A/B Squad shows placeholders for players newly moved into the squad (e.g. Corvin Garbe) even when Cutout megapack is installed. T150 warm on connect covers logos + flags only; faces never get `faces_update_cache`, and `PlayerFace` sticks the first miss in memory with no soft retry.

## Scope

- In:
  - `warmSquadGraphics`: queue unique squad player IDs → `faces_update_cache` (same fire-and-forget as logos/flags)
  - After warm starts: nudge `clearPlayerFaceMemoryCache` on short delays (steal logo/flag pattern)
  - `PlayerFace`: soft-miss retries like `ClubLogo` so early nulls refill when cache copies land
- Out:
  - NGRegens ethnicity-folder packs (different layout; separate ticket if needed)
  - Settings “Update faces” chrome
  - Theme / T139
  - Walking live SI packs on every row paint

## Acceptance criteria

- [x] After Load Active Save with Cutout megapack installed, squad rows for newly added players show portraits when `face_{uid}.png` exists (no remount required beyond soft retry window)
- [x] First paint / Load Active Save does not freeze; face copy runs off the UI thread
- [x] Early miss while warm runs later appears via retry / `fmt-faces-updated` without full screen remount
- [x] `cargo check` in `desktop/src-tauri` passes

## Notes / pointers

- Bug site: `desktop/src/domain/warm-squad-graphics.ts` (logos/flags only today)
- UI: `desktop/src/components/player-face.tsx` vs soft retries in `club-logo.tsx`
- Backend already has `faces_update_cache` → `warm_faces_for_players` (megapack O(1) `face_{uid}` only)
- Live face-cache sample: `%LOCALAPPDATA%\com.fmt.fm26\face-cache` (~35 files); Cutout config ~45MB under `graphics/Cutout_Player_Faces_Megapack_2026.08/faces`

## Progress

Shipped: squad player IDs → `faces_update_cache` on connect; post-warm `clearPlayerFaceMemoryCache` nudges; `PlayerFace` soft-miss retries (same cadence as ClubLogo). Verified `cargo check` ok. Commit `8a96c57`.
