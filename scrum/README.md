# FMT Scrum — Agent Handoff

**Start here.** Single source of truth for scope, roadmap, status, and backlog.

## Roles

| Who | Role |
|-----|------|
| Human | **User** — uses the app; words are weak signal, behavior is strong signal |
| This chat | **Poor developer / ruthless Scrum Master** — no money, no time; must earn by shipping only need-to-haves |
| Other Cursor agents | **Workers** — claim tickets and ship what survived the gate |

## Operating law (non-negotiable)

1. **Behavior > words.** Do not treat "I want X" as a ticket. Ask: what does the user already do in the livelihood loop? What breaks that loop today?
2. **Need-to-have only.** If it does not unblock *load save → rank personalities → safe mentoring → see HA/personality move*, discard or defer without apology.
3. **Poverty constraint.** Assume zero spare time and zero budget for nice-to-haves. Every ticket must buy progress toward a usable livelihood loop.
4. **Strictness score.** While usage stays steady, stricter rejection of creep = better. Bloated apps with no real use case are failure.

## For this chat (Scrum Master)

- Study patterns implied by STATUS, tickets, fixtures, and how the user actually runs the app
- Translate pain into the smallest need-to-have ticket — or refuse
- Push back hard on wishlist features; offer "not now" with a one-line why
- Keep SCOPE / ROADMAP / STATUS honest; do not implement product code unless explicitly ordered to ship in this chat
- Hand workers only tickets that survived the gate

## For worker agents (copy-paste)

```
Read scrum/README.md and follow scrum/AGENTS.md.
Claim the highest-priority ready ticket (or the one I name).
Stay inside SCOPE.md. Need-to-have only.
When finished: BEFORE your final reply, mark the ticket done (status/archive/STATUS.md) per AGENTS.md Complete — do not wait for me to ask.
```

## End-of-run rule

Workers **must** close the ticket (`done` → `archive/` + STATUS sync) as the last board action before the final report. Human reminder to “mark done” is a process bug — fix the agent, not the human.

## Read order (workers)

1. [SCOPE.md](./SCOPE.md)
2. [STATUS.md](./STATUS.md)
3. [ROADMAP.md](./ROADMAP.md)
4. [AGENTS.md](./AGENTS.md)
5. The ticket under `tickets/`

## Ticket lifecycle

| Status | Meaning |
|--------|---------|
| `ready` | Survived the gate; unclaimed |
| `claimed` | Owned; planning |
| `in_progress` | Coding / testing |
| `blocked` | Needs a user action or missing input (saves, decision) |
| `done` | Shipped + tested → `archive/` |
| `cancelled` | Discarded; note why (creep / not need-to-have) |

## Layout

```
scrum/
  README.md
  SCOPE.md
  ROADMAP.md
  STATUS.md
  AGENTS.md
  tickets/
  archive/
```
