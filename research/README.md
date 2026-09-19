# Research

FMT’s **R&D / knowledge** home — compounded while building the app, kept out of the product tree and out of the scrum board.

| File | What |
|------|------|
| [`ecosystem.md`](./ecosystem.md) | Public FM tools, steal modes, community recipes |
| [`recipes.md`](./recipes.md) | **FMT-locked** offsets, traps, open residuals |
| [`live-read.md`](./live-read.md) | Operational live-read law (world tables, affiliations, do/don’t) |
| [`fm-probe-gate.md`](./fm-probe-gate.md) | Cargo `fm-probe` feature — quiet product builds |
| [`agent-local-setup.md`](./agent-local-setup.md) | Optional: copy law into `.cursor` / Claude locally |
| [`club-team-display.md`](./club-team-display.md) | Audit: every UI surface showing club/team name, which function powers it, where they diverge |

**Process board** stays in `scrum/` (SCOPE, STATUS, tickets).  
**Product** stays in `desktop/`.  
**Editor rules** (`.cursor/`) are local QoL — see [`agent-local-setup.md`](./agent-local-setup.md).

## Why this folder exists

1. Future-proof patches and new FM versions without rediscovering heap walks.
2. Enable adjacent OSS / tooling that reuses verified recipes.
3. Keep publishable knowledge separate from RE scrap and UI code.
4. Single source of truth for agents — not buried only in gitignored Cursor files.

## How to maintain

- Before inventing live-memory RE: read `ecosystem.md` + `recipes.md` + `live-read.md` first.
- Public find → update `ecosystem.md` in the same run.
- First-party lock or discard → update `recipes.md` in the same run.
- Probe / build hygiene → `fm-probe-gate.md`.
- Do not resurrect deleted probe modules; start from these docs + ticket archives.

## Growth rule

Add a focused file under `research/` only when `recipes.md` (or ecosystem) gets too fat to scan — e.g. `affiliates.md`. Do not invent a second ticket board here.
