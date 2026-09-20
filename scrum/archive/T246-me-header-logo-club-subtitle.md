---
id: T246
title: ME card header — logo + club + TeamType subtitle
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T21:54:00+02:00"
started_at: "2026-09-06T21:54:00+02:00"
completed_at: "2026-09-06T21:57:00+02:00"
depends_on: [T244]
---

# T246 — ME card header — logo + club + TeamType subtitle

## Why

Logo boxes look framed; TeamType-only titles make two Schalke “First Team” cards ambiguous. Profile Club fact is the reference: flush logo + text.

## Scope

- In: ME header = `{logo} {clubName}` + `{TeamType}` subtitle; drop redundant position·rank meta
- In: Logo flush (no border/pad/fill), height ≈ name+subtitle stack (profile-fact style)
- Out: Loan-byte filter (T245); shortName RE; changing Squad desk

## Acceptance criteria

- [x] Header shows club name + TeamType subtitle; no DC/rank in title
- [x] Logos match profile Club fact treatment (no container chrome)
- [x] Commit `T246: …`

## Progress

Shipped: identity row = flush ClubLogo + club name (from `clubs` by id); TeamType subtitle replaces position·rank. Logo 22px, border/pad/bg cleared like `.player-fact-identity`. Verified vitest (10).

Commit: `d1bff0c`
