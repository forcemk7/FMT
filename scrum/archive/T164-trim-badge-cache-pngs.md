---
id: T164
title: Trim badge PNGs on cache for equal fill
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T18:34:00Z
started_at: 2026-08-26T18:34:00Z
completed_at: 2026-08-26T18:41:00Z
depends_on: [T160]
---

# T164 — Trim badge PNGs on cache for equal fill

## Why

Equal frames still looked uneven: nation plates padded/wide; club crests fill canvas. Trim on cache + cover for wide leftovers.

## Acceptance criteria

- [x] Cached logo/flag PNGs cropped to content when alpha allows
- [x] Old caches ignored (`logo-cache-trim` / `flag-cache-trim`)
- [x] Wide leftovers use cover (aspect ≥ 1.25)
- [x] cargo check + trim unit tests pass

## Progress

Trim-on-cache via `image` crate; cache dir bump; UI `data-fit` cover fallback. Tests 2/2. Residual: fully opaque wide flag art still needs cover (expected).
