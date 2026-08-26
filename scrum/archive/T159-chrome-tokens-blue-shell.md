---
id: T159
title: Standardize chrome tokens + blue-led shell
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T159 — Standardize chrome tokens + blue-led shell

## Why

Compact nav used a white pill while expanded used gold — forced nitpicking. Shell still read too green vs FM’s blue night atmosphere.

## Scope

- In: `--chrome-*` / `--control-*` contract for all header controls; compact trigger = same active chrome as nav; blue-dominant shell with faint green atmosphere only
- Out: Per-screen one-off colors; theme picker

## Acceptance criteria

- [x] Dashboard compact + expanded active states share gold chrome tokens
- [x] No white/light nav pill on dark shell
- [x] Canvas is blue-led (green only as subtle wash)

## Progress

- Rewrote `fmt-desk.css` token contract
- Commit: _(filled after git)_
