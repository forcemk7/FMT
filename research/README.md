# Research

FMT’s **R&D / knowledge** home — compounded while building the app, kept out of the product tree and out of the scrum board.

| File | What |
|------|------|
| [`ecosystem.md`](./ecosystem.md) | Public FM tools, steal modes, community recipes |
| [`recipes.md`](./recipes.md) | **FMT-locked** offsets, traps, open residuals |

**Process board** stays in `scrum/` (SCOPE, STATUS, tickets).  
**Product** stays in `desktop/`.  
**Operational agent law** for live-read edits: `.cursor/rules/fm-live-read.mdc` → points here.

## Why this folder exists

1. Future-proof patches and new FM versions without rediscovering heap walks.
2. Enable adjacent OSS / tooling that reuses verified recipes.
3. Keep publishable knowledge separate from RE scrap and UI code.

## How to maintain

- Before inventing live-memory RE: read `ecosystem.md` + `recipes.md` first.
- Public find → update `ecosystem.md` in the same run.
- First-party lock or discard → update `recipes.md` in the same run.
- Do not resurrect deleted probe modules; start from these docs + ticket archives.

## Growth rule

Add a focused file under `research/` only when `recipes.md` (or ecosystem) gets too fat to scan — e.g. `affiliates.md`. Do not invent a second ticket board here.
