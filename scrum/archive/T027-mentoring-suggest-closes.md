---
id: T027
title: Mentoring Suggest commits and closes; one-click from board
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T12:46:00+02:00
started_at: 2026-08-13T12:48:00+02:00
completed_at: 2026-08-13T12:54:00+02:00
depends_on: []
---

# T027 — Suggest commits the group and closes the picker

## Why

**Loop break (behavior):** Building groups is a click tax. Current path: **Add group → Suggest → Close (×)**. Suggest already **applies** the trio (`applyMentoringPickerSelection`) but the **modal stays open**, so the user still hunts a close target. User: "if I click Suggest, just close the modal"; fewer clicks, less dexterity.

## Scope

- In: picker **Suggest** = apply trio (existing) **and close** the picker. Next Add/Suggest starts a new group.
- In: Mentoring board **Suggest** (empty state + when under max groups) adds the next unused suggestion **without opening the picker**. One click → group on the board.
- In: **Add group** still opens the picker for manual pick / cycle-Suggest-in-picker (cycle: reopen picker, Suggest, close).
- Out: card layout redesign (T015–T022); Dynamics extract; T014; extra confirm dialogs; requiring Dynamics labels before close

## Acceptance criteria

- [x] Click **Suggest** in the picker: group is saved and picker **closes**; board shows the new group. No extra Close click.
- [x] Click **Suggest** on the Mentoring page (not inside picker): same — group appears, no modal.
- [x] If no unused suggestion: button disabled / "No ideas" — do not open an empty picker.
- [x] Manual **Add group** picker still works (pick 3 / Clear / Close).
- [x] Suggest still respects T025 gates (rejected keys, zero-influence ban).

## Notes / pointers

- `web/main.ts`: `suggestMentoringPickerSelection`, `applyMentoringPickerSelection`, `closeMentoringPicker`, `mentoringPickerSuggestBtn`
- `web/index.html`: picker header Suggest; Mentoring toolbar (`#mentoring-add` / empty state)
- Do not add a second confirm. Suggest **is** the commit.

## Progress

**Shipped**
- Picker Suggest applies the trio then `closeMentoringPicker()` — no extra Close.
- Board **Suggest** (`#mentoring-suggest-btn`) commits `nextUnusedMentoringSuggestion` via `commitMentoringSuggestion` with picker closed. Empty state + under max groups.
- **Add group** still `openMentoringPicker`. Cycle = reopen picker → Suggest → close.
- Both Suggest buttons: loading `Suggest…`; unused empty → disabled `No ideas` (does not open picker). Same `availableMentoringSuggestions` pool as T025 (rejected keys + finder gates).
- Cards untouched.

**Verified:** `npm test` (125 pass), `npm run typecheck`.

**Residual risk:** Board Suggest trusts the already-gated suggestion cache; click-through on a live save left to the user.
