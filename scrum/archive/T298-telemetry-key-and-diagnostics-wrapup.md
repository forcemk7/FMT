---
id: T298
title: Telemetry publishable key + readable Diagnostics (1.28 wrap-up)
status: done
priority: 1
owner: HQ chat (owner go)
claimed_at: 2026-09-30
started_at: 2026-09-30
completed_at: 2026-09-30
depends_on: [T290, T297]
---

# T298 — Telemetry publishable key + readable Diagnostics (1.28 wrap-up)

## Why

Last repo-side tweaks before the consolidated 1.28 live test pass. Supabase is deprecating the legacy `anon` key (end of 2026), and Settings > Diagnostics showed the last telemetry send as raw JSON.

## Scope

- In: switch T290's client to the publishable key; replace the JSON cell with plain-English text; version reset to 0.1.28; git wrap-up + push.
- Out: one-row-per-session telemetry (discussed, deferred — see Notes); any Supabase schema change.

## Acceptance criteria

- [x] Env var `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`; key sent on `apikey` header only (publishable keys aren't JWTs — `Authorization: Bearer` is rejected)
- [x] `.env.example` + `telemetry.ts` doc comment updated
- [x] Diagnostics "Last data sent" → **Last event**: `App launched` / `Load attempted` / `Loaded successfully` / `Load failed: <reason>` / `Load failed`, plus `(not delivered, HTTP n)` or `(not delivered, no connection)` when the send fails
- [x] Known `failure_stage` codes mapped to plain English; unknown codes fall back to underscores → spaces; DB still receives raw codes
- [x] Desktop version stays 0.1.28 (a `desktop:ship` run had bumped it to 0.1.29; owner reset it)
- [x] Working tree clean, pushed to origin

## Notes / pointers

- Sources: supabase.com/docs/guides/getting-started/api-keys, .../migrating-to-new-api-keys
- RLS policy (`to anon`), CSP `connect-src`, and the `anon_id` column need no change — publishable-key requests still run as the `anon` role.
- **Owner action:** rename the key line in `desktop/.env.local` to `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_…`.
- `desktop:ship` always does patch +1 (`scripts/bump-desktop-version.mjs`); 0.1.28 had already been set by hand in `6335160`. To rebuild without re-bumping: `npm run desktop:build`.
- **Deferred design:** one row per session (write once on success, or on close with the last failure stage). Owner chose to run the 3-rows-per-session experiment first. If the table gets noisy, cheapest path is a `session_id` column + a `sessions` view over `events` (keeps anon INSERT-only).

## Progress

- `f1bf5c0` — publishable key, `apikey` header only.
- `e13d755` — Diagnostics Last event text (`describeLastSent` in `domain/telemetry.ts`). Verified via a throwaway vitest printing all 8 cases; `tsc` clean outside pre-existing test-file errors. Not seen in the packaged app — needs the owner's rebuild + live pass.
- `251bdc9` — STATUS note.
- Discarded line-ending-only diffs on the version files and a build-rewritten `next-env.d.ts`.
- Protocol slip: used `git stash` once for a before/after `tsc` comparison; restored cleanly.
- Live verification folds into the consolidated 1.28 pass — reopen T298 if Diagnostics text or the key switch misbehaves.
