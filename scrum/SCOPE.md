# Scope

FMT is a **Football Manager 26** desktop companion: live read of the loaded save (no BepInEx), branded **FMT**.

**Stack:** Next.js + Tauri app in `desktop/` (FMT native path; GlassScout-derived — see `NOTICE-GlassScout.md`). Not an offline `.fm` parser. Not FMSuperScout.

**Career saves:** never extract/mmap live SI `games/*.fm`. Live path attaches read-only to `fm.exe` after the user loads a save.

## Livelihood loop (target)

```
Load save in FM → FMT Load Active Save
  → (T133 owner eval) GlassScout native full RAM index + tactic discovery
  → then decide permanent load shape vs LE-fast / Dossier
  → attributes desk (CA/PA/HA + history) → installer for daily use
```

## Need-to-have (do)

- Stable shell (T125)
- **Owner eval (T133):** restore GS full private-memory index on load so native GS reach/tactics can be judged; permanent load shape TBD after that
- Attribute history plot (T127) + tone colors (T128)
- Then **installer** as the lightness test (not `desktop:dev`) — after load shape is chosen

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
