import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const html = fs.readFileSync(path.join(root, "web", "index.html"), "utf8");
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const css = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");

const DROP = "Drop a Career Save (.fm) here, or use +";

function paneBlock(id: string): string {
  const start = html.indexOf(`id="${id}"`);
  expect(start).toBeGreaterThan(-1);
  const open = html.lastIndexOf("<", start);
  const tag = html.slice(open + 1).match(/^[a-z]+/i)?.[0];
  expect(tag).toBeTruthy();
  const close = `</${tag}>`;
  let depth = 0;
  let i = open;
  while (i < html.length) {
    const nextOpen = html.indexOf(`<${tag}`, i);
    const nextClose = html.indexOf(close, i);
    if (nextClose < 0) break;
    if (nextOpen >= 0 && nextOpen < nextClose) {
      depth += 1;
      i = nextOpen + tag!.length;
      continue;
    }
    depth -= 1;
    if (depth === 0) return html.slice(open, nextClose + close.length);
    i = nextClose + close.length;
  }
  return html.slice(open);
}

describe("T105 one table pane shell; drop well in the same slot", () => {
  it("four tabs share one table-pane class and the same drop-well slot", () => {
    const squad = paneBlock("squad-personalities-pane");
    const loans = paneBlock("squad-loans-pane");
    const mentoring = paneBlock("squad-mentoring-pane");
    const progress = paneBlock("squad-evolution");
    for (const pane of [squad, loans, mentoring, progress]) {
      expect(pane).toMatch(/\btable-pane\b/);
      expect(pane).toMatch(/class="table-pane-drop"/);
      expect(pane).toContain(DROP);
      expect(pane).not.toMatch(/<td[^>]*class="[^"]*pane-drop-copy/);
      expect(pane).not.toMatch(/<td[^>]*>\s*Drop a Career Save/);
    }
    expect(css).toMatch(/\.table-pane\s*\{/);
    expect(css).toMatch(/\.table-pane-drop\s*\{/);
    expect(css).toMatch(
      /\.table-pane-drop\s*\{[^}]*flex:\s*1 1 auto/,
    );
    expect(css).toMatch(
      /\.table-pane-drop\s*\{[^}]*align-items:\s*center/,
    );
    expect(css).toMatch(
      /\.table-pane-drop\s*\{[^}]*justify-content:\s*center/,
    );
  });

  it("empty Loans / Mentoring / Progress keep T104 thead above the drop well", () => {
    const loans = html.match(
      /id="squad-loans-empty-host"[\s\S]*?class="table-pane-drop"/,
    )?.[0];
    const mentoring = html.match(
      /id="mentoring-empty-host"[\s\S]*?class="table-pane-drop"/,
    )?.[0];
    const progress = html.match(
      /id="squad-progress-empty"[\s\S]*?class="table-pane-drop"/,
    )?.[0];
    expect(loans).toBeTruthy();
    expect(mentoring).toBeTruthy();
    expect(progress).toBeTruthy();
    expect(loans).toMatch(/<thead>[\s\S]*<th[^>]*>\s*Name/);
    expect(loans).toMatch(/<th[^>]*>\s*Unit/);
    expect(loans).toMatch(/<th[^>]*>\s*At/);
    expect(mentoring).toMatch(/<th[^>]*>\s*Group/);
    expect(mentoring).toMatch(/<th[^>]*>\s*Members/);
    expect(progress).toMatch(/<th[^>]*>\s*Name/);
    expect(progress).toMatch(/<th[^>]*>\s*CA/);
    expect(progress).toMatch(/<th[^>]*>\s*ΔCA/);
    expect(progress).toMatch(/<th[^>]*>\s*Det/);
    expect(progress).toMatch(/<th[^>]*>\s*ΔDet/);
    expect(loans).not.toMatch(/<tbody>/);
    expect(mentoring).not.toMatch(/<tbody>/);
    expect(progress).not.toMatch(/<tbody>/);
  });

  it("Mentoring empty hides Add group and Load a Career Save; drop still feeds +", () => {
    expect(css).toMatch(
      /\.table-pane\.is-empty-pane \.mentoring-board-actions/,
    );
    expect(main).toMatch(/mentoringBoardActionsEl\.hidden = true/);
    expect(main).toMatch(
      /mentoringBoardActionsEl\.hidden = mentoringCache\.groups\.length === 0/,
    );
    expect(main).not.toMatch(/setMentoringStatusNotice\("Load a Career Save"\)/);
    expect(main).toMatch(/function feedRosterUpload\(/);
    expect(main).toMatch(
      /function feedRosterUpload\([\s\S]*?rosterAmendTarget = null/,
    );
    expect(main).toMatch(/rosterUploadEl\.files = dt\.files/);
    expect(main).toMatch(/data-pane-drop/);
  });
});
