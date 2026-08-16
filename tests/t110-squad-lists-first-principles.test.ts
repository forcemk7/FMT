import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const vite = fs.readFileSync(path.join(root, "vite.config.ts"), "utf8");
const extractTs = fs.readFileSync(
  path.join(root, "shared", "save", "extract-first-team.ts"),
  "utf8",
);

describe("T110 First-principles squad lists — native FM26 first", () => {
  it("POST + / roster extract uses extract-squad-lists (not T108 fast path)", () => {
    expect(extractTs).toMatch(/extract-squad-lists\.py/);
    expect(extractTs).not.toMatch(/scripts[/\\]extract-first-team-fast\.py/);
    expect(extractTs).not.toMatch(/--names-only/);
    expect(extractTs).toMatch(/spawn\("python", \[script, savePath\]/);
    const postIdx = vite.indexOf('url === "/api/roster/first-team" ||');
    expect(postIdx).toBeGreaterThan(0);
    const postBlock = vite.slice(postIdx, postIdx + 1200);
    expect(postBlock).toMatch(/runExtractStreaming/);
    expect(postBlock).not.toMatch(/runIdentityStreaming/);
    expect(vite).toMatch(/T110: \+ \/ roster POST runs first-principles/);
  });
});
