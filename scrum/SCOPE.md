# Scope

FMT is an out-of-game **Football Manager 26** tool: fast, read-only **HA + CA** from a Career Save so you can decide who to mentor (and see youth out on loan), then store units as a **reminder for groups you create in FM**.

Not an editor. Not Genie Scout (no full-world load). Not a live mentoring client.

**Must be able to run in the cloud** (upload `.fm` → extract this club → discard the file). Local `npm run dev` uses the **same** savefile rules.

**Career saves:** never extract/mmap the live SI `games/*.fm` file. Local: copy into `data/saves` then extract. Cloud: upload to a temp working copy, extract, **delete the binary**. Do not persist career saves in the cloud.

**Extract:** this club’s players only — identity, unit, pack HA, Det/Lea, CA, loan flag. **Squad** = at-club FT + II + U19. **Loans** = outgoing. Do not load staff, stadiums, or the rest of the save. Full savefile do/don’t: [ROADMAP.md](./ROADMAP.md) §6.

**Faces / logos:** local copies in `data/faces` / `data/logos` only. Not required for cloud.

## What we ship (2026-08)

| Tab | Job |
|-----|-----|
| **Squad** | At-club HA table (FT + II + U19). Click → filters → capture a unit. Youth + first team in one list. |
| **Loans** | Outgoing loans. Honesty check (short list vs FM) and youth-out-on-loan for development planning. |
| **Mentoring** | Reminder stack for groups you will set in FM. No Suggest. |
| **Progress** | CA points (growth / likely PA) and HA points (influence). |

Tab order: **Squad | Loans | Mentoring | Progress**

Ship artifact: GitHub + **cloud** (upload save, no GS download). Tip: **Buy Me a Coffee**. Ground truth = a click.

## Livelihood loop

```
Squad (HA table) — who can mentor / who needs it
  → Loans — is extract honest; which kids are out
  → Progress (CA + HA) — who is growing
  → Mentoring — store the unit; create it in FM
```

## Need-to-have (do)

- Extract this club: uid, name, unit, pack HA, Det/Lea, CA, loan flag (ROADMAP §6)
- Cloud: upload `.fm` → same extract → delete the binary; no save retention
- **Squad:** at-club FT + II + U19; unit + age; one-click ≥ / age direction; Group checks
- **Loans:** same tags, outgoing only
- **Progress:** CA + HA data points
- **Mentoring:** capture / list / remove; no Suggest; at-club pool
- Blind extract trust; missing = —
- Buy Me a Coffee (optional tip)

## Optional (fund only if usage demands)

- CA / PA as **Squad** table columns

## Not need-to-have (discard)

- Mentoring Suggest / seating AI
- HAS ranker / checker / compare as product chrome
- Dynamics as a gate
- Editor / write-to-save / FMT→in-game sync
- Talent tab, staff/stadium extract, exe, Stripe, FM27
- Keeping uploaded `.fm` files in the cloud

## Competitors

Genie Scout already shows HA + CA/PA after a long full-save load. We exist as a **cloud-capable club HA/CA companion** (upload, no install). If GS is enough, this project is done.

## Gate

1. Which of Squad / Loans / Mentoring / Progress does this fix?
2. What behavior shows it is broken?
3. Smallest change that restores that tab?
4. If we never ship it, can they still pick a group from Squad + Progress and capture it?

If (1)–(3) are weak → **refuse**.
