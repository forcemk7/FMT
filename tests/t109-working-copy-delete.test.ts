import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const vite = fs.readFileSync(path.join(root, "vite.config.ts"), "utf8");
const savePaths = fs.readFileSync(
  path.join(root, "shared", "save", "save-paths.ts"),
  "utf8",
);

describe("T109 working-copy extract — delete after", () => {
  it("refuses live SI games path; cleanup never deletes live games", () => {
    expect(savePaths).toMatch(/export function assertNotLiveFmGamesSave/);
    expect(savePaths).toMatch(/extract only from a FMT working copy/);
    expect(savePaths).toMatch(/export function cleanupWorkingFm/);
    expect(savePaths).toMatch(/only FMT working copies/);
    expect(savePaths).toMatch(/export function resolveWorkingUploadsDir/);
  });

  it("POST + / Update uses tmp/uploads and deletes working .fm in finally", () => {
    expect(vite).toMatch(/resolveWorkingUploadsDir/);
    expect(vite).toMatch(/T109: \+ \/ Update lands in tmp\/uploads/);
    const postIdx = vite.indexOf('url === "/api/roster/first-team" ||');
    expect(postIdx).toBeGreaterThan(0);
    const postBlock = vite.slice(postIdx, postIdx + 4500);
    expect(postBlock).toMatch(/resolveWorkingUploadsDir\(rootDir\)/);
    expect(postBlock).toMatch(/finally \{/);
    expect(postBlock).toMatch(/cleanupWorkingFm\(savePath\)/);
    expect(postBlock).not.toMatch(/fs\.unlinkSync\(savePath\)/);
  });

  it("GET disk extracts are disabled — working copy + delete only", () => {
    expect(vite).toMatch(/T097: no disk GET extract/);
    expect(vite).toMatch(
      /T109: no disk GET extract from data\/saves — working copy \+ delete only/,
    );
  });
});
