#!/usr/bin/env node
/**
 * Keep desktop ship version in sync across package.json, tauri.conf.json, Cargo.toml,
 * and the startup download URL. Use before desktop:build so NSIS gets a new version
 * (same 0.1.x rebuild otherwise overwrites one installer and looks unchanged in ARP).
 *
 * Usage:
 *   node scripts/bump-desktop-version.mjs           # patch +1
 *   node scripts/bump-desktop-version.mjs 0.1.21    # set exact
 *   node scripts/bump-desktop-version.mjs --dry-run
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dryRun = process.argv.includes("--dry-run");
const explicit = process.argv.slice(2).find((arg) => /^\d+\.\d+\.\d+$/.test(arg));

const packagePath = path.join(root, "package.json");
const tauriPath = path.join(root, "src-tauri", "tauri.conf.json");
const cargoPath = path.join(root, "src-tauri", "Cargo.toml");
const distributionPath = path.join(root, "src", "domain", "distribution.ts");

const pkg = JSON.parse(fs.readFileSync(packagePath, "utf8"));
const current = pkg.version;
if (!/^\d+\.\d+\.\d+$/.test(current)) {
  console.error(`Unexpected package.json version: ${current}`);
  process.exit(1);
}

const next = explicit ?? (() => {
  const [major, minor, patch] = current.split(".").map(Number);
  return `${major}.${minor}.${patch + 1}`;
})();

if (next === current && !explicit) {
  console.error("Version unchanged.");
  process.exit(1);
}

function write(file, contents) {
  if (dryRun) {
    console.log(`[dry-run] would write ${path.relative(root, file)}`);
    return;
  }
  fs.writeFileSync(file, contents);
}

pkg.version = next;
write(packagePath, `${JSON.stringify(pkg, null, 2)}\n`);

const tauri = JSON.parse(fs.readFileSync(tauriPath, "utf8"));
tauri.version = next;
write(tauriPath, `${JSON.stringify(tauri, null, 2)}\n`);

let cargo = fs.readFileSync(cargoPath, "utf8");
cargo = cargo.replace(/^version\s*=\s*"[^"]+"/m, `version = "${next}"`);
write(cargoPath, cargo);

if (fs.existsSync(distributionPath)) {
  let distribution = fs.readFileSync(distributionPath, "utf8");
  distribution = distribution.replace(
    /app-v\d+\.\d+\.\d+/g,
    `app-v${next}`,
  );
  distribution = distribution.replace(
    /FMT(?:\.FM26)?_\d+\.\d+\.\d+_x64-setup\.exe/g,
    `FMT_${next}_x64-setup.exe`,
  );
  write(distributionPath, distribution);
}

console.log(dryRun ? `dry-run: ${current} → ${next}` : `bumped ${current} → ${next}`);
console.log(`Next installer: FMT_${next}_x64-setup.exe`);
