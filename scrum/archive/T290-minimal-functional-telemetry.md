---
id: T290
title: Minimal functional telemetry — install → launch → load → outcome
status: done
priority: 2
owner: auto
claimed_at: 2026-09-23
started_at: 2026-09-23
completed_at: 2026-09-28
depends_on: [T215]
---

# T290 — Minimal functional telemetry

## Why

Owner has no reliable signal on whether the tool actually works for people who download it — currently dependent on unreliable, low-volume forum follow-up (two load-failure reports, zero diagnostics screenshots provided despite being asked). Explicitly not interested in vanity metrics (page views, download counts, comment counts) — those are already visible and don't answer the real question: does the app run, does a load succeed or fail and why, and do people come back. This is the direct instrumentation pillar of the funded token spend behind FMT 1.28.

## Scope

- In: Anonymous, disclosed (visible in Settings / User Preferences) event reporting for: installer run, app launch, load-save attempt, load outcome (success / failure + failure reason if determinable), and repeat-run signal (has this anon id run successfully before)
- In: Failure reason should reuse whatever T215 Diagnostics already determines locally — do not invent a second failure-classification system
- In: Clear, honest user-facing disclosure of what is sent — no silent collection
- Out: Any personally identifying data, save contents, player/club data, IP-based analytics dashboards beyond what's needed to answer the questions above
- Out: A/B testing framework, funnels beyond install → launch → load → outcome, marketing analytics

## Acceptance criteria

- [ ] Owner can see: installs, launches, load attempts, load outcomes with failure reasons, and return-usage rate, without depending on user forum replies
- [ ] Disclosure is visible in-app before or alongside first send
- [ ] One commit `T290: …`

## Notes / pointers

- Depends on T215 landing first — telemetry should report the same accurate signals Diagnostics now surfaces locally, not a second guess at what happened
- **Destination decided (HQ, 2026-09-23): Supabase.** Client posts directly to Supabase's REST API with a bundled public anon key — no custom backend function to write or deploy. Security comes entirely from RLS (anon role: INSERT only), not from hiding the key.
- **Mandatory, no opt-out toggle, for this version.** Scoped strictly to app-performance signals (launch/load/outcome) — owner explicitly wants this outside the optional User Preferences section, since the whole point is an unbiased usage signal to inform 1.28 investment decisions. Any richer/product-usage telemetry later would be a separate, opt-in expansion — not this ticket.
- Failure vocabulary: reuse `status.failureStage` (`connector.rs`'s `ExtractionFailure.stage` strings, e.g. `open_read_only_process`, `manager_signature`, `player_collection`) verbatim as `failure_reason` — do not invent a second classification.
- Throttling: only send `load_outcome` when it differs from the last outcome sent this session (avoids T274's heartbeat/retry loop spamming identical failure events).
- "Install" = first-ever `launch` row per `anon_id` (derived by query later, not its own event/column) — no NSIS installer hook needed for v1.
- "Return-usage rate" = `anon_id`s with rows on more than one distinct `created_at::date` — derived by query, not its own event.

### Owner tasks (Supabase console — not in this repo)

- [ ] Create a Supabase project dedicated to FMT telemetry (keep it isolated from any future unrelated Supabase use)
- [ ] SQL editor — run:
  ```sql
  create table events (
    id bigint generated always as identity primary key,
    anon_id uuid not null,
    event_type text not null check (event_type in ('launch','load_attempt','load_outcome')),
    outcome text check (outcome in ('success','failure')),
    failure_reason text,
    app_version text not null,
    created_at timestamptz not null default now()
  );

  alter table events enable row level security;

  create policy "anon can insert" on events
    for insert
    to anon
    with check (true);

  -- Bounds the one failure mode we actually expect: T274's heartbeat retrying
  -- a stuck/failing load roughly every 8s would otherwise flood identical
  -- rows for a single install. Deliberately not defending against deliberate
  -- payload forgery (e.g. a spoofed created_at) — that's a more sophisticated
  -- threat than this project's model calls for (see ticket discussion,
  -- 2026-09-28) and the owner is already treating this data as approximate.
  create or replace function enforce_event_rate_limit()
  returns trigger as $$
  begin
    if (
      select count(*) from events
      where anon_id = new.anon_id
        and event_type = new.event_type
        and created_at > now() - interval '1 day'
    ) >= 50 then
      raise exception 'rate limit exceeded';
    end if;
    return new;
  end;
  $$ language plpgsql;

  create trigger events_rate_limit
  before insert on events
  for each row execute function enforce_event_rate_limit();
  ```
- [ ] Project Settings → API — copy the Project URL and the `anon` public key (these two values go into `.env.local`, not committed)
- [ ] Verify RLS actually blocks reads: try a `SELECT` against the table using the anon key (SQL editor "run as anon" or a direct REST call) and confirm it's rejected
- [ ] Leave **Realtime disabled** for this table (default for a new table) — turning it on would broadcast every inserted row over a websocket to any subscriber, bypassing the anon-can't-SELECT protection above

### Repo tasks (FMT/desktop — worker session on `FMT/`, not this HQ chat)

- [ ] Supabase URL + anon key as build-time config; update `tauri.conf.json`'s `security.csp` `connect-src` to allow the Supabase project domain (currently locked to `'self' ipc: http://ipc.localhost` — `connector.rs`/`tauri.conf.json:25-27`)
- [ ] Add `telemetryId` (uuid, generated once via `crypto.randomUUID()`) to `domain/preferences.ts`'s schema — lives alongside but is **not** a `PreferenceToggleCell` (no user-facing toggle)
- [ ] Small `telemetry.ts` client: one function to POST an event row to the Supabase REST endpoint
- [ ] Wire fire points: `launch` in `FMTApp`'s existing mount effect (`fmt-app.tsx:152-154`); `load_attempt`/`load_outcome` in `checkConnection` (`fmt-app.tsx:216-256`), with the outcome-change throttle
- [ ] Read app version (Tauri/Cargo package version) and attach as `app_version` on every event
- [ ] Disclosure text — its own small read-only cell (not under User Preferences), plain language: anonymous, what's tracked (4 things), no PII/save data, never sold
- [ ] QA: live-trigger each event type; confirm the Supabase row's `failure_reason` matches what Diagnostics shows on screen for the same failure; confirm `anon_id` persists across reloads and regenerates after clearing storage; confirm the RLS negative-test from above
- [ ] One commit `T290: …`

## Progress

**Repo-side code done, not yet committed — blocked on owner's Supabase setup for final live QA.**

- `SUPABASE_URL`/`SUPABASE_ANON_KEY` read from `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY` in `.env.local` (gitignored already, per this repo's existing `.env.*` convention; `.env.example` documents the shape). Missing/empty env is a deliberate no-op: `postEvent` skips silently, so this is safe to build against before `.env.local` exists. Owner creates/edits `.env.local` directly — not something the worker session reads.
- `telemetryId` added to `domain/preferences.ts`'s schema, generated once via `crypto.randomUUID()` on first load, persisted through the existing merge-onto-defaults path
- `connect-src` in `tauri.conf.json` opened to `https://*.supabase.co` (wildcard, so no follow-up edit needed once the real project exists)
- Fire points wired: `launch` in `FMTApp`'s existing boot-marker effect; `load_attempt`+`load_outcome` in `checkConnection`, throttled to only send when the outcome (success/failure + reason) differs from the last one sent this session — reuses `status.failureStage` verbatim as `failure_reason`, no new classification
- Disclosure added as its own `Telemetry` section in Settings (outside User Preferences, no toggle — always-on per owner's call), using the existing diagnostics-cell pattern
- Verified locally: `tsc --noEmit`/`eslint`/`vitest` clean on touched files (pre-existing unrelated errors in `attribute-history.test.ts`/`live-data.test.ts` and one pre-existing `fmt-app.tsx` lint warning confirmed via `git stash` to predate this work); live-checked in dev preview — Settings > Telemetry renders the disclosure text and a real generated anon id, no console/server errors
- **Not yet done**: owner's Supabase-side setup (table/RLS/rate-limit trigger, project URL + anon key — see "Owner tasks" above) and the live QA pass from the "Repo tasks" checklist (trigger each event type against the real table, compare `failure_reason` to what Diagnostics shows on screen, confirm the RLS negative-test).

**Closed 2026-09-28 by explicit owner decision, ahead of that QA.** Owner chose to close out T290's repo-side work now and batch live verification with T293/T139 into one build-and-test pass at the end of FMT 1.28, rather than block on Supabase setup before starting the next ticket. If that pass finds anything wrong here — Supabase setup, the fire points, the throttle, the disclosure copy, whatever — **reopen this ticket** (`status: in_progress` or `blocked`, move back out of `archive/`) rather than filing a new one, since the acceptance criteria were never actually verified live, only built and locally checked (`tsc`/`eslint`/`vitest` clean, dev-preview render confirmed). Commit covers the code above; no live Supabase data has been produced or checked against real values.
