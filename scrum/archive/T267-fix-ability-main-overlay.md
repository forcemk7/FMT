---
id: T267
title: Fix ability main overlay + mover chip case/bold
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T02:14:00+02:00"
started_at: "2026-09-07T02:14:00+02:00"
completed_at: "2026-09-07T02:16:00+02:00"
depends_on: [T266]
---

# T267 — Fix ability main overlay + mover chip case/bold

## Why

Best players/talent main CA/PA sits on the face (5th grid cell wrap). Mover pills mix ALL CAPS / Title Case and look lighter than personality chips.

## Scope

- In: Ability peeks — main is rightmost column again (4-col row + fixed extras grid)
- In: Mover chips — bold + Title Case labels (CA/PA stay uppercase), match personality weight
- Out: Changing ranking / peek count

## Acceptance

- [x] Best players / Best talent main CA/PA is rightmost, not on face
- [x] Attribute-change pills bold; one casing scheme shared with personality peeks
- [x] Commit `T267: …`

## Progress

- Restored face | identity | extras | main (4-col); extras = fixed team + secondary grid
- Mover chips: Title Case labels, font-weight 700 (no uppercase `<small>`)
- Commit: (pending)
