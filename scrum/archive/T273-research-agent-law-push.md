---
id: T273
title: Research-owned agent law + untrack .cursor; push GitHub
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T04:03:00+02:00"
started_at: "2026-09-07T04:03:00+02:00"
completed_at: "2026-09-07T04:10:00+02:00"
depends_on: [T272]
---

# T273 — Research-owned agent law + untrack .cursor; push GitHub

## Why

`.cursor/` is local QoL, not the repo’s source of truth. Canonical agent/RE law lives in `research/`; optional copy into `.cursor` / Claude rules. Then push `main` to GitHub.

## Scope

- In: `research/fm-probe-gate.md`, `research/live-read.md`, `research/agent-local-setup.md`; README index
- In: Revert `.gitignore` to ignore all `.cursor/`; `git rm --cached` tracked rules
- In: Point AGENTS / ecosystem / SCOPE at `research/`
- In: Root README mention `research/` + local setup
- In: `git push -u origin main`
- Out: Deleting local `.cursor` on disk; rewriting product code

## Acceptance

- [x] No `.cursor/` files tracked in git; research holds probe-gate + live-read law
- [x] agent-local-setup documents optional copy into `.cursor` / Claude
- [x] Push to `origin` succeeds
- [x] Commit `T273: …` then push

## Progress

- research/: live-read, fm-probe-gate, agent-local-setup; README index
- Untracked `.cursor/rules/*`; gitignore `.cursor/` only
- Pointers: AGENTS, SCOPE, scrum README, ecosystem, Cargo.toml, root README
- Commit + push: (pending)
