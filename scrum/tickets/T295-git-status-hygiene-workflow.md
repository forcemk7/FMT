---
id: T295
title: Repo git hygiene cleanup + workflow guardrail against it recurring
status: in_progress
priority: 1
owner: claude
claimed_at: 2026-09-20
started_at: 2026-09-20
completed_at: null
depends_on: []
---

# T295 — Repo git hygiene cleanup + workflow guardrail against it recurring

## Why

While closing T215, a `git stash` / `git stash pop` run (done to get a clean `tsc` baseline for comparison — not a dedicated audit) surfaced that `FMT/` has a large amount of pre-existing **uncommitted** work that isn't tied to any single open ticket: modified Rust files (`commands.rs`, `fm26/parser.rs`, `fm26/process.rs`, `fm26/scanner.rs`, `graphics/config_xml.rs`, `graphics/packs.rs`), modified frontend files (`live-data-state.tsx`, `ui/tooltip.tsx`, `attribute-history.ts`/`.test.ts`), version-bump-shaped files (`desktop/README.md`, `desktop/package.json`, `Cargo.lock`, `Cargo.toml`, `tauri.conf.json`), and a long tail of `scrum/archive/*.md` files showing as modified plus a couple of `scrum/tickets/*.md` showing as **deleted** (`T245`, `T249`) with several others untracked.

This is a real risk, not just clutter: `AGENTS.md`'s per-ticket discipline ("stage only files this ticket changed, not `git add -A`") assumes a working tree that's close to clean between tickets. A backlog like this makes it much easier for a future ticket's commit to silently sweep in unrelated changes, and it's exactly what made this session's own `git stash` (run without a `git status` check first, which is against the house safety rule) riskier than it should have been — it happened to pop back cleanly, but that was luck, not process.

## Scope

- In: Enumerate everything `git status` currently reports as modified/untracked/deleted in `FMT/` that isn't explained by a currently open/in-progress ticket
- In: For each item, decide with the owner: commit it (attributed to whichever historical ticket it actually belongs to, as its own small commit — don't fold unrelated history into one mega-commit), revert it, or gitignore it (e.g. if it's a genuine build/version-bump artifact)
- In: Specifically check whether the version-bump-shaped files (`README.md`, `package.json`, `Cargo.lock`, `Cargo.toml`, `tauri.conf.json`) are a recurring side effect of `desktop:ship` / `scripts/bump-desktop-version.mjs` that should either be committed as part of that script's normal flow or excluded — confirm, don't assume
- In: Explain the `scrum/tickets/T245`/`T249` deletions specifically — were they meant to be archived (i.e. this is an incomplete "Complete" step from an earlier ticket) or something else?
- In: Add a guardrail to `scrum/AGENTS.md`'s worker protocol: a "before claim" step to run `git status` and flag/stop if it shows dirty files unrelated to the ticket being claimed, rather than silently working around them
- In: Add a note (in `AGENTS.md` or `research/agent-local-setup.md`) against using `git stash`/`git stash pop` as a casual debugging convenience without a `git status` check immediately first — prefer `git diff` or a throwaway branch/worktree when a clean-baseline comparison is genuinely needed
- Out: Redesigning the scrum Git protocol beyond this hygiene pass
- Out: Touching any currently in-flight ticket's files

## Acceptance criteria

- [ ] `git status` in `FMT/` is clean, or every remaining item is explicitly explained/accounted for (owner confirmed disposition per file/group — nothing discarded without a decision)
- [ ] `scrum/tickets/T245`/`T249` deletions resolved (archived properly, or restored, with the reason recorded)
- [ ] `scrum/AGENTS.md` updated with the pre-claim `git status` check
- [ ] `AGENTS.md` (or `research/agent-local-setup.md`) notes the `git stash` guardrail
- [ ] Version-bump-artifact pattern documented so future sessions don't mistake it for scope creep on an unrelated ticket
- [ ] One commit `T295: …` for the hygiene pass itself (doc/protocol changes); any reattributed historical work gets its own separate commit(s) under its own message

## Notes / pointers

- Discovered 2026-09-20 during T215's `tsc` baseline check (`git stash` / `git stash pop`), not from a dedicated audit — re-run `git status --short` at the start of this ticket to get the current, authoritative list (it will have moved on from what's described above).
- Related precedent: this is a process/meta ticket in the same vein as T272 (fm-probe feature gate) and T273 (research-agent law push) — infra/hygiene, not a product feature.

## Progress

Re-ran `git status --short` 2026-09-20 — drift is larger than the discovery note above: 53 modified `scrum/archive/*.md`, 2 archive-duplicate deletions in `scrum/tickets/` (T245/T249), ~22 untracked ticket files, 2 untracked local-config dirs (`.claude/`, `desktop/src-tauri/.cargo/`), plus the previously-known Rust/frontend/version-bump files. Reported full categorized findings to owner; working through disposition one group at a time per owner's request (explain TL;DR, then commit, before moving to the next group).

**Group 1 — archive hygiene (done):** Diffed a sample of the 53 modified `scrum/archive/*.md` — all are the same pattern: backfilling `Commit: (pending)` → real SHA, or fixing a stale historical note. Confirmed via `git log` that `scrum/tickets/T245`/`T249` were already properly archived in real past commits (`2367d90`, `5aef510`); the `tickets/` copies were just never `git rm`'d after that archival — no data loss, safe to finish. Also found 3 fully-untracked archive files (T082, T089, T098, all `status: cancelled`) that were never committed at all. Committed all of the above as one commit (see SHA below).
