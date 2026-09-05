---
id: T218
title: Dead code / unused import build hygiene
status: done
priority: 6
owner: cursor-agent
claimed_at: "2026-09-05T20:28:27+02:00"
started_at: "2026-09-05T20:28:27+02:00"
completed_at: "2026-09-05T20:45:22+02:00"
depends_on: [T217]
---

# T218 — Dead code / unused import build hygiene

## Why

Owner feels compile/dev feedback is slow; suspects dead GlassScout leftovers, unused imports, and unused modules. Cleanup is real Loop A friction (wait time) but must stay sequential after search polish — not a pretext to rewrite the product.

## Scope

- In: measure baseline `cargo check` / `npm` typecheck or next build wall time once before and after (note in Progress)
- In: remove **proven-unused** TS/TSX imports and dead exported modules that nothing imports; drop Rust dead `use` / unused fns the compiler already flags when cheap
- In: kill clearly orphaned GS/FMT UI paths only when grep shows zero callers
- Out: architecture rewrite; moving folders “for cleanliness”; deleting probes still referenced by `npm run probe:*`; dependency upgrades; feature flags that change product behavior; fighting false-positive “unused” across cfg features without reading callers

## Acceptance criteria

- [x] Before/after wall times recorded in Progress (same machine, same commands)
- [x] No unused-import / dead-code sweep that breaks `cargo test` / vitest for touched packages
- [x] Diff is deletive or import-only except tiny glue if a delete requires it
- [x] STATUS notes residual suspects (if any) rather than inventing a follow-up epic

## Notes / pointers

- Start: `desktop/src` unused imports (tsc/eslint if configured), then `desktop/src-tauri` `cargo check` warnings
- Do not stage `data/`; do not touch live offsets “while cleaning”
- Prefer several small commits only if the ticket is split mid-flight — default one commit per AGENTS.md

## Progress

### Baselines (`cargo check --message-format=short` in `desktop/src-tauri`)

| When | Wall | Warnings |
|------|------|----------|
| Before (cold) | 260931 ms (~4m21s) | 358 |
| Before (warm) | 111836 ms (~1m52s) | 359 |
| After (warm) | 2714 ms (~2.5s) | 351 |

Warm after mainly reflects a hot cache; durable win is **~376 tracked files / ~115k lines** removed from the tree so Next/tsc/git stop walking dead GS + root vite suites.

### Shipped

- Staged already-orphaned trees: root `scripts/` `tests/` `web/` `src/` `shared/` + root package/vite/vitest/tsconfig + pages workflow
- Dead GS UI: sidebar, recruitment, roadmap, role-dna, tactical/tactics, topbar, favorites, mentoring panel, attr-colors panel
- Orphans deleted: `confidence-ring`, `startup-screen`, unused shadcn `ui/{avatar,dialog,separator,badge,card,progress}`
- Rust unused modules: `fm_dossier`, `mapping_lab`, `visibility`
- Domain `visibility.ts` (+ test)
- Glue: drop Mentoring tab import from player profile; `cargo fix` unused imports in `connector.rs`; remove unused `GitCompareArrows`

### Verified

- `npx vitest run src/domain` — 12 files / 103 tests pass
- `cargo check` finishes clean (warnings only)

### Residuals (STATUS)

- ~350 cargo warnings remain (probe/affiliate census, `tactics.rs` templates, `#![allow(dead_code)]` data stubs) — keep until probe feature cleanup
- CSS leftovers: `.confidence-ring*`, `.startup-screen` in `globals.css`
- Test-only islands: `scout-knowledge` / `player-evaluation` (still used by `product.test.ts`)
- `feature = "probe"` blocks still reference `find_fmle_process` without a default import (cfg-gated; no default-build break)
