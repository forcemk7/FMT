# Scope

FMT is a **Football Manager 26** desktop companion: live read of the loaded save (no BepInEx), branded **FMT**.

**Stack:** Next.js + Tauri app in `glassscout/` (GlassScout fork). Not an offline `.fm` parser. Not FMSuperScout.

**Career saves:** never extract/mmap live SI `games/*.fm`. Live path attaches read-only to `fm.exe` after the user loads a save.

## Livelihood loop (target)

```
Load save in FM → FMT Load Active Save (~LE-fast: live club desk, no RAM world scan)
  → world search via FM Dossier index → attributes desk (CA/PA/HA + history)
  → installer for daily use
```

## Need-to-have (do)

- Stable shell (T125)
- Load that stays interactive like Live Editor — **no multi-GB private-memory scan** (T129/T130); world reach via Dossier
- Attribute history plot (T127) + tone colors (T128)
- Then **installer** as the lightness test (not `desktop:dev`)

## Optional (fund only if usage demands)

- Mentor / loan / youth desks
- Folder rename, quiet launch polish
- Squad chrome cleanup / strip GlassScout noise

## Not need-to-have (discard)

- Offline `.fm` RE / cloud upload extract
- BepInEx
- World scout clone / tactics invention
- Premature performance work on `desktop:dev`
- Greenfield “new squad desk” rewrite

## Gate

1. Will the owner open this every session beside FM?
2. Smallest change that unlocks that habit?
3. If we never ship the next feature, does load + desk still work?
