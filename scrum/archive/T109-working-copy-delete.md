---
id: T109
title: Working-copy extract — never live FM; delete after
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-16T21:45:00+02:00
started_at: 2026-08-16T21:48:00+02:00
completed_at: 2026-08-16T22:00:00+02:00
depends_on: [T107]
---

# T109 — Working-copy extract — never live FM; delete after

## Why

Extract must not touch live `Sports Interactive/…/games/*.fm` (locks / races with FM). Owner: always **copy** to a safe working location first, extract from the copy, then **delete** the working `.fm` so `data/saves` does not accumulate redundant GB. Identity JSON / roster store stay; binaries are disposable.

## Scope

- In: + / Update / any extract entry: write/upload lands in a **working copy** path (temp or dedicated work dir under the repo’s gitignored area). Refuse live `games/*.fm` (already law)
- In: After identity (and any list extract that runs) finishes or aborts: **delete** that working `.fm` (and temp decompress artifacts). Do not leave multi‑hundred‑MB copies sitting in `data/saves` as the permanent product
- In: Vitest / unit guard: refuse live games path; delete-after on success path
- Out: Squad list recipe (T110). HA/CA. Changing identity field recipes

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap or open live `games/*.fm` for extract
- Do **not** delete the user’s original file outside FMT’s working copy

## Acceptance criteria

- [x] Extract always runs on a working copy, never SI `games/*.fm`
- [x] Working `.fm` is gone after extract success and after abort/fail (best-effort)
- [x] One git commit `T109: …` on FMT/

## Notes / pointers

- ROADMAP §6 / SCOPE already say copy-then-extract; local “keep data/saves” is wrong for upload hygiene — working copy is ephemeral
- `refuse_live_fm_games_save` in extract scripts; upload handlers in the Vite API / `main.ts`

## Progress

- Shipped: `resolveWorkingUploadsDir` + `cleanupWorkingFm` in `save-paths.ts`. POST + / Update writes to `tmp/uploads`, extracts there, `finally` deletes via `cleanupWorkingFm` (refuses live SI path). GET scout disk extract disabled (same as GET roster). Refuse-live message says working copy.
- Verified: `npx vitest run tests/t109-working-copy-delete.test.ts tests/save-paths.test.ts tests/t096-honest-identity-manage-saves.test.ts tests/t108-squad-list-after-identity.test.ts` — 21 passed.
- Commit: _(filled after git)_
