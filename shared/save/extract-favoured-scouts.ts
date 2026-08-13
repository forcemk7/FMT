/**
 * Players who list the managed club as a favoured club (career .fm extract).
 *
 * Shells out to `scripts/extract-favoured-scouts.py`.
 */

import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import type { FavouredClubScoutExtract } from "./types.ts";
export type { FavouredClubScoutExtract, FavouredClubScoutPlayer } from "./types.ts";

export type ExtractProgress = {
  elapsedMs: number;
  phase?: string;
  message?: string;
  pct?: number;
  etaMs?: number | null;
  outBytes?: number;
  [key: string]: unknown;
};

function repoRoot(): string {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
}

function parseProgressLine(line: string): ExtractProgress | null {
  if (!line.startsWith("PROGRESS ")) return null;
  try {
    return JSON.parse(line.slice("PROGRESS ".length)) as ExtractProgress;
  } catch {
    return null;
  }
}

function formatFailure(stdout: string, stderr: string, code: number | null): Error {
  let message = `extract-favoured-scouts.py failed (exit ${code})`;
  const trimmed = stdout.trim();
  if (trimmed) {
    try {
      const parsed = JSON.parse(trimmed) as { error?: string };
      if (parsed.error) return new Error(parsed.error);
    } catch {
      // fall through
    }
  }
  const errLines = stderr
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("PROGRESS "));
  if (errLines.length) {
    message = `${message}: ${errLines.slice(-3).join(" | ")}`;
  }
  return new Error(message);
}

export async function extractFavouredClubScouts(
  savePath: string,
  opts?: { onProgress?: (p: ExtractProgress) => void },
): Promise<FavouredClubScoutExtract> {
  if (!fs.existsSync(savePath)) {
    throw new Error(`Save not found: ${savePath}`);
  }
  const script = path.join(repoRoot(), "scripts", "extract-favoured-scouts.py");
  const raw = await new Promise<string>((resolve, reject) => {
    const child = spawn("python", [script, savePath], {
      cwd: repoRoot(),
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
        PYTHONIOENCODING: "utf-8",
      },
    });
    let stdout = "";
    let stderrBuf = "";
    let stderrAll = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk: string) => {
      stderrBuf += chunk;
      stderrAll += chunk;
      const parts = stderrBuf.split(/\r?\n/);
      stderrBuf = parts.pop() ?? "";
      for (const line of parts) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        const prog = parseProgressLine(trimmed);
        if (prog) opts?.onProgress?.(prog);
      }
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (stderrBuf.trim()) {
        const prog = parseProgressLine(stderrBuf.trim());
        if (prog) opts?.onProgress?.(prog);
      }
      const trimmed = stdout.trim();
      if (!trimmed) {
        reject(formatFailure(stdout, stderrAll, code));
        return;
      }
      try {
        const parsed = JSON.parse(trimmed) as { error?: string };
        if (parsed.error) {
          reject(formatFailure(trimmed, stderrAll, code));
          return;
        }
        resolve(stdout);
      } catch {
        reject(
          new Error(
            `extract-favoured-scouts.py returned invalid JSON (exit ${code})`,
          ),
        );
      }
    });
  });

  const result = JSON.parse(raw) as FavouredClubScoutExtract;
  result.savePath = savePath;
  result.saveName = path.basename(savePath);
  if (!Array.isArray(result.players)) result.players = [];
  return result;
}
