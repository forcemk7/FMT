---
id: T163
title: General Personality + Media Handling labels from HA pack
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T163 — General Personality + Media Handling labels from HA pack

## Why

Loop A desk General column shows Ability/Potential but Personality and Media Handling are always `—`. Live path already maps the HA pack (+ Det/Lea); old FMT band matcher already labels them — surface that on the desk.

## Scope

- In: Infer Personality + Media Handling labels from `personalityAttributes` + Det/Lea via the old catalog combo matcher (priority + tightness + T013 missing-pin rules); show on Attributes General column
- Out: Reading FM label strings from memory; mentoring desk; squad Personality column rename (stays HAS)

## Acceptance criteria

- [x] General column shows inferred Personality and Media Handling when the HA pack is complete enough to match
- [x] Incomplete pack → `—` (no invented midpoints)
- [x] Gilson-class regression: Det 14 / Lea 16 + pack → Light Hearted × Evasive, Reserved; not Born Leader
- [x] Vitest covers combo feasibility edge cases (media cases + T013)

## Notes / pointers

- Catalogs: `data/raw/FM HA Calculator - Personality.csv` / Media Handling Style
- Old code (git): `src/inference/match-combo.ts`, `src/data/personalities.ts`, `web/main.ts` `matchPersonalityComboFromAttrs`
- Live fields: `personalityAttributes`, `attributes.Determination` / `Leadership`; UI: `player-profile-screen.tsx` General column

## Progress

- Ported ha-core catalog + `comboFeasibleForAttrs` into `desktop/src/ha/`
- `matchBestPersonalityCombo` (priority + tightness) + `livePersonalityLabels` for the desk
- General column prefers live string if ever mapped, else inferred labels
- Verified: `npm test -- src/domain/personality-labels.test.ts` — 7/7 pass
- Commit: `724da8f`
