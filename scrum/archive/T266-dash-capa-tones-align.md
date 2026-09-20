---
id: T266
title: Dash CA/PA tones + age wording + ability column align
status: done
priority: 2
owner: auto
claimed_at: "2026-09-07T02:09:00+02:00"
started_at: "2026-09-07T02:09:00+02:00"
completed_at: "2026-09-07T02:12:00+02:00"
depends_on: [T265]
---

# T266 — Dash CA/PA tones + age wording + ability column align

## Why

CA/PA still ignore attr tones (flat green/grey). Age is cryptic. Digit width shifts misalign team/CA/PA columns.

## Scope

- In: All dash CA/PA (extras + main, ability + ME) use `abilityToneFromScore` / `attr-tone-*`
- In: Identity meta = `{age} years old · {pos}`
- In: Ability peek columns (logo+type, secondary, main) fixed so 2- vs 3-digit CA/PA still align
- Out: Changing peek count / widget set

## Acceptance

- [x] CA/PA follow core attr tone colors (not flat mint green / slate only)
- [x] Age reads `{n} years old` under name
- [x] Best players / Best talent columns line up across rows
- [x] Commit `T266: …`

## Progress

- `DashAbilityStat` — CA/PA via `abilityToneFromScore` + tone-tinted main chip
- Identity: `{age} years old · {pos}`
- Ability rows: 5-col grid (team / secondary / main fixed) for digit align
- Commit: `9fb17a7`
