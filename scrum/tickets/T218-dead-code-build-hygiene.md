---
id: T218
title: Dead code / unused import build hygiene
status: ready
priority: 6
owner: null
claimed_at: null
started_at: null
completed_at: null
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

- [ ] Before/after wall times recorded in Progress (same machine, same commands)
- [ ] No unused-import / dead-code sweep that breaks `cargo test` / vitest for touched packages
- [ ] Diff is deletive or import-only except tiny glue if a delete requires it
- [ ] STATUS notes residual suspects (if any) rather than inventing a follow-up epic

## Notes / pointers

- Start: `desktop/src` unused imports (tsc/eslint if configured), then `desktop/src-tauri` `cargo check` warnings
- Do not stage `data/`; do not touch live offsets “while cleaning”
- Prefer several small commits only if the ticket is split mid-flight — default one commit per AGENTS.md

## Progress

Ready after T217.
