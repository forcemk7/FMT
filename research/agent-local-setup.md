# Agent local setup (optional QoL)

Canonical agent / RE law lives in **`research/`** (versioned with the repo).  
**`.cursor/`** and Claude project rules are **local** — gitignored. Do not commit them.

## Why

Honest split: knowledge in git; editor auto-inject is a personal convenience. Clone the repo → you still have the law under `research/`. Want Cursor to auto-apply it → copy once (or after pulls that change research).

## Recommended copies

| Canonical (git) | Optional local |
|-----------------|----------------|
| [`live-read.md`](./live-read.md) | `.cursor/rules/fm-live-read.mdc` |
| [`fm-probe-gate.md`](./fm-probe-gate.md) | `.cursor/rules/fm-probe-gate.mdc` |
| [`../scrum/AGENTS.md`](../scrum/AGENTS.md) | `.cursor/rules/scrum.mdc` (thin always-apply pointer is enough) |

Also useful locally (not required in git): Claude project instructions that say “read `research/` + `scrum/AGENTS.md` before RE or tickets.”

## Install (Cursor)

From repo root (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path .cursor\rules | Out-Null
Copy-Item -Force research\live-read.md .cursor\rules\fm-live-read.mdc
Copy-Item -Force research\fm-probe-gate.md .cursor\rules\fm-probe-gate.mdc
```

Keep YAML frontmatter at the top of those files if you want Cursor globs / `alwaysApply`. Adjust globs to match your machine if needed.

Refresh Cursor rules / reload window after copying.

## Install (Claude / other)

Point project instructions at:

1. `scrum/AGENTS.md` — worker protocol  
2. `research/ecosystem.md` + `research/recipes.md` — before inventing offsets  
3. `research/live-read.md` + `research/fm-probe-gate.md` — live RE + quiet builds  

## After pulling

If `research/live-read.md` or `research/fm-probe-gate.md` changed, re-copy into `.cursor/rules/` (or re-read research directly — agents that follow AGENTS already will).

## Do not

- Force-add `.cursor/` to git  
- Treat local `.mdc` as source of truth — edit **`research/`** then re-copy  
