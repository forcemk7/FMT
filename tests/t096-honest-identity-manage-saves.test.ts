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
  it("POST + / upload extracts identity only — no FT/II/U19 HA walk", () => {
    expect(vite).toMatch(/extractManagedIdentity/);
    expect(vite).toMatch(/runIdentityStreaming/);
    expect(vite).toMatch(
      /T096: \+ \/ upload extracts clubId, clubName, gameDate only/,
    );
    expect(identityTs).toMatch(/extract-managed-team\.py/);
    expect(identityTs).toMatch(/result\.players = \[\]/);
    expect(identityTs).toMatch(/result\.metaOnly = true/);
    const postIdx = vite.indexOf('url === "/api/roster/first-team" ||');
    expect(postIdx).toBeGreaterThan(0);
    const postBlock = vite.slice(postIdx, postIdx + 900);
    expect(postBlock).toMatch(/runIdentityStreaming/);
    expect(postBlock).not.toMatch(/runExtractStreaming/);
  });

  it("GET disk extract still uses the full first-team path", () => {
    expect(vite).toMatch(/runExtractExclusive\(\(\) =>\s*runExtractStreaming/);
    expect(vite).toMatch(/extractFirstTeam/);
  });

  it("Manage saves In-game is extract gameDate or —", () => {
    expect(main).toMatch(/formatInGameDateRow\(entry\.gameDate\)/);
    expect(main).toMatch(
      /function formatInGameDateRow\(isoDate: string \| null \| undefined\): string \{[\s\S]*?if \(!isoDate\) return "—";/,
    );
    expect(main).toMatch(/gameDate: body\.gameDate \?\? null/);
  });
});
