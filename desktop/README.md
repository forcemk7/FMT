# FMT (desktop app)

Next.js + Tauri app for **FMT**. Product entry: repo-root `Start FMT.cmd` → this folder.

Origin: GlassScout fork — see `../NOTICE-GlassScout.md`.

Daily use: `npm run desktop:stable` (or the root launcher). Dev with file watch: `npm run desktop:dev`.

**Ship / reinstall:** use `npm run desktop:ship` (bumps patch `0.1.x` across `package.json`, `tauri.conf.json`, `Cargo.toml`, then `tauri build`). Same version rebuild overwrites one installer and Windows still shows the old build number — bump first. Installer: `src-tauri/target/release/bundle/nsis/FMT_<version>_x64-setup.exe`. App data under `%LOCALAPPDATA%\com.fmt.fm26` is kept.
