---
id: T202
title: Squad face cache freshness for recycled UIDs
status: done
priority: 3
owner: cursor-agent
claimed_at: 2026-09-04T04:16:00Z
started_at: 2026-09-04T04:16:00Z
completed_at: 2026-09-04T04:25:00Z
depends_on: [T157]
---

# T202 — Squad face cache freshness for recycled UIDs

## Why

Newgen remaps recycle UIDs; pack `from=` / face files update but FMT `face-cache` treats UID hits as forever — Squad shows the wrong person until cache wipe.

## Scope

- In:
  - Background warm for requested squad UIDs re-resolves source (cutout + mapped `_config.xml`)
  - Replace cache when mapped `from` identity changes, or source mtime/size differs
  - Sidecar stores source identity; existing `fmt-faces-updated` nudges stay
- Out:
  - Hot-path live graphics on every `player_face_data`
  - Full pack watchers / world-wide reindex
  - Theme / Settings chrome beyond existing warm path

## Acceptance criteria

- [x] `warm_faces_for_players` does not skip on cache hit when live source identity or mtime/size changed
- [x] Mapped newgen refresh uses `_config.xml` `from=` as identity (recycled UID case)
- [x] Hot path still serves face-cache first (no UI freeze from XML)
- [x] Unit tests cover identity stale / fresh; `cargo test --lib graphics::faces` passes

## Notes / pointers

- `desktop/src-tauri/src/graphics/faces.rs` — `warm_faces_for_players`, `resolve_cached_face`, `scan_mapped_face_configs`
- Warm entry: `faces_update_cache` ← `warm-squad-graphics.ts` on load

## Progress

Shipped: warm re-resolves cutout + mapped sources; `.src` sidecar holds `map:{from}` or `file:{path}`; refresh on identity/mtime/size change; clears sibling extensions so stale format hits cannot win. UI nudge at 15s after warm. Verified: `cargo test --lib graphics::faces` 7/7 ok. Commit `c6b17fd`.
