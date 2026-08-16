import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const vite = fs.readFileSync(path.join(root, "vite.config.ts"), "utf8");
const identityTs = fs.readFileSync(
  path.join(root, "shared", "save", "extract-managed-team.ts"),
  "utf8",
);

describe("T096 honest club id, name, and game date on Manage saves", () => {
  it("identity helper still exists; roster POST list extract is T108", () => {
    expect(vite).toMatch(/extractManagedIdentity/);
    expect(vite).toMatch(/runIdentityStreaming/);
    expect(identityTs).toMatch(/extract-managed-team\.py/);
    expect(identityTs).toMatch(/result\.players = \[\]/);
    expect(identityTs).toMatch(/result\.metaOnly = true/);
    // T108: + fills Squad via names-only list extract (identity fields still in result).
    const postIdx = vite.indexOf('url === "/api/roster/first-team" ||');
    expect(postIdx).toBeGreaterThan(0);
    const postBlock = vite.slice(postIdx, postIdx + 1200);
    expect(postBlock).toMatch(/runExtractStreaming/);
    expect(postBlock).not.toMatch(/runIdentityStreaming/);
  });

  it("GET disk extract is disabled — identity is POST + only", () => {
    expect(vite).toMatch(/T097: no disk GET extract/);
    expect(vite).toMatch(/Extract starts from \+ only/);
  });

  it("Manage saves In-game is extract gameDate or —", () => {
    expect(main).toMatch(/formatInGameDateRow\(entry\.gameDate\)/);
    expect(main).toMatch(
      /function formatInGameDateRow\(isoDate: string \| null \| undefined\): string \{[\s\S]*?if \(!isoDate\) return "—";/,
    );
    expect(main).toMatch(/gameDate: body\.gameDate \?\? null/);
  });
});
