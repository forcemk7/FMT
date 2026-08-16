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
const py = fs.readFileSync(
  path.join(root, "scripts", "extract-managed-team.py"),
  "utf8",
);

describe("T097 bare Manage saves — no auto-sync, lock game date", () => {
  it("does not start poll, SSE, startup disk refresh, or Update-from-games", () => {
    expect(main).toMatch(
      /T097: no poll, no SSE, no startup disk refresh, no Update-from-games/,
    );
    expect(main).not.toMatch(/new EventSource/);
    expect(main).not.toMatch(/savePollTimer = setInterval/);
    expect(main).not.toMatch(/Startup disk check/);
    expect(main).not.toMatch(/dataset\.action = "update"/);
    expect(vite).toMatch(/T097: no SSE save-changed/);
    expect(vite).toMatch(/T097: no Update-from-games/);
    expect(vite).toMatch(/T097: no disk GET extract/);
    expect(vite).not.toMatch(
      /await runExtractExclusive\(\(\) =>\s*runExtractStreaming\(res, savePath/,
    );
  });

  it("Manage saves chrome is +, club id/name/in-game, Delete, Active", () => {
    expect(main).toMatch(/formatClubLine\(club, id\)/);
    expect(main).toMatch(/formatInGameDateRow\(entry\.gameDate\)/);
    expect(main).toMatch(/roster-saves-item-badge">Active/);
    expect(main).toMatch(/deleteBtn\.textContent = "Delete"/);
    expect(main).not.toMatch(/updateBtn\.textContent = "Update"/);
    expect(main).not.toMatch(/disk-linked/);
    expect(main).not.toMatch(/roster-saves-item-badge is-syncing/);
  });

  it("+ still extracts identity only", () => {
    expect(vite).toMatch(/extractManagedIdentity/);
    expect(vite).toMatch(/runIdentityStreaming/);
    expect(identityTs).toMatch(/extract-managed-team\.py/);
    expect(identityTs).toMatch(/result\.players = \[\]/);
    expect(identityTs).toMatch(/result\.metaOnly = true/);
    const postIdx = vite.indexOf('url === "/api/roster/first-team" ||');
    expect(postIdx).toBeGreaterThan(0);
    const postBlock = vite.slice(postIdx, postIdx + 900);
    expect(postBlock).toMatch(/runIdentityStreaming/);
    expect(postBlock).not.toMatch(/runExtractStreaming/);
  });

  it("gameDate is UniqueID-tail doy+year, not day/month or calendar table", () => {
    expect(py).toMatch(/uniqueid_tail_doy_year/);
    expect(py).toMatch(/doy_year_to_iso/);
    expect(py).toMatch(/date\(y, 1, 1\) \+ timedelta\(days=n - 1\)/);
    expect(py).not.toMatch(/2026-01-04/);
    expect(py).not.toMatch(/identity_today_ptr/);
  });
});
