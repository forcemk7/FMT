# FMT

Football Manager 26 **club companion** (live `fm.exe` reader). Product name: **FMT**.

## Origin

Desktop app forked from [TobiasTest22/GlassScout](https://github.com/TobiasTest22/GlassScout) (see `NOTICE-GlassScout.md`). Legacy offline `.fm` extract and FMSuperScout dump paths were removed from this repo.

## Layout

```
desktop/        # Next.js + Tauri app (FMT native path)
scrum/          # board + SCOPE
Start FMT.cmd   # double-click launcher (calls desktop/Start FMT.cmd)
```

## Run (dev)

1. Close any previous FMT window.  
2. Double-click **`Start FMT.cmd`** at the repo root.  
3. Wait for the **desktop window** titled **FMT** (ignore `localhost:3000` in the browser).  
4. Load a save in FM26 → **Load Active Save**.

Needs: VS Build Tools 2022 + Windows SDK, Rust (`cargo`).

Prefer `npm run desktop:stable` (via the launcher) over raw `desktop:dev` for daily use.

## Build installer later

```bat
cd desktop
call vcvars64.bat
npm run desktop:build
```

## Scrum

[`scrum/SCOPE.md`](./scrum/SCOPE.md) · [`scrum/STATUS.md`](./scrum/STATUS.md)
