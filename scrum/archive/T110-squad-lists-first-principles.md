---
id: T110
title: First-principles squad lists — native FM26 first
status: done
priority: 1
owner: auto
claimed_at: "2026-08-16T22:15:00+02:00"
started_at: "2026-08-16T22:16:00+02:00"
completed_at: "2026-08-16T22:53:54+02:00"
depends_on: [T109]
---

# T110 — First-principles squad lists — native FM26 first

## Why

T108 cancelled: old MVP rewired; continue counts wrong; other saves empty. Owner rejects fitted extract.

**club_id → squads → player lists → one Squad table** (name, unit FT/II/U19, uid if keyed that way). No HA/CA. No Loans yet.

## Prove order (non-negotiable)

1. **Native FM26 first** (`tagHex` `00950e01`). Lock the structural pattern on **several** native Careers (owner’s gameDate stack / Liverpool, Bournemouth, etc. — not one club). Same recipe → honest names+unit on more than one save.
2. **Then** continue / FM24 (`00950e02`): RE using what native taught, **or** (secondary) diff a rolling continue pack if it helps isolate list bytes. Rolling packs worked for **gameDate**; they do **not** automatically avoid custom-fitting for squad structure — prefer native-locked motifs over “only moves across König v02–v10.”
3. Do **not** tune continue Schalke to force in-game **87** as law. Owner’s continue smoke notes stay as a later check, not the lock target.

## Owner smoke (continue — later check only)

T108 claimed 94 (35+29+30). In-game **87**. FT display+loans ≈ 31; Res 33 undifferentiated; U19 22 with name quality issues. Use after native is locked — not as the recipe’s first success criterion.

## Scope

- In: From locked identity `clubId` / tag, discover FT / II / U19 lists → people. First principles. **Do not** paste back `extract-first-team-fast` as the product path
- In: Squad UI: one list — name, unit, uid (if available). No HA/CA required (`—` / hide columns OK)
- In: Synthetic structural tests from the **native** lock. `tmp/` dumps OK (gitignored)
- Out: Loans. Pack / CA / HA. Mentoring. Progress. T087. T108 revival. Fitting one continue save before native is locked

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm` (T109)
- Do **not** hard-wire König (or any one Career) names/UIDs/byte windows as law
- Do **not** start HA/CA extract

## Acceptance criteria

- [x] Native FM26: documented recipe club_id → squads → names (+ uid) + unit; works on **≥2** native Careers (or honest structural miss on the second with STATUS note — not silent fake success)
- [x] Continue: either same recipe adapted from native knowledge, or explicit “continue not yet” with diagnostic — no T108-style 94 lie
- [x] No HA/CA required for rows
- [x] One git commit `T110: …` on FMT/

## Notes / pointers

- Identity: `extract-managed-team.py` (T099 native date / T106 continue date). List = **new** step
- Native eight Careers already proved identity (T099) — reuse those files as list smoke, then delete working copies per T109
- After this: Loans, then CA/HA — HQ funds separately

## Progress

- Native FM26 lock: identityAbs + ~515-521 -> u32 count -> lp32 names (full then abbr tail). Canonical FT = full names + uncovered abbr surnames.
- Smoke: Liverpool gameDate1 FT 25; Bournemouth gameDate2 FT 24; also Leicester/Bodo/Glimt namelist geometry. II/U19 not in identity neighborhood (honest empty + unitStatus).
- Continue dynamics-c: identity OK, players [], missReason continue-squad-lists-not-yet (no T108 94 lie).
- Product path: extract-squad-lists.py via extract-first-team.ts (not extract-first-team-fast). Squad HA table shows names/unit; attrs —.
- Tests: unittest T110 synthetic; vitest wiring. No committed .fm.
- Commit SHA: (filled after commit)
