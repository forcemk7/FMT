---
id: T011
title: Blind extract trust bar — incomplete players cannot look “done”
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-12T14:31:00+02:00
started_at: 2026-08-12T14:35:00+02:00
completed_at: 2026-08-12T14:50:00+02:00
depends_on: [T010]
---

# T011 — Blind extract trust bar — incomplete players cannot look “done”

## Why

**Loop break (behavior):** User trust collapsed. Accurate-looking rows feel like they only work when the human spoon-fed screenshots / Overview lists / names for RE. When something novel tests the system (new movement, personality estimate, attrs, names, contract/loan status), it fails repeatedly. Phase 1a tickets closed against **provided GT**; generalization is unproven. Mentoring cannot be tested honestly while partial extracts look complete.

Fact check for workers: product extract does **not** load `data/history.json` or fixtures at runtime — recipes are inlined constants calibrated on this career. Personality **labels** are client combo-matches from extracted attrs, not an FM personality string. The failure mode is **silent incompleteness / wrong confidence**, not “UI pastes the user’s screenshots.”

## Scope

- In: after Career Save ingest, each roster/Mentoring candidate must expose extract completeness (at least: name resolved?, HA/attr signals enough for combo?, loan/employment classification known vs unknown)
- In: Mentoring Suggest must **not** seat players that fail the bar (no name and/or insufficient attr signals); UI must not present `uid:` / empty HAS as a normal confident card without a clear incomplete state
- In: one **blind** smoke path documented: load save → sync → inspect Mentoring/squad/Loans **without** new GT files from the user; record what the extract claims vs what is marked incomplete
- Out: Dynamics; new loan motif RE unless required to mark “unknown loan” honestly; sync-pill cosmetics; expanding HAS catalog; fixing Millwood-class motifs unless they break the bar definition

## Acceptance criteria

- [x] Player cards / Mentoring pool show an explicit incomplete state when name missing or attr signals &lt; Mentoring threshold (not a fake full personality)
- [x] Mentoring Suggest never seats incomplete players
- [x] Post-ingest summary or equivalent: counts complete vs incomplete (name / attrs / loan flag) so “feels fine” cannot hide holes
- [x] Blind smoke notes in Progress: what failed without user-provided GT for that event
- [x] Document in Progress: personality = inferred from attrs (not read as FM text)

## Notes / pointers

- `extract-first-team-fast.py` (binary recipes); `web/main.ts` `matchPersonalityComboFromAttrs` / mentoring filters
- T007 residual no-motif loans → must surface as incomplete/unknown where still untagged and still at-club in UI
- Do not claim “extract works” because fixtures pass — fixtures only lock recipes

## Progress

### Personality is inferred (not FM text)

Extract stores attrs (mental Det/Lea + general pack). The UI **never reads an FM personality string**. Labels on cards / Mentoring come from `matchPersonalityComboFromAttrs` (catalog band match). A confident personality card is an inference, not a save field.

### Shipped

1. `web/extract-trust.ts` — bar: name resolved (not empty / `uid:` / `job:`), ≥3 mentoring attr signals, loan status known vs unclassified. Mentoring-ready = name + attrs.
2. Squad / Loans cards: incomplete chrome when name missing or attrs short — **no fake combo / HAS rank**. Badge shows “Name missing” instead of `uid:…`.
3. Mentoring Suggest pool = `mentoringSuggestPool` (not loanedOut, name + attrs). Incomplete FT rows still list in the picker as disabled **Incomplete**. Suggest refuses any trio that fails the bar.
4. Post-ingest / idle roster status: `N/M mentoring-ready · X name missing · Y attrs short · Z loan unclassified`. Updated flash tooltip includes the same counts; they persist after the flash.

### Blind smoke (no new GT)

Inspected existing Career Save extract dump `tmp/live-0112-extract.json` with the bar only — no Overview / screenshot lists.

| Claim | Count |
|-------|-------|
| Players | 76 |
| Mentoring-ready (name + ≥3 attrs) | 76 |
| Name missing / `uid:` | 0 |
| Attrs short | 0 |
| Loan classified | 1 (`loanedOut`: Sipho Sithole) |
| Loan unclassified | **75** |

What failed without GT: **loan honesty**. Names and attrs look finished; 75/76 rows have no loan flag, so untagged outgoing loans still sit in the at-club / Mentoring pool. That hole is now visible on the status line (`75 loan unclassified`) instead of a silent green squad. Millwood-class motif misses stay unclassified (no new RE). Fresh T010 ingest may classify more outgoing loans; unclassified count is the trust signal.

### Verified

- `npx vitest run tests/extract-trust.test.ts tests/mentoring.test.ts tests/loans-roster.test.ts tests/roster-personality-signals.test.ts tests/roster-store-ingest.test.ts` — 38 passed
