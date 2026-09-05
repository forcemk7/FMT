---
id: T219
title: R&D knowledge base + strip probe fossils
status: done
priority: 4
owner: cursor-agent
claimed_at: "2026-09-05T21:08:00+02:00"
started_at: "2026-09-05T21:08:00+02:00"
completed_at: "2026-09-05T21:32:33+02:00"
depends_on: [T218]
---

# T219 — R&D knowledge base + strip probe fossils

## Why

Owner wants a serious FMT R&D/knowledge layer (future OSS / adjacent tooling / version sustain) and a thinner product tree. Probe modules, dump piles, and GS islands burn compile time; knowledge must survive in docs, not only in deleted Rust.

## Scope

- In: `scrum/FM-RECIPES.md` — first-party verified recipes (affiliates, Club.Teams, origin, world-table direction); link from `FM-ECOSYSTEM.md` + `fm-live-read.mdc`
- In: Delete probe-only `fm26` modules, `fmt-probe` bin/feature, npm `probe:*`, untracked dump/scripts junk, dead CSS, TS `scout-knowledge` / `player-evaluation` islands, unused `roles`/`tactics`/`data` stubs, connector debug probe surface
- In: Keep production load: `affiliate_links` + `affiliation_types` + `blob_scan` + core reader; commit `NOTICE-GlassScout.md`
- In: `.gitignore` probe dump patterns
- Out: Loop D world walker; rewriting affiliate production path; deleting entity-maps; rewriting SCOPE north stars

## Acceptance criteria

- [x] FM-RECIPES documents locked affiliate edge, type map, origin byte, Club.Teams, and what was discarded (registry/FMLE heap)
- [x] `cargo check` (default features) succeeds without `fmt-probe` / deleted modules
- [x] Domain vitest passes (product.test trimmed)
- [x] Probe JSON/bin dumps and `target-t214` gone from working tree; gitignore covers dump globs
- [x] One commit `T219: …`

## Progress

### Knowledge

- Added `scrum/FM-RECIPES.md` (first-party R&D book). Linked from `FM-ECOSYSTEM.md`, `fm-live-read.mdc`, `scrum/README.md`, `AGENTS.md`.

### Removed

- Probe modules + orphans: agreement/census/duisburg/editor/pge/player_origin/registry/fmle_*/index_signature/club_team_anchors/team_names/roles/tactics
- `data/` stubs; `fmt-probe` + `affiliate_flags_probe`; npm `probe:*`
- ~205 desktop dump files + `target-t214` (both paths); probe helper scripts (kept `bump-desktop-version.mjs`)
- Connector probe cfg surface (~1.1k lines); TS scout-knowledge / player-evaluation islands

### Kept

- Production: `affiliate_links`, `affiliation_types`, `blob_scan`, memory/offsets/parser/process/scanner/structs/validator/permissions/executable

### Verified

- `cargo check` ok (~4s warm)
- `npx vitest run src/domain` — 100 pass

### Residual

- Orphan GS CSS in `globals.css` (not deleted this ticket — surgical risk)
- Main/Permanent/PMF bytes still open (FM-RECIPES)

Commit: `6b455d1`.
