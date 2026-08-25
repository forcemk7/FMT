# Scope

FMT is a **Football Manager 26** desktop companion: live read of the loaded save (no BepInEx), branded **FMT**.

**Stack:** Next.js + Tauri app in `desktop/` (FMT native path; GlassScout-derived — see `NOTICE-GlassScout.md`). Not an offline `.fm` parser. Not FMSuperScout.

**Career saves:** never extract/mmap live SI `games/*.fm`. Live path attaches read-only to `fm.exe` after the user loads a save.

## Livelihood loop (target)

```
Load save in FM → FMT Load Active Save (managed squad only, fast)
  → club attributes desk (CA/PA/HA) + attribute history that replaces sheets
  → then (later) limited outward/world — only after squad desk is useful daily
```

## Need-to-have (do)

- **Step 1 — Club desk:** squad-only load (no world spray); correct attrs; history that works for daily use
- No empty console on installed Windows launch
- Stable installer as the daily driver (not `desktop:dev`)
- Strip GS superficial chrome only when it blocks the desk (not a skin rewrite)

## Optional (fund only if usage demands)

- Mentor / loan / youth desks
- Quiet launch polish beyond console
- World / continue full index (explicit later step — not funded now)

## Not need-to-have (discard)

- Blind player-table RE / “beat FMLE at 2s” as current bet
- Offline `.fm` RE / cloud upload extract
- BepInEx
- World scout clone / tactics invention as product surface
- Greenfield “new squad desk” rewrite

## Gate

1. Will the owner open this every session beside FM for the **club** desk?
2. Smallest change that unlocks that habit?
3. If we never ship world, does squad + history still beat sheets?
