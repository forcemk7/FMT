/**
 * Managed-club identity + in-game date only (T096).
 *
 * Shells out to `scripts/extract-managed-team.py` — no FT/II/U19, HA/CA, or loans.
 */

import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import type { FirstTeamExtract } from "./types.ts";
import { assertNotLiveFmGamesSave } from "./save-paths.ts";
import {
  attachExtractAbort,
  forgetExtractPid,
  rememberExtractPid,
} from "./extract-child.ts";
import type { ExtractProgress } from "./extract-first-team.ts";

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
  let message = `extract-managed-team.py failed (exit ${code})`;
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

/** Club UniqueID, name, and UniqueID-tail gameDate — no squad walk. */
export async function extractManagedIdentity(
  savePath: string,
  opts?: {
    onProgress?: (p: ExtractProgress) => void;
    signal?: AbortSignal;
  },
): Promise<FirstTeamExtract> {
  assertNotLiveFmGamesSave(savePath);
  if (!fs.existsSync(savePath)) {
    throw new Error(`Save not found: ${savePath}`);
  }
  if (opts?.signal?.aborted) {
    throw new Error("Extract aborted");
  }
  const script = path.join(repoRoot(), "scripts", "extract-managed-team.py");
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
    rememberExtractPid(child.pid);
    attachExtractAbort(child, opts?.signal);
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
    child.on("error", (err) => {
      forgetExtractPid(child.pid);
      reject(err);
    });
    child.on("close", (code) => {
      forgetExtractPid(child.pid);
      if (opts?.signal?.aborted) {
        reject(new Error("Extract aborted"));
        return;
      }
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
            `extract-managed-team.py returned invalid JSON (exit ${code})`,
          ),
        );
      }
    });
  });

  const result = JSON.parse(raw) as FirstTeamExtract;
  result.savePath = savePath;
  result.saveName = path.basename(savePath);
  result.players = [];
  result.metaOnly = true;
  if (result.gameDate === undefined) result.gameDate = null;
  return result;
}
