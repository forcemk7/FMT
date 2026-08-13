# Agent protocol

Workers ship tickets that already survived the need-to-have gate. The planning chat is a **poor developer / ruthless Scrum Master**: behavior over words, discard creep.

## Before any product work

1. Read `scrum/SCOPE.md`. If not need-to-have for the livelihood loop → stop; do not code.
2. Read `scrum/STATUS.md` and pick a ticket:
   - Prefer an explicitly named ticket
   - Else highest priority `ready` ticket (lowest `priority` number, then lowest ID)
3. Follow **Claim** below before editing product code (or before RE spikes on a claimed RE ticket).
4. Do not invent extra work mid-flight. No "while I'm here".

## Claim

1. Open `scrum/tickets/TXXX-*.md`
2. Set frontmatter: `status: claimed`, `owner`, `claimed_at`
3. Sync the Board in `scrum/STATUS.md`
4. Do not steal `claimed` / `in_progress` tickets

If nothing is `ready`, stop and ask the Scrum Master chat — do not invent tickets from chat wishlist.

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
5. **Then** report to the human: ticket ID, shipped, how tested, residual risk

If you only partially finished: leave `in_progress` or set `blocked` / return to `ready` with reason — never silent-abandon.

## Do not

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
