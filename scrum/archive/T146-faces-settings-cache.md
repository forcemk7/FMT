---
id: T146
title: Player faces via settings path + local cache
status: done
priority: 3
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25T20:35:00Z
completed_at: 2026-08-25T20:40:00Z
depends_on: [T144]
---

# T146 — Player faces via settings path + local cache

## Why

Cutout faces make Loop A pleasant. GS shipped lookup code but only checked `graphics/faces` — real packs live under megapack folders. No images shipped in the fork.

## Acceptance criteria

- [x] Settings shows graphics path + Update faces control
- [x] Resolve from local cache first; copy miss from SI packs once
- [x] After load, background warm of squad IDs
- [x] Pack discovery includes Cutout/NewGAN-style subfolders
- [x] cargo check passes

## Progress

Shipped pack discovery + `%LOCALAPPDATA%\com.fmt.fm26\face-cache`, settings UI, post-load warm. Verified cargo check. Residual: logos still shallow-ish; huge config.xml only used if direct `face_{id}` miss.
