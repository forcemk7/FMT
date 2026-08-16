---
id: T102
title: Structured hover tooltip on save cards
status: done
priority: 1
owner: composer
claimed_at: 2026-08-16T13:38:00+02:00
started_at: 2026-08-16T13:39:00+02:00
completed_at: 2026-08-16T13:44:00+02:00
depends_on: [T101]
---

# T102 — Structured hover tooltip on save cards

## Why

Save-card hover is a dump of fields. Owner wants a fixed label list so every identity field is readable without crowding the card.

## Scope

- In: hover tooltip on the save row (native `title` is fine) exactly:

```
{file_name}
Game Version: {FM24|FM26}
Club Name: {club_name}
Club ID: {club_id}
Game Date: {game_date}
Uploaded: {uploaded_date}
```

- In: missing gameDate → `—`. Dates use the same card format (Game Date Mon DD, YYYY; Uploaded Mon DD, HH:MM AM/PM)
- Out: extract Python. Card layout change. App shell. Auto-sync. `*.fm` in git

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`

## Acceptance criteria

- [x] Tooltip text matches that six-line shape (vitest chrome guard on `syncRosterSavesMenu` / `title`)
- [x] One git commit `T102: …` on FMT/

## Notes / pointers

- `web/main.ts` `syncRosterSavesMenu` — current `selectBtn.title` / row title
- Identity marker already on the store from T101 (`tagHex` / FM24 vs FM26)

## Progress

Shipped: save-row hover is six labeled lines (`saveCardHoverTitle`): filename; Game Version FM24/FM26 or —; Club Name; Club ID; Game Date (`formatInGameDateRow`, Mon DD, YYYY or —); Uploaded (`formatUploadedAtRow`, Mon DD, H:MM AM/PM). Native `title` on the row and select button. Card layout / extract / auto-sync unchanged. No committed `.fm`.

Verified: `npx vitest run` t102 + t101 + t100 (8 passed).
