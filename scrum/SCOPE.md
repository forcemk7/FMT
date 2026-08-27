# Scope

FMT is a **Football Manager 26** desktop companion: live read of the loaded save (no BepInEx), branded **FMT**.

**Stack:** Next.js + Tauri app in `desktop/` (FMT native path; GlassScout-derived — see `NOTICE-GlassScout.md`). Not an offline `.fm` parser. Not FMSuperScout.

**Career saves:** never extract/mmap live SI `games/*.fm`. Live path attaches read-only to `fm.exe` after the user loads a save.

## Livelihood loops (usage, not features)

**Loop A — Replace the spreadsheet (Step 1, funded now)**  
Load save → FMT connects (squad only) → **Squad** → open player desk → attrs + CA/PA/HA + history → decide development. Owner returns next session because the sheet is obsolete.

**Loop B — Squad at a glance (Step 1 companion)**  
Load → **Dashboard** = collective view of the same squad/profile signals (movement, CA/HA, flags) → click into a player (Loop A). Dashboard is not a second product; it is Squad rolled up.

**Loop C — Club roles (only when a decision loop is proven)**  
Nav stubs stay **Later** until they have load → desk → decision. Empty chrome = GlassScout failure mode.

- **Loans** — live: Squad twin filtered to outgoing `loanedOut` (honesty / tracking).
- **GM** — live: Squad twin that **advises Sell vs Loan** from squad **median CA**. Sell = capped low PA, or past dev age (25+) with CA far below PA (decline). Loan = age ≤24 with CA far below PA — youth below median (loan then sell) or CA still below median. Not a transfer market, not a loan finder.
- **HoYD** — live: Squad twin filtered to **high-PA groom prospects** (`PA ≥ squad median CA`, headroom > 8), sorted PA desc. Not mentoring, not world search.
- **Tactic · TD** — still Later until each has its own proven loop.

**Loop D — Replace FMLE (Step 2, not funded)**  
Full-save index at usable speed. Hard RE. Parked until Loop A is daily habit.

## Need-to-have (do)

- Squad-only live load; correct attrs; history that replaces sheets (Loop A)
- One main header row (merge GS double header) so the shell is usable
- Nav = Dashboard · Squad · Tactic · HoYD · GM · Loan · TD (+ Settings) — **Squad + Dashboard + Loans + GM + HoYD live**; others muted roadmap
- Dashboard = collective squad/profile signals (feeds Loop B), reusable “dashboard blocks” only when a second live tab needs them — no platform rewrite
- Player profile desk + history teaching (CA/HA / movement) on Squad path
- Installer daily driver; no empty console

## Optional

- Theme polish after header + nav + desk usable
- Player cutout faces: Settings path + local cache (never hot-path stream live SI `graphics/` after copy)
- Mentoring as a real desk only after Loop A sticks
- Club-relative GM thresholds: median CA in T194; Settings knobs still optional after that sticks

## Not need-to-have (discard)

- Six layers of headers / GS recruitment chrome
- Building Tactic/HoYD/TD (or GM beyond filtered Squad) as fake working products
- GM sell/loan recommenders, listing workflows, world search
- Blind world-table RE / beat FMLE this week
- Offline `.fm` extract / BepInEx
- “Dashboard component framework” as a standalone project

## Gate

1. Does this strengthen Loop A or B this week? (GM only after the move-on loop is proven — it is.)
2. If we never ship Loop C/D, does Loop A still beat sheets?
3. Smallest UI change that removes friction from Loop A?
