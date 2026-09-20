# Agent protocol

Workers ship tickets that already survived the need-to-have gate. The planning chat is a **poor developer / ruthless Scrum Master**: behavior over words, discard creep.

## Before any product work

1. Read `scrum/SCOPE.md`. If not need-to-have for the livelihood loop → stop; do not code.
2. Read `scrum/STATUS.md` and pick a ticket:
   - Prefer an explicitly named ticket
   - Else highest priority `ready` ticket (lowest `priority` number, then lowest ID)
3. Run `git status --short`. Anything modified/untracked/deleted that isn't explained by the ticket you're about to claim → stop before claiming. Don't silently work around it or `git stash` it away. If it's plausibly another live session's in-progress work (check for peer sessions if your tooling supports it), leave it alone and proceed touching only your own ticket's files; otherwise report the drift to the human before continuing.
4. Follow **Claim** below before editing product code (or before RE spikes on a claimed RE ticket).
5. Do not invent extra work mid-flight. No "while I'm here".

## Parallel sessions (only when the owner has explicitly allowed more than one ticket in flight)

The default is one ticket at a time (see **Stop the line**). When the owner has explicitly broken that rule, dirty files in `git status` can belong to a session that's still running, not to stale drift — and guessing by re-reading diffs or watching for a file to "appear mid-session" is slow and unreliable (this is literally how T295 first tried to sort this out on 2026-09-20 — don't repeat it). Instead, use the board, which is the actual source of truth for what's live:

1. `grep -l "status: claimed\|status: in_progress" scrum/tickets/*.md` — this is the authoritative signal for "is there live work right now," not file content or timestamps.
2. If that returns anything, treat **every** dirty file in the working tree as potentially in-flight, even ones that look unrelated to your own ticket. Do not commit, revert, or gitignore any of it — wait for those tickets to reach `done` or `blocked`, then re-check.
3. Only once that grep is empty is it safe to treat pre-existing dirty files as historical drift rather than live parallel work. At that point, whether a file was already shipped-but-undocumented or genuinely never committed is a `git log -- <file>` question, not a guess.

## Claim

1. Open `scrum/tickets/TXXX-*.md`
2. Set frontmatter: `status: claimed`, `owner`, `claimed_at`
3. Sync the Board in `scrum/STATUS.md`
4. Do not steal `claimed` / `in_progress` tickets

If nothing is `ready`, **stop**. Do not invent tickets. Do not edit SCOPE/ROADMAP. Do not “fix while I’m here.” Ask HQ. If STATUS says freeze, stop even if the human pastes a wishlist.

## In progress

1. Set `status: in_progress` and `started_at`; sync STATUS.md
2. Only acceptance criteria in the ticket
3. If blocked: `blocked` + `## Blockers` (what user action or input is missing); sync STATUS.md; report — then you may end

## Update

Keep `## Progress` current: tried / locked / failed / next step. Sync STATUS.md on status/owner/Now/Blockers changes only.

## Complete (mandatory — do this before you end)

**Do not wait for the human to ask you to close the ticket.** Closing the board is part of shipping. Ending the turn with `in_progress` / `claimed` after the work is finished is a protocol failure.

When acceptance criteria are met and verified, **in this order, before the final user message**:

1. Fill final `## Progress` (what shipped / how verified)
2. Set frontmatter: `status: done`, `completed_at`
3. Move file: `scrum/tickets/TXXX-*.md` → `scrum/archive/TXXX-*.md`
4. Update `scrum/STATUS.md` Board + Recently done (clear your owner row)
5. **Git commit on `FMT/`** (see **Git** below). Put the SHA in Progress.
6. **Then** report to the human: ticket ID, shipped, how tested, commit SHA, residual risk

If you only partially finished: leave `in_progress` or set `blocked` / return to `ready` with reason — never silent-abandon. Never end a turn with an uncommitted diff for your own ticket sitting in the working tree: either finish the commit step below, or if blocked/partial, name exactly what's uncommitted and why in `## Progress` — so a future session doesn't mistake your legitimate in-flight work for unrelated drift and touch it. This is how T295 (repo hygiene) had to happen; don't recreate the backlog it just cleaned up.

## Git (one commit per ticket)

Work only in `C:\Users\mrdev\Documents\Projects\FMT` — never `git add` from the parent `Projects/` folder.

1. Stage **only files this ticket changed** (not `git add -A`).
2. Do not stage `data/saves/`, `data/faces/`, `data/logos/`, `*.fm`, `.env`, secrets.
3. Commit:

```
git commit -m "T0XX: short why"
```

4. Do **not** push unless the ticket says to. Do **not** amend unless the ticket says to and the commit is yours and unpushed.
5. If the commit is rejected by a hook, fix and make a **new** commit — do not `--no-verify`.

Archiving without a commit is not done.

**Known non-ticket artifact:** `npm run desktop:ship` (`scripts/bump-desktop-version.mjs`) rewrites `desktop/package.json`, `desktop/src-tauri/tauri.conf.json`, `desktop/src-tauri/Cargo.toml`, and `desktop/src/domain/distribution.ts`; a subsequent `cargo build` then updates `Cargo.lock`'s own version line as a side effect. If that's all `git status` shows modified, it's not your ticket's scope creep — commit it as its own small `chore: bump desktop version to X.Y.Z` commit (if you're the one who ran `desktop:ship`), or leave it alone for whoever did. Don't sweep it into an unrelated ticket's commit, and don't revert it.

## Stop the line

- Empty board or STATUS freeze → end. Shipping a ticket you wrote yourself is a protocol failure.
- One ticket per run. Files outside that ticket’s acceptance = out of bounds.
- Do not grow SCOPE from a worker chat.

## Do not

- Extract or mmap `.fm` from `Documents/Sports Interactive/…/games/` — copy the selected save into `data/saves` first
- Stream live SI `graphics/` on `/api/faces` or `/api/logos` when a repo copy exists — copy missing files into `data/faces` / `data/logos` once, then serve those
- Invent live-memory offsets or heap/idiom world scans without checking `research/ecosystem.md`, `research/recipes.md`, and `research/live-read.md` first; when you find a public FM tool, **update research/ecosystem.md**; when you lock a first-party offset/trap, **update research/recipes.md** in the same run
- Leave new RE/probe-only Rust helpers on the default feature set — gate with `#[cfg(feature = "fm-probe")]` (see `research/fm-probe-gate.md`); do not spam `dead_code` on product builds
- Run `git stash` / `git stash pop` as a casual debugging convenience — check `git status` immediately first, and prefer `git diff`, a throwaway branch, or a worktree when you genuinely need a clean-baseline comparison. A stash on top of unrelated dirty state is exactly how T295 (repo hygiene) had to happen
- Commit `.cursor/` — it is gitignored; edit `research/` and optionally re-copy per `research/agent-local-setup.md`
- Expand scope from verbal wants
- Rewrite SCOPE/ROADMAP priorities without Scrum Master chat
- Leave abandoned `claimed` / `in_progress` tickets
- End a successful run without step **Complete** above
- Expect the human to prompt “mark it done”

## Ticket frontmatter

```yaml
id: T000
title: short title
status: ready | claimed | in_progress | blocked | done | cancelled
priority: 1
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
```
