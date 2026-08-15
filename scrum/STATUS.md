# Status

Last updated: 2026-08-15 (HQ: Squad + Loans + Mentoring + Progress)

## Now

**Loop:** Squad (HA) → Loans (honesty / youth out) → Progress (CA + HA) → Mentoring (in FM).

**SHIP.** Four tabs: Squad, Loans, Mentoring, Progress. Cloud-capable extract. BMC tip.

**T038 done** — II Lars Gabrielsen Det/Lea is the same T014 tip class (not a new locus). Remaining hist=0 stay `—`.

**T039 done** — Age column + one-click find mentor (<24) / find mentee (≥24). Heuristic floors, editable after click.

**T040 done** — Itu is at-club II; list-adjacent team-body `64ff24` no longer tags him as a U19 loan.

**T041 done** — Filter dropdown long names + per-row ± + footer loosen/tighten all.

**T042 done** — nameless FT ghost dropped from HA table. Trust bar may still show `1 name missing`.

**T044 done** — HA filters one per line; + Add filter is Squad = FT. One-click preset unchanged.

**T045 done** — per-row ± updates the number; footer −1/+1 is 18→17 / 18→19 on both at least and at most.

**T046 done** — Age filter is the same number dropdown as HAS / attrs (0–50, not a browser spinner).

**T047 done** — Footer ± inverts Controversy only (CON ≤ 18 + footer +1 → 17; DET ≥ 18 → 19). Row ± stays +1/−1. Age still follows the footer number.

**T061 done** — Progress HA deltas compound across extracts (Det/Lea join pack snapshots). Default Progress chips = HA table keys. One extract → value, empty delta.

**SHIP.** Lookup is the product (Itu → Robert + Miraglia → Group 3). Git: one commit per ticket. Money: Buy Me a Coffee, not a paywall.

**Next:** T075 strip other chrome, T070 BMC (needs URL). T074 cancelled (Loans stays).

| Area | State | Need-to-have? |
|------|--------|---------------|
| Det/Lea for Gilson-class (≥ filter) | **T014 done** | **Yes** |
| Other hist=0 signing Det/Lea source | **T038 done** (T014 tip) | **Yes** |
| Age column + one-click age direction | **T039 done** | Yes |
| Itu at-club II missing from HA (false U19 loan) | **T040 done** | **Yes** |
| Filter labels + ± / loosen-all | **T041 done** | Yes |
| Nameless FT ghost on HA table | **T042 done** | **Yes** |
| Compact filter rows (value then −+) | **T043 done** | Yes |
| One filter per line; Add = Squad FT | **T044 done** | Yes |
| Per-row ±; footer ± is number not op | **T045 done** | **Yes** |
| Age filter dropdown (not number input) | **T046 done** | Yes |
| Footer ± inverts CON only | **T047 done** | Yes |
| Per-player HA progress pane | **T048 done** | **Yes** |
| HA Group column (3 checks = unit) | **T049 done** | Yes |
| Progress pills (delta left; all-time/recent) | **T050 done** | Yes |
| Progress delta column + Show/Hide next-action | **T051 done** | Yes |
| HA truncated-cell tooltip | **T052 done** | Yes |
| Mentoring faces missing (initials) | **T053 + T058 + T059 done** (repo copies only) | **Yes** |
| Live SI games/*.fm lock (autosave) | **T055 done** | **Yes** |
| Copy selected SI save → data/saves then extract | **T056 done** | **Yes** |
| Progress chip scan + dropdowns | **T054 done** | Yes |
| Progress visibility select idle `-` | **T057 done** | Yes |
| Footer ± skips Age (one-click floor survives loosen-all) | **T060 done** | **Yes** |
| Progress HA deltas compound across extracts (Det/Lea) | **T061 done** | **Yes** |
| Mentoring HA arrows = attr up/down; ± in own column | **T062 done** | **Yes** |
| Progress HA plot one x after daily syncs (Yoan / Det/Lea) | **T063 done** | **Yes** |
| HA gameDate from blob only (ignore filename date) | **T064 done** | **Yes** |
| Auto-sync idle when data/saves copy is missing | **T065 done** | **Yes** |
| Progress Det/Lea from CA strip (pack stays snapshots) | **T066 + T068 done** | **Yes** |
| Sync idle when caught up; in-game today must move | **T067 + T068 done** (blob today still 2040-01-13 on König) | **Yes** |
| Extract matches this club (date, squads, FT CA strip) | **T068 done** | **Yes** |
| Mentoring pool FT+II+U19 | **T037 done** | Yes |
| HA table → Add mentoring unit | **T036 done** | Yes |
| CA/PA on Squad table | unfunded | Optional |
| Progress CA + HA points | **keep** (loop) | **Yes** |
| Loans tab | **keep** (honesty + youth out) | **Yes** |
| Suggest | cancelled | No — hidden (T071) |
| Buy Me a Coffee | **T070 ready** | Tip only |
| One extract Python (no 5×2GB on start) | **T072 done** | **Yes** |
| Extract this club only (not world) | **T076 done** | **Yes** |
| Personalities label → Squad | **T073 done** | Yes |

## Board

| ID | Title | Status | Owner |
|----|-------|--------|-------|
| T075 | Strip chrome that is not the four tabs | ready | |
| T070 | Buy Me a Coffee tip on the UI | ready | |

## Behavior

- ≥ filter without Det/Lea is dishonest for mentoring suitability.
- Units in FMT = planning reminder for FM.
- **Used (2026-08-14):** Clear filters → click Adrian Itu → loosen-all → Yoan Robert + Miraglia. FT-only hid this. Empty FT list was correct.
- **Used (2026-08-15 HQ):** Loans tab stays — honesty + youth out on loan. Tab name: **Squad**. Progress CA = growth/PA proxy; HA points = influence.
- After groups exist in FM: extract on a new in-game date → Progress HA delta (pack + Det/Lea). Two different gameDates required; one extract → value, empty delta.
- Progress plot: HA pack has no in-save strip (extract snapshots). Det/Lea use the attributes-card CA strip (T066). Pack chips stay on `fmt.ha-history.v1`.
- Career `.fm`: copy selected live save into `data/saves`, then extract. Never extract the live file.
- **T065:** selected live `.fm` copies into `data/saves` even when dest was missing; `(v02)` and other careers stay out. 97/99 after a live save is a new extract.
- **T068:** poll copies live→dest when dest is stale. U19 uses the before-name list (window 400). Quota compact keeps FT CA strips. König dest blob today is still **2040-01-13**. Restart `npm run dev`; wait for extract.
- Faces: copy roster portraits into `data/faces`, then serve the copies.
- Logos: copy crests into `data/logos`, then serve the copies. SI graphics only for a missing file.

## Gate

- Refuse Suggest. Refuse CA/PA. Refuse Stripe paywall / packaging / FM27.
- BMC is a tip. Do not gate the table.
- Workers: one ticket, one commit on `FMT/`.

## Blockers

- T070: live Buy Me a Coffee URL (paste here).

## Recently done

- **T076** — Extract walks this club’s FT/II/U19 only (skip all-club 7f02 + foreign staff-link ranking; stadiums never walked). König `data/saves` copy: 372s → 316s; same 34/30/30 UIDs, U19 before-name, FT CA strip. Live `games/*.fm` still refused. Restart `npm run dev`.
- **T071** — Mentoring board and Add-group picker have no Suggest button. Groups + Add group / HA Group checks unchanged. Suggest engine left in place.
- **T073** — Navigator tab Personalities → Squad. Click/filter/Group unchanged. Ranker chrome left for T075.
- **T069** — Working tree committed as ship baseline `f57e928a57dea364715b5e630cc810dd56c28aae`. Later tickets compound from here. No push.
- **T074 cancelled** — Loans tab stays (honesty + youth out on loan).
- **T072** — One extract Python at a time. Reload/poll no longer stacks 5×2GB decompresses. Vite start kills leftover extract pid. Restart `npm run dev`. Kill stray `python.exe` once if RAM is still high. One extract still ~2GB while it runs.
- **T068** — Poll copies the selected live save into `data/saves` even when dest already exists (dest was 56 min stale). U19 is the before-name Schalke list (Δ≈−189), not the after-name decoy. Quota compact no longer wipes FT Det/CA strips. Restart `npm run dev` and let extract finish. König blob today is still 2040-01-13.
- **T067** — Syncing idles when dest matches last persist. Date walk still stuck König at Jan 13 (T068 residual: blob marker).
- **T065** — Selected Career Save copies into `data/saves` when dest is missing (T056 only copied names already there). `(v02)` / other clubs not copied. Live `games/*.fm` still never extracted. Restart `npm run dev`.
- **T064** — Extract `gameDate` is the in-save today marker only. Filename `In-game date DD.MM.YYYY` is ignored (stale / T056). Re-extract.
- **T063** — T056 fixed-filename extracts no longer lock gameDate to 2039-07-25. Latest today_ptr appends HA x (Koenig decomp → 2040-01-13). Det/Lea: HA ≥2 dates, else FT CA strip. II/U19 stay HA-only. Re-extract the rolling save.
- **T062** — Mentoring HA arrows = the number will move (lower → ▲, higher → ▼, equal/unlabeled empty). Influencer ± = influencer − mentee in a reserved marks column (values 7 and 16 align). CON numeric. Seat face chevrons unchanged.
- **T061** — Progress HA deltas compound across extracts. Det/Lea join pack snapshots by club+gameDate; chips/chart use that series. Default chips = HA table keys. CA/tech strip unchanged.
- **T060** — Footer −1/+1 skips Age (T039 mentor/mentee floor survives loosen-all). Per-row Age ± still ±1. CON invert unchanged.
- **T059** — Faces and logos: copy once into `data/faces` / `data/logos`. Cache hit and status do not open SI graphics. Server start does not index live packs. Restart `npm run dev`.
- **T058** — Roster faces copy into `data/faces/{uid}.*` (SI graphics = source only). `/api/faces` serves the copies. Extract fills missing FT+II+U19 UIDs. Restart `npm run dev`.

- **T057** — Progress visibility select idle is `-` (role-default chips). Show all / Hide all stay explicit. Window default still Recent.
- **T056** — After FM finishes writing the selected Career Save, FMT copies it into `data/saves` then extracts the copy. Live `games/*.fm` is never extracted. Restart `npm run dev`. Untracked careers in `games/` are ignored (name must already exist in `data/saves`).

- **T054** — Progress chips: reserved delta with more gap; HA `good`/`bad` on values; selected = ink border (no accent wash); Show all / Hide all and Recent / All time are `<select>`s.
- **T053** — Mentoring faces: skip config-only duplicate NGRegens pack so UID maps to the PNG pack. Seimen cutout unchanged; Kizza/Itu/Yoan HIT. Restart `npm run dev`.
- **T055** — Career `.fm` only from `data/saves`. Dev server no longer watches SI `games/`. Extract refuses that path. Restart `npm run dev`. SI `graphics/` faces/logos unchanged.

- **T052** — HA Name / Personality / Media: hover tip = full string only when clipped (header metric tip; native `title` is blocked by overflow). `—` has no tooltip. Row click ≥ filter unchanged.
- **T051** — Progress chips: reserved delta column (empty if 0); values align. Visibility pill names next action (Show all / Hide all). Window pill still Recent / All time.
- **T050** — Progress chips: delta left of value (no empty +/− slot); Show all/Hide all and All time/Recent as cycling pills. Chart path unchanged.
- **T049** — HA Group column: third check creates the unit; header is Group (not Add). # still deletes the group. 1–2 checks do not create.
- **T048** — Progress tab on Squad navigator; club-wide named picker; `#roster/progress` deep-link. Existing HA-pack chart path unchanged. No Yoan Robert hunt.
- **T047** — Footer −1/+1 inverts Controversy only (CON 18 → 19 / 17 when DET 18 → 17 / 19). Per-row CON ± stays +1/−1. Age at-most still follows the footer number.
- **T046** — Age HA filter is the same `<select>` as HAS / attrs (0–50). No browser spinner. One-click floors and ± still work.
- **T045** — Per-row filter ± updates the displayed number; footer −1/+1 is a straight number delta (18→17 / 18→19), not loosen/tighten by op.
- **T044** — HA filters one per line (shrink-to-content); + Add filter defaults to Squad = FT. One-click kid/senior preset unchanged.
- **T043** — Compact HA filter chips: shrink-to-content, value then −+, wrap instead of full-bleed rows.
- **T042** — Drop nameless FT ghost from club HA table (empty / `uid:` / `job:`). Named `—` cells stay. Trust bar still counts the extract hole.
- **T041** — Filter dropdown Determination/Squad/Media Handling; per-row ±; footer Clear All + −1/+1 loosen/tighten.
- **T040** — Itu at-club II: drop list-adjacent team-body `64ff24` false loan (3609393 dup). Re-upload save.
- **T039** — HA table Age column + one-click find mentor (<24, Age ≥ +3, HA ≥) / find mentee (≥24, Age ≤ −3, inverted HA).
- **T038** — Other signing Det/Lea is II Lars Gabrielsen via T014 tip (not a new path); 2 hist=0 remain `—`.
- **T014** — Gilson Det/Lea via first Progress Report tip (tech-wiped tip accept).
- **T037** — Mentoring pool FT+II+U19.
- **T036** — HA table → Add mentoring unit.
- **T035 / T034 / T033** — club HA table + filters.
