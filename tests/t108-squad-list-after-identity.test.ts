import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const vite = fs.readFileSync(path.join(root, "vite.config.ts"), "utf8");
const extractTs = fs.readFileSync(
  path.join(root, "shared", "save", "extract-first-team.ts"),
  "utf8",
);

describe("T108 Squad list after identity — shortest path; stream if cheap", () => {
  it("POST + / roster extract uses names-only list path (not metaOnly)", () => {
    expect(extractTs).toMatch(/extract-first-team-fast\.py/);
    expect(extractTs).toMatch(/--names-only/);
    const postIdx = vite.indexOf('url === "/api/roster/first-team" ||');
    expect(postIdx).toBeGreaterThan(0);
    const postBlock = vite.slice(postIdx, postIdx + 1200);
    expect(postBlock).toMatch(/runExtractStreaming/);
    expect(postBlock).not.toMatch(/runIdentityStreaming/);
    expect(vite).toMatch(/T108: \+ \/ roster POST runs names-only/);
    expect(vite).toMatch(/progressive row append skipped/);
  });
});
