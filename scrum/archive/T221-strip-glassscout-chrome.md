---
id: T221
title: Strip GlassScout chrome leftovers (CSS + scratch)
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T00:55:00+02:00"
started_at: "2026-09-06T00:56:00+02:00"
completed_at: "2026-09-06T01:06:00+02:00"
depends_on: []
---

# T221 — Strip GlassScout chrome leftovers (CSS + scratch)

## Why

Loop A cleanup: after T218 killed most GS components, the fork still leaves weight in `globals.css` and untracked probe/scratch files. Rip proven-dead chrome so FMT is what remains — not a second product pass.

## Scope

**In — delete only after grep shows zero TSX/CSS callers in `desktop/src/components/` (and no FMT class reuse):**

- Orphan GS CSS families in `desktop/src/app/globals.css`: `.confidence-ring*`, `.startup-screen` (+ mode cards if unused), `.app-sidebar` / scout-room-only rules, `.scout-room-*`, favorites-table chrome, recruitment chrome
- Dead `.fit-score-*` overrides in `globals.css` / `fmt-desk.css` with no component callers (keep live `.ability-ring-*` / squad metric rings)
- Scratch dumps: `desktop/walk-summary.txt`, `desktop/affiliate-containers-summary.txt`, `desktop/target-check.txt`, `desktop/src-tauri/probe-err.txt`, root `tmp_json_opt.rs`
- Unused `desktop/src/domain/distribution.ts` (TobiasTest22 installer URL, no importers)
- Optional: tighten `.gitignore` for `desktop/*-summary.txt` / `*-err.txt` style noise

**Out:**

- Pass 2 — **T222**
- `NOTICE-GlassScout.md`, origin README lines, `research/`
- Crate rename `glassscout_fm26_lib`, `.cargo/config.toml`
- Live RE / Loop D / affiliation bytes / T190 / theme / new features
- ROADMAP rewrite

## Acceptance criteria

- [x] Listed orphan CSS families removed; `rg` finds no remaining class names used by components
- [x] Scratch dumps deleted; `distribution.ts` gone; `.gitignore` tightened
- [x] Vitest smoke (attr-colors / attribute-tone / has-score / squad-desk-session) passed
- [x] One commit `T221: …`

## Notes / pointers

- Prefer block deletes with verification grep over speculative rewrites of live desk CSS
- Kept: ability-ring, squad-metric-ring, favorites-empty, app-canvas/app-main, club-squad-grid

## Progress

Deleted scratch dumps + `distribution.ts`. Stripped scout-room / sidebar / startup / confidence / fit-score / recruitment / favorites-table CSS from `globals.css` (~3.8k→~2.5k lines) and dead fit-score/startup overrides in `fmt-desk.css`. Vitest smoke OK.
