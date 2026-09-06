---
id: T252
title: ME clubTeam logos via same UniqueID path
status: done
priority: 2
owner: auto
claimed_at: "2026-09-06T23:20:00+02:00"
started_at: "2026-09-06T23:20:00+02:00"
completed_at: "2026-09-06T23:28:00+02:00"
depends_on: [T251]
---

# T252 — ME clubTeam logos via same UniqueID path

## Why

Match experience cards for second-hop II (e.g. Kaiserslautern II) show empty logos while FM and other ME cards (Schalke II) resolve. Same UniqueID → pack logo mechanic; no parent-logo fallback.

## Scope

- In: Warm `clubTeams[].clubId` (not only managed / players / clubs)
- In: ClubLogo must not permanent-cache miss while logo index is still building / pending fill
- In: After index exists, drain newly queued logo IDs (warm after first build)
- Out: Parent-club logo fallback; pack invent; live SI graphics stream

## Acceptance

1. ME card for Kaiserslautern II (and any other loaded `clubTeams` with its own UniqueID) resolves logo the same way as Schalke II / Kaiser First — UniqueID only
2. No parent UniqueID substitution when the II logo is missing or late
3. Late pack-index fill refreshes the UI (no stuck empty after ~9s race)

## Progress

- Root cause: warm omitted `clubTeams` UniqueIDs; ClubLogo applied permanent null before background logo index finished copying to `logo-cache-trim`
- Shipped: warm includes `clubTeams[].clubId`; `LogoLookup::{Found,Pending,Missing}` + post-index pending drain; ClubLogo soft-retries while `pending`; longer `fmt-logos-updated` clears
- Verified: `cargo check` in `desktop/src-tauri`
- Commit: (this ticket)
