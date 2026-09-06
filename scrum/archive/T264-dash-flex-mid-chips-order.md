---
id: T264
title: Dash true flex fill + mid-tone chip padding + detail order
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T01:51:00+02:00"
started_at: "2026-09-07T01:51:00+02:00"
completed_at: "2026-09-07T01:55:00+02:00"
depends_on: [T263]
---

# T264 — Dash true flex fill + mid-tone chip padding + detail order

## Why

Hardcoded peek density still scrolls on small viewports and wastes space on large ones. Loyalty/Temperament mid-tone chips lose padding (`attr-tone-mid { padding:0 }`) and overlap. Ability/ME detail order needs a pass.

## Scope

- In: Dash grid + peek rows flex to fill available space; no widget scrollbars (overflow hidden, rows shrink)
- In: Fix mid-tone chip padding (do not zero padding on dash chips / stop global mid padding kill)
- In: Detail order — players: age, pos, team, PA, CA; talent: age, pos, team, CA, PA; ME: age, from→to, CA, PA, `#rank pos`
- Out: Dynamic peek count JS; division RE

## Acceptance

- [x] No scrollbar inside dash widgets at typical fullscreen; rows grow on large viewports
- [x] Loyalty 8 / Temperament 8 pills no longer overlap
- [x] Detail order matches above
- [x] Commit `T264: …`

## Progress

- Root cause: `body.fmt-shell .attr-tone-mid { padding:0 }` — values 8–12 (Loyalty/Temperament) are mid-band
- Peek rows `flex:1 1 0`; faces `clamp(20px,4.2vh,36px)`; grid fills viewport; no widget scroll
- Detail order updated
- Commit: (pending)
