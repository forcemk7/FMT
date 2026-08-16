import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const html = fs.readFileSync(path.join(root, "web", "index.html"), "utf8");
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const css = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");

const header = html.match(/<header class="app-header">[\s\S]*?<\/header>/)?.[0];
const tabsMark = html.indexOf('class="squad-view-tabs page-tabs"');
const navStart = tabsMark >= 0 ? html.lastIndexOf("<nav", tabsMark) : -1;
const navEnd = navStart >= 0 ? html.indexOf("</nav>", tabsMark) : -1;
const pageTabs =
  navStart >= 0 && navEnd > navStart
    ? html.slice(navStart, navEnd + "</nav>".length)
    : "";

describe("T103 page shell — header identity + four tabs + one pane", () => {
  it("header is FMT, club, date, then + / saves / BMC", () => {
    expect(header).toBeTruthy();
    expect(header).toMatch(/class="app-brand"[\s\S]*?>\s*FMT\s*</);
    expect(header).toMatch(/id="app-header-club"/);
    expect(header).toMatch(/>\s*No save\s*</);
    expect(header).toMatch(/id="app-header-date"/);
    expect(header).toMatch(/id="roster-save-controller"/);
    expect(header).toMatch(/id="roster-upload-btn"/);
    expect(header).toMatch(/id="roster-saves-btn"/);
    expect(header).toMatch(/id="roster-saves-menu"/);
    expect(header).toContain('href="https://buymeacoffee.com/mrramirez"');
    expect(header).toMatch(/Buy me a coffee/);
    expect(header).not.toMatch(/Club ID/);
    expect(header).not.toMatch(/FM24|FM26/);
    expect(header).not.toMatch(/id="squad-view-first-team"/);
  });

  it("page tabs sit under the header in Squad | Loans | Mentoring | Progress order", () => {
    expect(pageTabs).toBeTruthy();
    expect(html.indexOf('class="app-header"')).toBeLessThan(
      html.indexOf('class="squad-view-tabs page-tabs"'),
    );
    expect(html.indexOf('class="squad-view-tabs page-tabs"')).toBeLessThan(
      html.indexOf('id="roster"'),
    );
    const tabs = [
      ...pageTabs!.matchAll(
        /id="squad-view-(?:first-team|loans|mentoring|progress)"[\s\S]*?>\s*([^<]+)\s*</g,
      ),
    ].map((m) => m[1].trim());
    expect(tabs).toEqual(["Squad", "Loans", "Mentoring", "Progress"]);
    expect(pageTabs).toMatch(/id="squad-view-reserves"[\s\S]*?\bhidden\b/);
    expect(pageTabs).toMatch(/id="squad-view-under19s"[\s\S]*?\bhidden\b/);
    expect(html).not.toMatch(
      /class="squad-view-toolbar"[\s\S]*?class="squad-view-tabs"/,
    );
  });

  it("does not resurrect Rank / Checker / Compare as nav", () => {
    expect(header).not.toMatch(/data-tool="rank"/);
    expect(pageTabs).not.toMatch(/Checker|Compare|Ranker/);
    expect(pageTabs).not.toMatch(/>\s*First Team\s*</);
  });

  it("Active save club + date drive the header; no save is No save; empty players keep tabs", () => {
    expect(main).toMatch(/function syncAppHeaderIdentity\(/);
    expect(main).toMatch(/function hasActiveSave\(/);
    expect(main).toMatch(/appHeaderClubEl\.textContent = "No save"/);
    expect(main).toMatch(
      /appHeaderDateEl\.textContent = formatInGameDateRow\(rosterMeta\.gameDate\)/,
    );
    expect(main).toMatch(/squadViewTabsEl\.hidden = !hasSave/);
    expect(main).toMatch(/Active save with empty players\[\]/);
    expect(main).toMatch(/restoreView && hasActiveSave\(\)/);
    expect(main).not.toMatch(
      /restoreView && clubPlayerCount\(\) > 0 \? restoreView/,
    );
    expect(css).toMatch(/\.app-header-club/);
    expect(css).toMatch(/\.app-header-date/);
    expect(css).toMatch(/\.page-tabs\.squad-view-tabs/);
  });
});
