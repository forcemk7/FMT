# FMT Scrum — Agent Handoff

**Start here.** Scope = law. Roadmap = funded features. Status = ticket board.

## Roles

| Who | Role |
|-----|------|
| Human | **User** — uses the app; words are weak signal, behavior is strong signal |
| This chat | **Poor developer / ruthless Scrum Master** — no money, no time; must earn by shipping only need-to-haves |
| Other Cursor agents | **Workers** — claim tickets and ship what survived the gate |

## Operating law (non-negotiable)

1. **Behavior > words.** Do not treat "I want X" as a ticket. Ask: what does the user already do in the livelihood loop? What breaks that loop today?
2. **Need-to-have only.** If it does not unblock *Squad HA → Loans honesty → Progress CA/HA → Mentoring reminder → group in FM*, discard or defer without apology.
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
Read scrum/README.md, scrum/AGENTS.md, scrum/STATUS.md.
If STATUS says freeze, or the Board has no ready ticket: stop. Do not invent work. Do not edit SCOPE.
Otherwise claim only the ticket I name (or the single ready ticket).
Stay inside that ticket’s acceptance. No second ticket.
If the ticket touches FM live memory / offsets / world index: read `research/ecosystem.md` + `research/recipes.md` before inventing RE; update them if you find or lock something.
When finished: BEFORE your final reply, Complete (archive + STATUS) then git commit on FMT/ per AGENTS.md Git — one commit, message T0XX: why. Do not push unless the ticket says to.
```

## End-of-run rule

Workers **must** close the ticket (`done` → `archive/` + STATUS sync) as the last board action before the final report. Human reminder to “mark done” is a process bug — fix the agent, not the human.

## Read order (workers)

1. [SCOPE.md](./SCOPE.md)
2. [STATUS.md](./STATUS.md)
3. [ROADMAP.md](./ROADMAP.md)
4. [AGENTS.md](./AGENTS.md)
5. The ticket under `tickets/`
6. If the ticket touches live FM memory / offsets / FMLE / world index: [`research/ecosystem.md`](../research/ecosystem.md) + [`research/recipes.md`](../research/recipes.md) **before** inventing RE

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

Knowledge (not the board): [`../research/`](../research/) — public ecosystem + FMT recipes.

## Research index

[`research/ecosystem.md`](../research/ecosystem.md) compounds public FM tooling knowledge.  
[`research/recipes.md`](../research/recipes.md) is **FMT first-party** locked offsets / traps.  
Workers: **check both before inventing memory RE.** Update them when you find or verify a source. Operational law: [`research/live-read.md`](../research/live-read.md). Optional local Cursor copies: [`research/agent-local-setup.md`](../research/agent-local-setup.md).
