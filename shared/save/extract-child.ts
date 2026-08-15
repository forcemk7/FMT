/**
 * Spawn/kill helpers for extract-first-team / favoured-scouts Python children.
 * Windows does not reliably SIGTERM python.exe — use taskkill /T.
 */

import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function pidFile(): string {
  return path.join(
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", ".."),
    "tmp",
    "fmt-extract.pid",
  );
}

export function killExtractChild(child: ChildProcess): void {
  const pid = child.pid;
  if (pid == null) return;
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(pid), "/t", "/f"], {
      windowsHide: true,
      stdio: "ignore",
    });
    return;
  }
  try {
    child.kill("SIGTERM");
  } catch {
    // already exited
  }
}

export function killStaleExtractPid(): void {
  const file = pidFile();
  try {
    const pid = Number(fs.readFileSync(file, "utf8").trim());
    if (Number.isFinite(pid) && pid > 0) {
      if (process.platform === "win32") {
        spawn("taskkill", ["/pid", String(pid), "/t", "/f"], {
          windowsHide: true,
          stdio: "ignore",
        });
      } else {
        try {
          process.kill(pid, "SIGTERM");
        } catch {
          // gone
        }
      }
    }
  } catch {
    // no pid file
  }
  try {
    fs.unlinkSync(file);
  } catch {
    // ignore
  }
}

export function rememberExtractPid(pid: number | undefined): void {
  if (pid == null) return;
  const file = pidFile();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, String(pid), "utf8");
}

export function forgetExtractPid(pid: number | undefined): void {
  if (pid == null) return;
  const file = pidFile();
  try {
    const cur = Number(fs.readFileSync(file, "utf8").trim());
    if (cur === pid) fs.unlinkSync(file);
  } catch {
    // ignore
  }
}

export function attachExtractAbort(
  child: ChildProcess,
  signal?: AbortSignal,
): void {
  if (!signal) return;
  const onAbort = () => killExtractChild(child);
  if (signal.aborted) {
    onAbort();
    return;
  }
  signal.addEventListener("abort", onAbort, { once: true });
  child.once("close", () => {
    signal.removeEventListener("abort", onAbort);
  });
}
