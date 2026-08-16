# Status

Last updated: 2026-08-16 (T110 done)

## Now

**Loop:** Squad (HA) → Loans (honesty / youth out) → Progress (CA + HA) → Mentoring (in FM).

**SHIP.** Four tabs: Squad, Loans, Mentoring, Progress. Cloud-capable extract. BMC tip on the header.

**T107 done** — empty panes share one thead chrome + identical `.table-pane-drop` under `.table-pane-head` (Squad no longer forks into `#roster-body`). Mentoring empty hides mentee strip.

**Used (2026-08-16 HQ):** Continue date works on owner save. Final chrome: same thead look + drop well in the identical place on all four tabs.

**Used (2026-08-16 HQ):** Fund Squad list next. Shortest solid FT/II/U19 path after identity; progressive row append only if cheap (else one-shot JSON).

**T108 cancelled** — owner rejected. Worker rewired old `extract-first-team-fast` MVP; counts 94 vs FM 87; loans/names wrong; other saves 0 players. Do not build on that list path.

**Used (2026-08-16 HQ):** Fund hygiene + first-principles lists only. Sequence: working copy then delete → club_id → squads → names (+ uid) + unit. No HA/CA. Loans after lists are convincing.

**Used (2026-08-16 HQ):** T110 prove order = **native FM26 first** (≥2 Careers). Then RE continue from that pattern; rolling continue pack only secondary (date-lock ≠ squad-lock; avoid fitting).

**Next:** T087 frozen. Do not claim T077 / T080 / T081. Board empty of ready need-to-haves until HQ funds II/U19 / continue lists / Loans.

**T110 done** — Native FM26: club identity → namelist (~+520) → FT names (+ sparse uid). ≥2 Careers (Liverpool 25 / Bournemouth 24). II/U19 empty (not in identity neighborhood). Continue = `continue-squad-lists-not-yet`. Not extract-first-team-fast.

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

**T070 done** — Header Buy me a coffee → `https://buymeacoffee.com/mrramirez` (new tab, optional thank-you). Table stays free.

**FREEZE over (extract).** T083–T086 done: managed club → employed FT/II/U19 → HA+CA → at-club vs loaned + census.

**T088 done** — Sync belongs to the selected save. Start on A → select B → A finishes into slot A; Active / Squad stay on B.

**T090 done** — `match_reserve_name_score` is defined (was dead after `lp32_name_ending_at` return). Extract no longer NameErrors on the T084 reserve join.

**T091 done** — `resolve_ft_squad` keeps scanning catalog hits until a 7f02 job-list exists. First PRE_NAME object with no list is skipped. `BODY_HIT_LIMIT` expands. Identity known + miss still `ft-club-squad-join-miss`. Restart `npm run dev` and re-extract a non-Schalke career.

**T092 done** — FT join primary key is identity club UniqueID; UTF-8 parent_short is fallback. Strict `7f02…ffffffff` / +128 / 00×10 expand to loose `7f02` and `010302`. Resolve PROGRESS includes `jobsFound`. Identity known + miss still `ft-club-squad-join-miss`, never `pick_tid`. Restart `npm run dev` and re-extract a non-Schalke career.

**T093 done** — Two recipes in one Python: continue = club-object `7f02`; native = UniqueID glued to `7f02`+`010302`. PROGRESS `layout` is `continue` | `native`. Identity known no longer skips native list discovery and still never `pick_tid` or world-club walk.

**T094 done** — Native UniqueID then nearby `7f02`+`010302` (expanding `LIST_WINDOWS`). Glued UniqueID|`7f02` still hits. Identity known + miss still `ft-club-squad-join-miss`. Restart `npm run dev` and re-extract a native FM26 career.

**Used (2026-08-16 HQ):** T093 glued UniqueID|`7f02` missed real club objects. **T094 done** — nearby list. Native `players[]` still unknown until re-extract.

**T095 done** — + stays usable while A extracts. Chosen B waits; König auto-sync does not jump that queue. Delete on Syncing aborts Python then removes the slot.

**Used (2026-08-16 HQ):** Leicester City 673 Active, Uploaded 09:13, In-game **May 25, 2038** (owner: not 2038), empty Squad. **T096 done** — that year was the 24MB calendar-run; upload In-game is neighborhood date or `—`.

**Used (2026-08-16 HQ):** Club id/name look locked. Game date still `—`. Owner: FM today is **4 Jan 2026** = `u8` doy immediately before `u16` year after UniqueID (`04 04 ea 07` → doy 4, year 2026). Not 4 Apr. **T097 done** — UniqueID-tail doy+year; auto-sync killed.

**Used (2026-08-16 HQ):** T097 date only works on the inspect save. Worker froze UniqueID+1/+2 (`04 04 ea 07`), not “find year, doy is the byte before it”.

**T099 done** — gameDate is UniqueID+4 `u16` doy + UniqueID+6 `u16` year (`raw>366` → `raw & 0x1FF`). Owner: eight Careers match FM.

**Used (2026-08-16 HQ):** Liverpool / Bournemouth / Leicester / Schalke / Bodø/Glimt / Legia / Melbourne Victory / Santos — club + in-game date locked. First upload stays Active; cards need uploaded date + icon edit/delete.

**T100 done** — + / Edit persist sets Active to that save. Cards: club+id | uploaded; game date | edit+delete icons. Date parser unchanged.

**Used (2026-08-16 HQ):** Continue Schalke Game Date `—` (tag `02`); native eight locked. Cards need FM24/FM26 pill, ID, Game Date labels, update-same-name (not overwrite).

**T101 done** — persist tagHex FM26/FM24 pills. Tag 01 date = T099 UniqueID-tail; tag 02 = continue calendar (never T099). Cards: pill+club | Uploaded; ID + Game Date | refresh+delete. Update same filename only. Menu widened. No page shell.

**T102 done** — save-card hover is six labeled lines (filename, Game Version, Club Name, Club ID, Game Date, Uploaded). Missing gameDate → —. Card layout unchanged.

**T103 done** — page shell: header FMT · club · in-game date · + · saves · coffee; tabs Squad | Loans | Mentoring | Progress; one pane. No save → No save. Empty players still show tabs.

**Used (2026-08-16 HQ):** Shell suits. Leftover header Squad pill; empty panes not unified. Owner likes Squad thead; wants that + drop `.fm` on every tab.

**T104 done** — header Squad pill gone. Empty tabs: thead + drop `.fm` (same as +). Filled panes unchanged.

**Used (2026-08-16 HQ):** Empty copy exists on all four tabs, but the table panel and drop well are not the same component (skinny Loans row, Mentoring Add group, different drop boxes). Owner: one pane shell; drop well under thead in the same place.

**T105 done** — one `.table-pane` shell; empty drop well under thead (same slot). Mentoring empty hides Add group / Load a Career Save.

**Used (2026-08-16 HQ):** FM24 Schalke card still `Game Date: —`. Repro `dynamics-c.fm`: tag 02, continue calendar finds prelude-only (2038–39 table), no `today_ptr` → `identity_unsure`. T101 synthetic had a planted ptr; real save does not. Do not take max prelude (T096).

**Used (2026-08-16 HQ):** Owner will not give the date. Hunting via rolling continue stack in `data/saves`: `FM24Career.fm` + `(v02)`…`(v10)` (same club, different days). Lock date blob from diffs, then **delete** those copies.

**T106 done** — continue gameDate from UniqueID trailer; König stack deleted. T087 frozen. Do not claim T077 / T080 / T081.

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
| Buy Me a Coffee | **T070 done** | Tip only |
| One extract Python (no 5×2GB on start) | **T072 done** | **Yes** |
| Extract this club only (not world) | **T076 done** | **Yes** |
| Extract four steps, any Career Save | **T083–T086 done** | **Yes** |
| Favoured-club / scout extract | **T080 blocked** (on T086) | No |
| Loan scan speed | **T081 blocked** (on T086) | later |
| Loans as König counts | **T082 cancelled** (absorbed: T086) | — |
| Personalities label → Squad | **T073 done** | Yes |
| Ranker / checker / compare chrome | **T075 done** | Yes |
| Progress default chip + FM columns | **T078 done** | Yes |
| Extract NameError match_reserve_name_score | **T090 done** | **Yes** |
| Non-Schalke extract empty Squad (first catalog hit) | **T091 done** | **Yes** |
| Non-Schalke extract still 0 players | **T092 done** | **Yes** |
| Native FM26 0 players (continue join only) | **T093 done** | **Yes** |
| Native FM26 still 0 players (UniqueID glued to 7f02) | **T094 done** | **Yes** |
| Cannot add/delete save while König Syncing | **T095 done** | **Yes** |
| Honest club id / name / game date (any save) | **T096 done** | **Yes** |
| Bare Manage saves; lock game date; kill auto-sync | **T097 done** | **Yes** |
| Game date only on inspect-save 4-byte tail | **T098 cancelled** (wrong encoding) | — |
| Game date u16 doy + u16 year after UniqueID | **T099 done** | **Yes** |
| Identity upload locked; last + Active; compact cards | **T100 done** | **Yes** |
| Save cards FM24/FM26; continue date; update-same-name | **T101 done** | **Yes** |
| Structured save-card hover tooltip | **T102 done** | Yes |
| Page shell: header identity + four tabs + one pane | **T103 done** | **Yes** |
| Kill header Squad leftover; unified empty pane + drop | **T104 done** | Yes |
| One table pane shell; same drop well slot | **T105 done** | Yes |
| Continue FM24 gameDate (rolling stack lock) | **T106 done** | **Yes** |
| Standardize pane thead + identical drop well | **T107 done** | Yes |
| Squad list after identity; stream if cheap | **T108 cancelled** (fitted MVP; owner rejected) | — |
| Working-copy extract; delete `.fm` after | **T109 done** | **Yes** |
| First-principles squad lists (native FM26 first) | **T110 done** | **Yes** |
| Progress GK abilities + outfield GK rating | **T087 blocked** (on T094) | after native roster |
| npm run dev from HQ | **T089 cancelled** | — |
| Sync steals Active save when extract finishes | **T088 done** | **Yes** |
| II/U19 Progress CA strip | **T079 done** | **Yes** |

## Board

| ID | Title | Status | Owner |
|----|-------|--------|-------|
| T087 | Progress GK vs outfield CA layout | blocked | |
| T077 | Live www URL — upload save, extract, four tabs | blocked | |
| T080 | Stop favoured-club extract on roster path | blocked | |
| T081 | Faster loan motif search — same loan flags | blocked | |

## Behavior

- ≥ filter without Det/Lea is dishonest for mentoring suitability.
- Units in FMT = planning reminder for FM. Mentoring pool = at-club only. Loaned names on Loans. Same person must not be on both.
- **Used (2026-08-14):** Clear filters → click Adrian Itu → loosen-all → Yoan Robert + Miraglia. FT-only hid this. Empty FT list was correct.
- **Used (2026-08-16 HQ):** Start sync on save A → select save B in Manage saves → extract finishes → view jumped back to A. **T088 done** — persist stays on A’s slot; Active / Squad stay on B.
- **Used (2026-08-16 HQ):** Club id/name on Manage saves, 0 players. Schalke = FM24 continue; others = native FM26. Identity works; continue 7f02 join does not. Native list parse is skipped because identity is known. **T093 done** — native UniqueID glued to `010302`. **Used after T093:** still 0 players on native. Glued UniqueID|`7f02` misses real club objects. **T094 done** — UniqueID then nearby `7f02`. Re-extract a native career.
- **Used (2026-08-16 HQ):** Eight Careers: club + gameDate match FM (T099). First + stayed Active (T088 keepActive). **T100 done** — last + / Edit is Active; compact icon cards.
- **Used (2026-08-16 HQ):** Extract `NameError: name 'match_reserve_name_score' is not defined`. **T090 done** — scorer lives next to `match_unit_core_score`; dead block after `lp32_name_ending_at` removed. Restart `npm run dev` and re-extract.
- After groups exist in FM: extract on a new in-game date → Progress HA delta (pack + Det/Lea). Two different gameDates required; one extract → value, empty delta.
- Extract is two blobs once (pack + CA card). UI: Squad HA = pack + Det/Lea from the card. Progress CA = card history; Progress HA = pack snapshots + Det/Lea from the card (T066). Do not hunt Det/Lea as a third extract.
- Progress plot: HA pack has no in-save strip (extract snapshots). Det/Lea use the attributes-card CA strip (T066). Pack chips stay on `fmt.ha-history.v1`.
- Career `.fm`: copy selected live save into `data/saves`, then extract. Never extract the live file.
- **T065:** selected live `.fm` copies into `data/saves` even when dest was missing; `(v02)` and other careers stay out. 97/99 after a live save is a new extract.
- **T068:** poll copies live→dest when dest is stale. U19 uses the before-name list (window 400). Quota compact trims CA strips (24/8); II/U19 keep history unless last-resort overflow. König dest blob today is still **2040-01-13**. Restart `npm run dev`; wait for extract.
- Faces: copy roster portraits into `data/faces`, then serve the copies.
- Logos: copy crests into `data/logos`, then serve the copies. SI graphics only for a missing file.

## Gate

- Board: no ready need-to-haves. T110 done — native FT namelist locked; II/U19 + continue lists still open for HQ. T087 frozen. T077 / T080 / T081 blocked. One ticket per worker.
- Refuse Suggest. Refuse CA/PA. Refuse Stripe paywall / packaging / FM27.
- BMC is a tip. Do not gate the table.
- Workers: one ticket, one commit on `FMT/`. If freeze, do not claim anything else.

## Blockers

- Host RAM / T077 after owner says the local loop is honest (any save + Active not stolen).

## Recently done

- **T110** — Native FM26 squad lists from identity neighborhood namelist (count → lp32 names → canonical FT). Liverpool + Bournemouth smoke; II/U19 honest empty; continue `continue-squad-lists-not-yet`. Product uses `extract-squad-lists.py` (not T108 fast). Unittest + vitest. Restart `npm run dev` and + a native Career. No committed `.fm`.

- **T109** — + / Update extract lands in `tmp/uploads` working copy; `cleanupWorkingFm` deletes it after success or abort (never live SI `games/*.fm`). GET scout disk extract disabled. Vitest refuse + delete-after. Restart `npm run dev`. No committed `.fm`.

- **T108 cancelled** — Owner rejected: rewired MVP list extract; 94 ≠ 87; FT/Res/U19 vs loans wrong; other Careers 0 players. Identity shell stays. Next T109–T110.

- **T107** — Empty Squad / Loans / Mentoring / Progress share `.table-pane-empty` → `.table-pane-head` + `.table-pane-drop`. Shared thead typography tokens (also filled Squad HA head). Mentoring empty hides mentee strip. Drop still + identity upload. Vitest chrome. Restart `npm run dev`. No committed `.fm`.

- **T106** — Continue tag `02` gameDate from UniqueID trailer (lp32 → u32 0 → u32 0xffffffff → u16 doy + u16 year; same T099 mask). Not UniqueID+4, not c708/today_ptr. Locked via König FM24Career v02–v10 diffs; those copies deleted. Native tag `01` still T099. Unittest t106+t101+t099+t097+t096. Restart `npm run dev` and + a continue save. No committed `.fm`.

- **T105** — Squad / Loans / Mentoring / Progress share `.table-pane`. Empty: T104 thead on top, `.table-pane-drop` under it (not a table row). Mentoring empty hides Add group and “Load a Career Save”. Drop still + identity upload. Filled Loans cards / Mentoring groups / Progress chart stay in the same panel. Vitest chrome. Restart `npm run dev`. No committed `.fm`.

- **T104** — Header has no leftover Squad pill (`#tool-nav` gone). Empty Squad / Loans / Mentoring / Progress show that tab’s thead + `Drop a Career Save (.fm) here, or use +`. Drop on an empty pane is the + identity upload (new save, not overwrite). Filled Loans cards / Mentoring groups / Progress chart stay. Vitest chrome guard. Restart `npm run dev`. No committed `.fm`.

- **T103** — Page shell: header FMT · Active club · in-game date (Mon DD, YYYY or —) · + · saves · BMC. No save → No save. Tabs Squad | Loans | Mentoring | Progress under the header; Reserves / U19 stay hidden. Empty pane prompts +. Active save with empty `players[]` still shows tabs. Hash restore (`#roster/mentoring`) does not require a non-empty roster. Save cards / extract unchanged. Vitest chrome guard. Restart `npm run dev`. No committed `.fm`.

- **T102** — Save-card hover is six labeled lines: filename; Game Version FM24/FM26 (or —); Club Name; Club ID; Game Date (Mon DD, YYYY or —); Uploaded (Mon DD, H:MM AM/PM). Native `title` on the row. Card layout unchanged. Vitest chrome guard. Restart `npm run dev`. No committed `.fm`.

- **T101** — Persist `tagHex`: `00950e01` → FM26 pill, `00950e02` → FM24 pill. Tag 01 gameDate stays UniqueID+4/+6 (T099). Tag 02 uses continue calendar (`c708` / today_ptr), never T099; unsure → —. Cards: pill+club name | Uploaded: Mon DD, H:MM AM/PM; ID + Game Date | refresh update + delete. Update refuses a different `.fm` name (use +). Menu widened. Auto-sync stays dead. No page shell. Restart `npm run dev`. Owner: continue Schalke should show FM24 + a Game Date or honest `—`. No committed `.fm`.

- **T100** — + / Edit identity persist sets Active to that save (first upload no longer stuck). Cards: club name+id | uploaded date; game date | edit+delete icons. No DELETE text. Auto-sync stays dead. Date parser unchanged. Vitest Active + chrome. Restart `npm run dev` and + a second Career Save. No committed `.fm`.

- **T099** — UniqueID-tail gameDate is u16 LE doy at +4 and u16 LE year at +6 (`doy = raw` if 1..366 else `raw & 0x1FF`; `date(year,1,1)+(doy-1)`). `0x0404` → 4 Jan not 4 Apr; 363 → 29 Dec not 1 Jan / 17 Apr. Invalid → —. Identity club parse unchanged. Unit tests only. Restart `npm run dev` and + four Career Saves. Owner: say if In-game matches FM. No committed `.fm`.

- **T097** — Bare Manage saves: + / rows (club id, name, in-game date) / Delete / Active. No poll, SSE, startup disk refresh, or Update-from-games. gameDate is UniqueID-tail doy+year (`04 04 ea 07` → 4 Jan, not 4 Apr). Invalid → —. Dump `tmp/identity/convert_to_human_readable_report.txt` (gitignored). Restart `npm run dev` and + a Career Save. Owner: say if In-game matches FM. Schalke on disk must not extract. No committed `.fm`.

- **T096** — + / upload extracts clubId, clubName, gameDate only (no FT/II/U19/HA/loans). In-game is identity-neighborhood today_ptr or `—`, never the 24MB calendar-run year. Dump `tmp/identity/convert_to_human_readable_report.txt` (gitignored). Synthetic T083 + later-table-not-today. Restart `npm run dev` and + a Career Save. Owner: say if the three fields match FM. No committed `.fm`.

- **T095** — + stays usable while A extracts (picker not disabled). Chosen B waits for the current Python; König auto-sync does not start first if a + upload is queued or the picker is open. Delete on the Syncing row aborts fetch + leftover-pid kill, then removes the slot. Vitest chrome guards. Restart `npm run dev`. No committed `.fm`.

- **T094** — Native UniqueID then nearby `7f02`+`010302` (continue `LIST_WINDOWS` expand; glued T093 still hits). Continue club-object `7f02…ffffffff` unchanged. Identity known + miss still `ft-club-squad-join-miss`, never `pick_tid`. Synthetic padded + glued + continue + miss tests. Restart `npm run dev` and re-extract a native FM26 career. If `jobsFound > 0` and UI empty, stop (names / T042). No committed `.fm`.

- **T093** — Native FM26 this-club FT list: layout `continue` | `native` on PROGRESS (`00950e02` / zstd@26 vs `00950e01`). Continue club-object `7f02…ffffffff` unchanged. Native UniqueID | `7f02`+`010302` via `parse_squad_candidates`; 11–55 count is not law. Identity known does not skip native discovery, does not walk every club, miss still `ft-club-squad-join-miss`. Synthetic native + continue + miss tests. Restart `npm run dev` and re-extract a native FM26 career. No committed `.fm`.

- **T092** — FT list from identity club UniqueID (short-name catalog is fallback). Strict `7f02…ffffffff` / +128 / 00×10 expand to `LIST_SENTINEL_LOOSE` + `TAG_010302`. Resolve PROGRESS includes `jobsFound`. Identity known + miss still `ft-club-squad-join-miss`, never `pick_tid`. Synthetic UniqueID + loose-sentinel tests. Restart `npm run dev` and re-extract a non-Schalke career. No committed `.fm`.

- **T091** — FT join keeps scanning catalog PRE_NAME hits until a 7f02 job-list exists. `BODY_HIT_LIMIT` expands. II skips first-hit `list: None`. Identity known + miss still `ft-club-squad-join-miss`, never `pick_tid`. Synthetic two-object test. Restart `npm run dev` and re-extract a non-Schalke career. No committed `.fm`.

- **T090** — Extract NameError: `match_reserve_name_score` defined from `_reserve_suffix` + `match_unit_core_score`. Unreachable block after `lp32_name_ending_at` removed. Join recipe unchanged. Unittest II/B/U21 + T084. Restart `npm run dev` and re-extract. No committed `.fm`.

- **T089 cancelled** — do not run FMT from HQ. `npm run dev` is `cd FMT`.

- **T088** — Sync belongs to the selected save. `upsertRoster` no longer steals Active. Disk extract starts only for Active (one at a time); in-flight extract finishes into that slot. Selecting another save keeps Squad on that save. Syncing + progress live on that row in Manage saves. Queued auto-sync re-checks Active. Vitest ingest + T088 chrome guards.

- **T086** — At-club vs loaned-out is the loan object on FT/II/U19 jobs (same recipe). Foreign-U19 namelist is not the youth-loan path. Packed `64ff24` stride is not a loan. One census PROGRESS line after the split. Squad / Mentoring = at-club; Loans = outgoing; Progress picker includes both. Synthetic tests. Optional local smoke census to the human; no committed `.fm`.

- **T085** — HA/CA for listed people: UniqueID / NEWGEN bands are heuristics. Employment tag + person double keep out-of-band UniqueIDs; pack + CA card once each; miss is `—`, not a dropped row. Synthetic blob tests. Optional local smoke counts to the human; no committed `.fm`.

- **T084** — FT/II/U19 lists join from this club’s team object (catalog PRE_NAME → teamId/dup → job-list). Dropped MB windows, FT 15–45, `{short} II`/`{short} U19` as the only names, and subunit jobId 50k–2M as law. Identity known + miss never takes `pick_tid`. Missing II/U19 unit = empty subunit. Youth live list is before-name (after-name decoy). Synthetic blob tests. Optional local smoke counts to the human; no committed `.fm`.

- **T083** — Managed-club identity is tag → person lp32 → club short lp32 → UniqueID. Same parser on the roster extract. Search bounds expand if the tag sits later; miss is tag/offset/bytes scanned, not a guessed club. Synthetic blob test. No committed `.fm`.

- **T082 cancelled** — loan counts ticket absorbed: T086 is the generic loan object.

- **T079** — II/U19 Progress keeps the in-save CA strip (not one tip). Pack HA still uses extract snapshots. Quota may trim to 24/8; tip-only II/U19 only if that still overflows. Restart `npm run dev` and re-extract.
- **T078** — Progress starts with no attribute selected (empty chart until a click). Chip grid matches FM: outfield Technical+Set Pieces | Mental | Physical; GK Goalkeeping | Mental | Physical+Technical. Pack Personality sits below as extra. `-` still restores HA chips. No GK/outfield 1–10 ratings.
- **T070** — Header Buy me a coffee opens `https://buymeacoffee.com/mrramirez` in a new tab. Copy: optional thank-you. HA table, filters, mentoring capture stay free. No Stripe.
- **T075** — Navigator is Squad | Loans | Mentoring | Progress. Ranker / Best Personalities / checker hashes land on Squad. Loans + HAS table unchanged.
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
