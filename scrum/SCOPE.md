# Scope

FMT is a **Football Manager 26** desktop companion: live read of the loaded save (no BepInEx), branded **FMT**.

**Stack:** Next.js + Tauri app in `glassscout/` (GlassScout fork). Not an offline `.fm` parser. Not FMSuperScout.

**Career saves:** never extract/mmap live SI `games/*.fm`. Live path attaches read-only to `fm.exe` after the user loads a save.

## Livelihood loop (target)

```
Load save in FM → FMT Load Active Save (full index) → attributes desk (CA/PA/HA + history)
  → installer for daily use → later desks that consume history
```

## Need-to-have (do) — current order

1. **Stable shell** (T125) — stays open until user closes it
2. **Full-save load** (T126) — LE-shaped reach, not squad-only
3. **Attribute history plot** (T127) — append-only; desk toggles + deltas
4. **Attribute tone colors** (T128) — OG good/mid/bad
5. Then **installer** as the lightness test (not `desktop:dev`)

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
