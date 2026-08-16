import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const html = fs.readFileSync(path.join(root, "web", "index.html"), "utf8");
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const css = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");

const header = html.match(/<header class="app-header">[\s\S]*?<\/header>/)?.[0];
const DROP = "Drop a Career Save (.fm) here, or use +";

describe("T104 drop header Squad leftover; unified empty pane", () => {
  it("header has no Squad button leftover", () => {
    expect(header).toBeTruthy();
    expect(header).not.toMatch(/id="tool-nav"/);
    expect(header).not.toMatch(/tool-nav-btn/);
    expect(header).not.toMatch(/>\s*Squad\s*</);
    expect(html).not.toMatch(/id="tool-nav"/);
    expect(css).not.toMatch(/\.tool-nav-btn/);
  });

  it("empty Loans / Mentoring / Progress show that tab's thead", () => {
    const loans = html.match(
      /id="squad-loans-empty-host"[\s\S]*?<\/table>/,
    )?.[0];
    const mentoring = html.match(
      /id="mentoring-empty-host"[\s\S]*?<\/table>/,
    )?.[0];
    const progress = html.match(
      /id="squad-progress-empty"[\s\S]*?<\/table>/,
    )?.[0];
    expect(loans).toBeTruthy();
    expect(mentoring).toBeTruthy();
    expect(progress).toBeTruthy();
    const loanHeads = [...loans!.matchAll(/<th\b[^>]*>\s*([^<]+)\s*</g)].map(
      (m) => m[1].trim(),
    );
    const mentorHeads = [
      ...mentoring!.matchAll(/<th\b[^>]*>\s*([^<]+)\s*</g),
    ].map((m) => m[1].trim());
    const progressHeads = [
      ...progress!.matchAll(/<th\b[^>]*>\s*([^<]+)\s*</g),
    ].map((m) => m[1].trim());
    expect(loanHeads).toEqual(["Name", "Unit", "At"]);
    expect(mentorHeads).toEqual(["Group", "Members"]);
    expect(progressHeads).toEqual(["Name", "CA", "ΔCA", "Det", "ΔDet"]);
  });

  it("all four empty panes share the drop copy; drop feeds + upload", () => {
    expect(main).toMatch(/const PANE_DROP_COPY = "Drop a Career Save \(\.fm\) here, or use \+"/);
    expect(html).toContain(DROP);
    expect(main).toMatch(/rosterEmptyEl\.textContent = PANE_DROP_COPY/);
    expect(html).toMatch(/class="table-pane-drop"/);
    expect(main).toMatch(/function feedRosterUpload\(/);
    expect(main).toMatch(
      /function feedRosterUpload\([\s\S]*?rosterAmendTarget = null/,
    );
    expect(main).toMatch(/rosterUploadEl\.files = dt\.files/);
    expect(main).toMatch(/rosterTablePanelEl\.addEventListener\("dragover"/);
    expect(main).toMatch(/rosterTablePanelEl\.addEventListener\("drop"/);
    expect(main).toMatch(/data-pane-drop/);
    expect(main).toMatch(/function fmFileFromDrop\(/);
  });
});
