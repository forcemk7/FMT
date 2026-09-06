# Scope

FMT is a **Football Manager 26** desktop companion: live read of the loaded save (no BepInEx), branded **FMT**.

**Stack:** Next.js + Tauri app in `desktop/` (FMT native path; GlassScout-derived — see `NOTICE-GlassScout.md`). Not an offline `.fm` parser. Not FMSuperScout.

**Career saves:** never extract/mmap live SI `games/*.fm`. Live path attaches read-only to `fm.exe` after the user loads a save.

## Livelihood loops (usage, not features)

**Loop A — Replace the spreadsheet (Step 1, funded now)**  
Load save → FMT connects (squad only) → **Squad** → open player desk → attrs + CA/PA/HA + history → decide development. Owner returns next session because the sheet is obsolete.

**Loop A product shape (UI):** managed club → club teams → roster players → attributes. That is what the user must see and trust — **not** a mandate that live bytes are only walked that way. Prefer proven OSS / archive field layouts (see `.cursor/rules/fm-live-read.mdc`) for accuracy and cross-save reliability; invent managed-graph RE only when giants don’t cover the gap. Full-world index **load** remains Loop D.

**Loop B — Squad at a glance (Step 1 companion)**  
Load → **Dashboard** = collective view of the same squad/profile signals (movement, CA/HA, flags) → click into a player (Loop A). Dashboard is not a second product; it is Squad rolled up.

**Loop C — Club roles (only when a decision loop is proven)**  
Nav stubs stay **Later** until they have load → desk → decision. Empty chrome = GlassScout failure mode.

- **Loans** — live: Squad twin filtered to outgoing `loanedOut` (honesty / tracking).
- **GM** — live: Squad twin that **advises Sell vs Loan** vs **senior-team median CA** (manager First Team). Candidates = club-wide at-club employees. Sell = capped low PA, or past dev age (25+) with CA far below PA (decline). Loan = age ≤24 with CA far below PA — youth below median (loan then sell) or CA still below median. Not a transfer market, not a loan finder.
- **HoYD** — live: Squad twin filtered to **high-PA groom prospects** (age ≤24, `PA ≥ senior-team median CA`, headroom > 8), sorted PA desc; candidates club-wide. Not mentoring, not world search.
- **Tactic · TD** — not in nav until a proven loop + recipes exist (no empty stubs).

**Loop D — Shared scouting core / replace FMLE read speed (Step 2, not funded)**  
Full-world live index in ~&lt;2s (FMLE-class **read** core; FMT does not ship live editing). Parked until Loop A is daily habit. Direction: load `game_plugin` object tables first, then attach managed club/teams. Catalog: `research/ecosystem.md` + `research/recipes.md`. Law: `.cursor/rules/fm-live-read.mdc`. FMLE binary = A/B only.

## Need-to-have (do)

- Squad-only live load; correct attrs; history that replaces sheets (Loop A)
- One main header row (merge GS double header) so the shell is usable
- Nav = Dashboard · Squad · Loans · HoYD · GM (+ Settings) — all live; no Tactic/TD stubs
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
- Building Tactic/TD as fake working products; empty Later nav stubs
- GM sell/loan recommenders, listing workflows, world search
- Blind heap/idiom world RE / beat FMLE this week (table-walk path is Loop D, parked)
- Offline `.fm` extract / BepInEx
- “Dashboard component framework” as a standalone project

## Gate

1. Does this strengthen Loop A or B this week? (GM only after the move-on loop is proven — it is.)
2. If we never ship Loop C/D, does Loop A still beat sheets?
3. Smallest UI change that removes friction from Loop A?
