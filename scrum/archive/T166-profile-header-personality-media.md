---
id: T166
title: Personality/Media in profile header; General = CA/PA only
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T166 — Personality/Media in profile header; General = CA/PA only

## Why

Personality and Media Handling are labels, not attributes — they clutter General. Traits is empty. Put labels next to the player name; General keeps Ability + Potential only.

## Scope

- In: Profile header shows inferred Personality + Media Handling; General column = Ability + Potential only; drop Traits / Personality / Media from General
- Out: Squad HAS Personality column; Traits RE; reading FM strings from memory

## Acceptance criteria

- [x] Profile header shows Personality and Media Handling when inferred (or `—` if incomplete)
- [x] General column lists only Ability and Potential
- [x] Traits / Personality / Media Handling rows gone from General

## Progress

- Header line under club/CA/PA: `Personality · Media Handling`
- General = Ability + Potential only
- Commit: _(filled after git)_
