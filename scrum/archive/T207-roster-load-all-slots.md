---
id: T207
title: Roster — load all First Team Players slots (39=39)
status: done
priority: 1
owner: auto
claimed_at: "2026-09-04T06:07:00+02:00"
started_at: "2026-09-04T06:07:00+02:00"
completed_at: "2026-09-04T06:13:00+02:00"
depends_on: [T205]
---

# T207 — Roster — load all First Team Players slots (39=39)

## Why

FM.exe senior First Team roster count is the ground truth (Liverpool = 39, including not-at-club). FMT already reads that Team.Players vector (`rosterLen` 39) but drops slots in resolve/validation (~36 loaded). Loop A needs **loaded count == rosterLen** (honest skips only for true empty pointers). T206 labels wait on this.

## Scope

- In: Live diagnose failing First Team slots (vtable / FSS class / nested PLAO); fix production resolve so every non-empty Players slot yields a player (UID + name) when FM shows them
- In: Metric = `rosterLen` vs loaded (no name fixtures); QA on Liverpool and one other gameDate club when available
- In: Keep Club.Teams → Team.Players path (right list); do not invent a second squad source
- Out: T206 tab labels; full-world People index; affiliate II; matching FMLE UI chrome

## Acceptance criteria

- [x] Liverpool (or current managed first team): non-empty Players slots all load (loaded + empty_pointer == rosterLen; no `person_unresolved` / false non-person on real rows)
- [x] Skip details still list any true failures with vtable/reason
- [x] Unit test or probe field documents the lock (class offset / indirection)
- [x] One commit `T207: …`

## Progress

### Lock

Live Liverpool First Team slot 1: person @ PLAO+0x288 had **name Dominik Szoboszlai** and UID **16202373**, but `is_plausible_fm_unique_id` required `>= 20_000_000`, so identity failed. Same Team.Players list (39) — drop was our UID floor, not a wrong list.

### Shipped

- Widen plausible UID to `1_000_000..=99_999_999` (plus existing ~2.0B newgen band)
- Unit test: `plausible_uid_accepts_sub_20m_db_ids` (Szoboszlai 16202373)
- Live verify: First Team `rosterLen=39` → `ok: 39` (includes Szoboszlai)

### Residual

- U18 still has 3 `person_unresolved` on this save (out of First Team acceptance). Follow-up if youth tabs need the same count honesty.

### Commit

`e096e72` — T207: accept sub-20M FM UIDs so First Team slots load
