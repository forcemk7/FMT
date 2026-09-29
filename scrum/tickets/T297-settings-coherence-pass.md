---
id: T297
title: Settings coherence pass — section-by-section truth audit
status: ready
priority: 1
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T215, T290, T292, T293]
---

# T297 — Settings coherence pass

## Why

Final FMT 1.28 ticket. Settings grew across T215/T276–T286/T290/T292/T293 and now carries cells that say what FMT does *not* do, and the same fact stated twice in different words. 1.28 is a trust pass; a Settings page that contradicts or repeats itself undercuts that. Goal: every cell states something true about what the app actually does, once.

## Scope

- In: Walk Settings **one section at a time**, top to bottom, with the owner. For each section:
  1. List what's there (every cell/label/copy line, as rendered).
  2. Check each against what the code actually does — say what's true, what's stale/false.
  3. Propose: keep / reword / merge / remove. Owner decides.
  4. Apply only the agreed edits for that section, then move to the next.
- In: Remove "we do NOT do X" style cells; collapse duplicate facts phrased differently; fix copy that no longer matches behavior.
- Out: New preferences, new diagnostics, new sections, layout/theme changes (T139/T293 territory), backend/RE changes. If a cell is false because the *feature* is broken, note it and spin off — don't fix the feature here.
- Out: T290 telemetry disclosure *meaning* — wording can be tightened, but it must still disclose what's sent and that there's no opt-out.

## Acceptance criteria

- [ ] Every Settings section reviewed with the owner, one at a time, with an explicit keep/reword/merge/remove decision per cell (recorded in Progress)
- [ ] No cell describes something FMT doesn't do; no fact appears twice
- [ ] `tsc`/`eslint`/`vitest` clean on touched files; dev-preview render checked
- [ ] One commit `T297: …` on `FMT/`, **then push** (this ticket says to push)

## Notes / pointers

- Investigate-before-coding applies: present each section's findings and proposed edits, wait for go-ahead, then edit.
- Settings screen: `desktop/src/components/settings-screen.tsx`; preferences store `desktop/src/domain/preferences.ts`; Telemetry section from T290.
- Section order today (T215 + T292 follow-up): User Preferences panel, then Graphics → FM26 → Save → Manager → Club → Affiliations → Teams → Players, plus Telemetry (T290).
- Ordering vs the consolidated 1.28 live test pass: owner's call. Doing T297 first means the pass also covers the cleaned Settings copy.

## Progress

_(worker fills)_
