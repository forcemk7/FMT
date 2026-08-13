#!/usr/bin/env node
/** Thin CLI wrapper — prefers `npm run extract:ft` (Python). */
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const script = path.join(root, "scripts", "extract-first-team.py");
const args = process.argv.slice(2);
const child = spawn("python", [script, ...args], {
  cwd: root,
  stdio: "inherit",
  windowsHide: true,
  env: { ...process.env, PYTHONUNBUFFERED: "1" },
});
child.on("exit", (code) => process.exit(code ?? 1));
