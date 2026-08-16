---
id: T108
title: Squad list after identity — shortest path; stream if cheap
status: done
priority: 1
owner: auto
claimed_at: "2026-08-16T20:38:00+02:00"
started_at: "2026-08-16T20:40:00+02:00"
completed_at: "2026-08-16T21:10:34+02:00"
depends_on: [T094, T107]
---

# T108 — Squad list after identity — shortest path; stream if cheap

## Why

Identity + shell are locked (T096–T107). Native (and often continue) Squad stays empty: `players[]` never fills the T107 pane. Owner: take the **shortest / fastest / solid** scan for club FT+II+U19 people. If progressive render’s benefit/drawback ratio is positive, keep scanning after identity is shown and **append rows as players are found**.

## Priority (do in this order)

1. **Solid list path** — after managed club + tag + gameDate are known, find FT / II / U19 job lists → people (names + unit + uid). Prefer reuse of T093/T094 recipes (`continue` club-object `7f02` vs `native` UniqueID nearby `7f02`+`010302`). Stop inventing new joins if an existing one hits.
2. **Fill Squad** — upsert into the Active save; rows appear in the locked Squad table. Missing HA/attrs = `—` (honest). Do not block the list on pack/CA.
3. **Progressive only if cheap** — identity chrome already paints first. If Python can emit player batches on the existing PROGRESS / stdout path **without** a second architecture, append rows live. If streaming needs a rewrite, **ship one final `players[]` JSON** and leave streaming for a follow-up. Drawbacks to weigh: abort on delete/switch save (T088/T095), partial table flicker, empty→row races.

## Scope

- In: Extract path that yields at-club (or employed) people for the managed club into `players[]` / unit buckets the UI already understands
- In: + / Update still shows identity immediately; list work continues (or finishes) without stealing Active (T088)
- In: Synthetic tests for the locked list recipe (continue + native). No `.fm` in git
- Out: Full HA/CA pack hunt as a blocker for first rows. Loans/Mentoring/Progress redesign. Shell/thead changes. T087. Cloud (T077). Auto-sync resurrection

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm`
- Do **not** hard-wire König offsets as law; structural recipes only
- Do **not** take max calendar prelude as a date (identity stays T099 / T106)

## Acceptance criteria

- [x] After + a native FM26 career, Squad shows named players (or a clear miss diagnostic), not a permanent empty drop well with identity in the header
- [x] Continue Schalke (tag 02) still identity-correct; list either fills or fails honestly
- [x] Progressive: either live append works and respects abort/Active, **or** documented skip + one-shot JSON (STATUS note)
- [x] Unit tests for the list recipe; one git commit `T108: …` on FMT/

## Notes / pointers

- Identity: `scripts/extract-managed-team.py` (metaOnly today). Full join leftovers: `extract-first-team-fast.py` / T091–T094 archives
- UI: `upsertRoster` / Squad HA table already renders `—` for missing attrs
- Owner smoke: native save with known club in header → names appear on Squad

## Progress

- Wired POST `/api/roster/first-team` to `runExtractStreaming` (names-only `extract-first-team-fast.py`, T093/T094 joins). Identity-only helper kept but unused on +.
- Progressive row append **skipped** (needs new NDJSON player batches + UI merge/abort). One-shot final `players[]` JSON.
- Vitest T108 + updated T096; unittest T093/T094 OK.
- Smoke: `dynamics-c.fm` continue — club FC Schalke 04, FT 35 / II 29 / U19 30, method `ft-club-squad-join-v1`. Truncated `gameDate5.fm` identity OK + honest `ft-club-squad-join-miss` / 0 players.
