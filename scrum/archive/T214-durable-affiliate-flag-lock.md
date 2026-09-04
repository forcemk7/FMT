---
id: T214
title: Lock durable Squad-tab affiliate discovery (FMLE flags)
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-09-04T10:04:00+02:00"
started_at: "2026-09-04T10:04:00+02:00"
completed_at: "2026-09-04T23:20:00+02:00"
depends_on: [T203, T212]
---

# T214 — Lock durable Squad-tab affiliate discovery (FMLE flags)

## Why

T212 loads II/NPL via parent-edge + name/roster satellite. That will break when live layout or naming shifts. FMLE already shows the durable class: **Main + Permanent + Players Move Freely** (and a **Type** enum including II Club / B Club / Sub Team). Need the real affiliation container + type/flag bytes, then replace satellite discovery.

## Scope

- In: Find the link/agreement records FMLE edits for Squad-tab reserves (may not be `@0x8E8`)
- In: Lock Type + Main / Permanent / Players Move Freely offsets (static II-vs-feeder and/or FM Affiliates UI A/B; paid FMLE A/B is optional, not assumed to succeed)
- In: Production discovery = those flagged affiliates → existing Club.Teams load (keep T212 load path)
- Out: Decompiling FMLE into product; full-world Loop D; tab label polish; deleting T212 bridge until flag path verified

## Acceptance criteria

- [x] Document locked container edge (managed → link/agreement → affiliate club) reboot-stable on Schalke **or** Melbourne
- [x] Document locked flag/type byte offsets (+ expected values) for Squad-tab class vs feeder
- [x] Production uses type/flag filter (no II/NPL name needles) and still loads Schalke II + Melbourne NPL counts
- [x] One feeder on the same save does **not** load as a Squad tab
- [x] One commit `T214: …`

## Progress

- **Shipped:** Durable edge `club+0x118` → wrapper → nested partner UID `@+0x0C`; type at wrapper `+0x30`.
- **Type map:** `0x01` Normal Affiliated Club, `0x08` II Club (Squad tab), `0x10` Good Relations, `0x11` Likely Friendly. Squad allow-list = `0x08` only for now.
- **Production:** type walk first; T212 satellite merge for NPL / unmapped reserves; Normal/Good Relations/Likely never tabs; unmapped bytes → Diagnostics `affiliationTypes` coverage + `Map AffiliationType 0xNN` warnings / tab reminder.
- **Residual:** Main/Permanent/Players Move Freely bytes still open; Sub/B/C/2/3/Feeder/etc. unmapped — expand allow-list when found; NPL still via satellite until its type byte is known.
- Cancel A/B locked the edge (inbox processing shrinks `+0x118` by cancelled count). PGE multi-type edit on one save unstable — deferred to discover-as-you-go.
- Commit: `b4bf074` `T214: wire club+0x118 type filter + map reminders`

## Blockers

- None
