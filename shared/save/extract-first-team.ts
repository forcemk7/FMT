/**
 * First Team roster (+ club identity) from an FM career .fm save.
 *
 * Shells out to `scripts/extract-first-team-fast.py --names-only`
 * (identity + personality attributes; Det/Lea from CA; Amb…Tem from pack;
 * CA attributeHistory change-points for Squad evolution charts).
 */

import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import type { FirstTeamExtract } from "./types.ts";
export type {
  FirstTeamExtract,
  FirstTeamPlayer,
  GeneralAttributes,
  PersonalitySignals,
  PlayerAttributes,
  PlayerDynamics,
  PlayerTraining,
  ReservesSquadExtract,
  U19SquadExtract,
} from "./types.ts";
export {
  JOB_ID_HI,
  JOB_ID_LO,
  UID_HI,
  UID_LO,
  ageFromDateOfBirth,
  hasPersonalitySignals,
  personalitySignalsFromAttributes,
} from "./types.ts";

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

export function resolveDefaultSavePath(rootDir: string): string {
  const dir = path.join(rootDir, "data", "saves");
  if (!fs.existsSync(dir)) {
    throw new Error(`No data/saves directory at ${dir}`);
  }
  const files = fs
    .readdirSync(dir)
    .filter((f) => f.toLowerCase().endsWith(".fm"))
    .map((f) => path.join(dir, f));
  if (files.length === 0) {
    throw new Error(`No .fm save found in ${dir}`);
  }
  files.sort((a, b) => fs.statSync(b).size - fs.statSync(a).size);
  return files[0]!;
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
  let message = `extract-first-team-fast.py failed (exit ${code})`;
  const trimmed = stdout.trim();
  if (trimmed) {
    try {
      const parsed = JSON.parse(trimmed) as {
        error?: string;
        diagnostics?: Record<string, unknown>;
      };
      if (parsed.error) {
        message = parsed.error;
        const d = parsed.diagnostics;
        if (d && typeof d === "object") {
          const bits: string[] = [];
          if (d.inferredLayout) bits.push(`layout=${d.inferredLayout}`);
          if (d.saveBytes != null) bits.push(`bytes=${d.saveBytes}`);
          if (d.method) bits.push(`method=${d.method}`);
          if (d.squadCount != null) bits.push(`squadCount=${d.squadCount}`);
          if (d.squadTidCount != null) bits.push(`squadTids=${d.squadTidCount}`);
          if (d.rankedTids) bits.push(`tids=${JSON.stringify(d.rankedTids)}`);
          if (d.decompressedBytes != null) {
            bits.push(`decomp=${d.decompressedBytes}`);
          }
          if (bits.length) message = `${message} [${bits.join(", ")}]`;
        }
        return new Error(message);
      }
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
  } else {
    message = `${message}: no JSON`;
  }
  return new Error(message);
}

/** Extract managed club identity + First Team Unique IDs / names. */
export async function extractFirstTeam(
  savePath: string,
  opts?: { onProgress?: (p: ExtractProgress) => void },
): Promise<FirstTeamExtract> {
  if (!fs.existsSync(savePath)) {
    throw new Error(`Save not found: ${savePath}`);
  }
  const script = path.join(repoRoot(), "scripts", "extract-first-team-fast.py");
  const raw = await new Promise<string>((resolve, reject) => {
    const child = spawn("python", [script, "--names-only", savePath], {
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
      process.stderr.write(chunk);
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
            `extract-first-team-fast.py returned invalid JSON (exit ${code})`,
          ),
        );
      }
    });
  });

  const result = JSON.parse(raw) as FirstTeamExtract;
  result.savePath = savePath;
  result.saveName = path.basename(savePath);
  if (!Array.isArray(result.players)) result.players = [];
  return result;
}

