/**
 * Resolve FM career .fm files on disk (FM games folder + repo data/saves).
 * Used by the dev server for path-based extract and auto-sync.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const FM_GAME_TITLE = "Football Manager 26";

export function resolveFmGamesDir(): string {
  return path.join(
    os.homedir(),
    "Documents",
    "Sports Interactive",
    FM_GAME_TITLE,
    "games",
  );
}

export function resolveRepoSavesDir(rootDir: string): string {
  return path.join(rootDir, "data", "saves");
}

/** Directories searched for career saves, in priority order. */
export function saveSearchDirs(rootDir: string): string[] {
  return [resolveFmGamesDir(), resolveRepoSavesDir(rootDir)];
}

export function listFmSavePaths(rootDir: string): string[] {
  const files: string[] = [];
  const seen = new Set<string>();
  for (const dir of saveSearchDirs(rootDir)) {
    if (!fs.existsSync(dir)) continue;
    for (const name of fs.readdirSync(dir)) {
      if (!name.toLowerCase().endsWith(".fm")) continue;
      const full = path.join(dir, name);
      const key = path.normalize(full).toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      files.push(full);
    }
  }
  return files;
}

/** Resolve a save by filename (case-insensitive). Returns on-disk casing. */
export function resolveFmSaveByName(
  saveName: string,
  rootDir: string,
): string | null {
  const base = path.basename(saveName);
  if (!base.toLowerCase().endsWith(".fm")) return null;

  const want = base.toLowerCase();
  for (const dir of saveSearchDirs(rootDir)) {
    if (!fs.existsSync(dir)) continue;
    for (const name of fs.readdirSync(dir)) {
      if (name.toLowerCase() === want) return path.join(dir, name);
    }
  }
  return null;
}

export type SaveDiskStat = {
  saveName: string;
  path: string;
  mtimeMs: number;
  size: number;
};

export function statFmSave(
  saveName: string,
  rootDir: string,
): SaveDiskStat | null {
  const filePath = resolveFmSaveByName(saveName, rootDir);
  if (!filePath) return null;
  const st = fs.statSync(filePath);
  return {
    saveName: path.basename(filePath),
    path: filePath,
    mtimeMs: st.mtimeMs,
    size: st.size,
  };
}

/**
 * FM touches the file on Save click, then can keep writing for a long time.
 * Prefer a long delay over a silent corrupt extract.
 */
export const SAVE_SETTLE_POLL_MS = 2000;
/** Size/mtime must stay unchanged this long before we treat the write as finished. */
export const SAVE_SETTLE_STABLE_MS = 15_000;
/** Cap how long we wait for a stable write (auto-sync). */
export const SAVE_SETTLE_MAX_MS = 180_000;
/**
 * Quiet period after the *last* change event before settle-checking.
 * 60s keeps us clear of slow FM saves; each new write resets this timer.
 */
export const SAVE_WATCH_DEBOUNCE_MS = 60_000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Poll until `mtimeMs`+`size` are unchanged for `stableMs`, or until `maxMs`.
 * Returns the last observed stats, or null if the file disappears.
 */
export async function waitForFileStable(
  filePath: string,
  options?: {
    pollMs?: number;
    stableMs?: number;
    maxMs?: number;
  },
): Promise<{ mtimeMs: number; size: number } | null> {
  const pollMs = options?.pollMs ?? SAVE_SETTLE_POLL_MS;
  const stableMs = options?.stableMs ?? SAVE_SETTLE_STABLE_MS;
  const maxMs = options?.maxMs ?? SAVE_SETTLE_MAX_MS;
  const started = Date.now();
  let last: { mtimeMs: number; size: number } | null = null;
  let stableSince = 0;

  while (Date.now() - started < maxMs) {
    try {
      if (!fs.existsSync(filePath)) return null;
      const st = fs.statSync(filePath);
      const cur = { mtimeMs: st.mtimeMs, size: st.size };
      if (
        last &&
        cur.mtimeMs === last.mtimeMs &&
        cur.size === last.size
      ) {
        if (Date.now() - stableSince >= stableMs) return cur;
      } else {
        last = cur;
        stableSince = Date.now();
      }
    } catch {
      // mid-write / locked — keep waiting
      last = null;
      stableSince = 0;
    }
    await sleep(pollMs);
  }
  return last;
}
