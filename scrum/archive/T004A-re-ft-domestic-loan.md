---
id: T004A
title: "RE: FT domestic loan signal (Vlad → Frankfurt)"
status: done
priority: 1
owner: cursor-worker-t004a
claimed_at: 2026-08-11
started_at: 2026-08-11
completed_at: 2026-08-11
depends_on: []
---

# T004A — RE: FT domestic loan signal (Vlad → Frankfurt)

## Why

Mentoring is FT-only. Sipho (`64 ff 26` → Legia) is tagged; **Moise Vlad-Paul** (UID `2002330407`, job `437615`, → Eintracht Frankfurt) is not. That is the live Suggest bug.

## Scope

- In: find binary recipe that tags Vlad (and any other **FT** GT loans) without false-positing at-club FT (Paco, Bandeira, Kizza, Jones, Seimen)
- Out: editing `extract-first-team-fast.py` / `web/main.ts` (hand recipe to **T004**); Loans tab; II/U19 (T004B); missing extract players (T004C)

## Ground truth

- Vlad: uid `2002330407` job `437615` loan club Frankfurt
- Sipho (control positive): uid `2002282525` job `382267` loan `1456` Legia — already works
- At-club controls: see extract FT without loan on FM list
- Artifacts: `tmp/live-0112-decomp.bin`, `tmp/live-0112-extract.json` (utf-16), `tmp/fm-spike/loan-*.txt`

## Acceptance criteria

- [x] Written detect recipe in Progress (offsets/motif/join rules + false-positive check)
- [x] Demonstrated on decomp bin: Vlad hits; ≥2 at-club FT controls miss; Sipho still hits
- [x] Spike script under `scripts/spike-loan-*.py` or `tmp/` reproducing it
- [x] **No** product code edits

## Claim rule

One agent. Write findings only to this ticket Progress + spike output files.

## Progress

### Verdict

Domestic FT loan (Vlad→Frankfurt) uses the **same loan-object template** as Sipho→Legia, but with motif kind **`0x24`** (not `0x26`) and **no** `job + FFFFFFFF×2` header. Product `detect_loaned_out_jobs` only accepts `64 ff 26` + lookback 8..48 → Sipho-only.

### Detect recipe (hand to T004)

On decompressed save (`tmp/live-0112-decomp.bin`):

1. **Motif-first scan** for `64 ff ??` with `0x20 ≤ kind ≤ 0x30`.
2. **Template** at motif (byte offsets from `64`):
   ```
   64 ff kind | u32 A | 10×0x00 | u32 B | clubId | clubId | u16 0x000A
   ```
   - `clubId` duplicated, `50 ≤ clubId ≤ 100_000`, `clubId ≠ parentClub` (920 on this save)
   - Do **not** require FF-pad before motif
3. **Join**: look back **8..56** bytes from motif start for a squad `jobId` (Vlad needs **49**; Sipho uses **25**; product’s 48 misses Vlad by 1).
4. Emit `jobId → loanClubId`.

Kinds observed:

| Player | jobId | kind | back | loanClubId | Club |
|--------|-------|------|------|------------|------|
| Sipho Sithole | 382267 | `0x26` | 25 | 1456 | Legia |
| Moise Vlad-Paul | 437615 | `0x24` | 49 | 912 | Eintracht Frankfurt |

Club **912** locked as Frankfurt via utf-8 `"Eintracht Frankfurt"` co-occurrence (22 hits); **1456** remains Legia.

### False-positive check (`tmp/live-0112-decomp.bin` + extract)

- Recipe `back_hi=56`: **Vlad ✓**, **Sipho ✓**
- Controls miss: Paco, Bandeira, Kizza, Jones, Seimen, Miraglia — **all miss**
- Product `64 ff 26` only: `{382267: 1456}` (Sipho only)
- Bare `64 ff 24` without template **false-positives** many at-club FT (Kizza/Jones/…) — template + `0x000A` marker is required

### Spikes

- `tmp/_spike_loan_t004a_vlad.py` → `tmp/fm-spike/loan-t004a-vlad-recipe.txt` (FF-pad absence)
- `tmp/_spike_loan_t004a_vlad_v2.py` → `tmp/fm-spike/loan-t004a-vlad-v2.txt` (ranked sites; 912 dup)
- `tmp/_spike_loan_t004a_vlad_v3.py` → `tmp/fm-spike/loan-t004a-vlad-v3.txt` (912=Frankfurt; unique owner)
- `tmp/_spike_loan_t004a_confirm.py` → `tmp/fm-spike/loan-t004a-recipe-confirm.txt` (**repro recipe**)

### Note for T004B (not owned here)

Same template also tags GT II/U19 on this bin: Braescu→916, Manole→2238, Öztürk→2249. Millwood not hit — T004B.

### How tested

Ran confirm spike on `tmp/live-0112-decomp.bin` / `tmp/live-0112-extract.json`. No edits to `scripts/extract-first-team-fast.py` or `web/main.ts`.
