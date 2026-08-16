import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const html = fs.readFileSync(path.join(root, "web", "index.html"), "utf8");
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const css = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");

const DROP = "Drop a Career Save (.fm) here, or use +";

const EMPTY_HOSTS = [
  "squad-ha-empty-host",
  "squad-loans-empty-host",
  "mentoring-empty-host",
  "squad-progress-empty",
] as const;

function hostBlock(id: string): string {
  const start = html.indexOf(`id="${id}"`);
  expect(start).toBeGreaterThan(-1);
  const open = html.lastIndexOf("<", start);
  const close = "</div>";
  let depth = 0;
  let i = open;
  while (i < html.length) {
    const nextOpen = html.indexOf("<div", i);
    const nextClose = html.indexOf(close, i);
    if (nextClose < 0) break;
    if (nextOpen >= 0 && nextOpen < nextClose) {
      depth += 1;
      i = nextOpen + 4;
      continue;
    }
    depth -= 1;
    if (depth === 0) return html.slice(open, nextClose + close.length);
    i = nextClose + close.length;
  }
  return html.slice(open);
}

describe("T107 standardize pane thead + identical drop well", () => {
  it("all four empty hosts share table-pane-head then table-pane-drop", () => {
    for (const id of EMPTY_HOSTS) {
      const block = hostBlock(id);
      expect(block).toMatch(/class="table-pane-empty"/);
      expect(block).toMatch(/class="table-pane-head"/);
      expect(block).toMatch(/class="table-pane-drop"/);
      expect(block).toContain(DROP);
      const headAt = block.indexOf('class="table-pane-head"');
      const dropAt = block.indexOf('class="table-pane-drop"');
      expect(headAt).toBeGreaterThan(-1);
      expect(dropAt).toBeGreaterThan(headAt);
      expect(block).not.toMatch(/<tbody>/);
    }
  });

  it("shared thead typography tokens cover pane head and Squad HA head", () => {
    expect(css).toMatch(
      /\.table-pane-head \.ranker-list-table thead th,\s*\.squad-ha-list \.ranker-list-table thead th\s*\{/,
    );
    expect(css).toMatch(
      /\.table-pane-head \.ranker-list-table thead th,\s*\.squad-ha-list \.ranker-list-table thead th\s*\{[^}]*font-size:\s*0\.68rem/,
    );
    expect(css).toMatch(
      /\.table-pane-head \.ranker-list-table thead th,\s*\.squad-ha-list \.ranker-list-table thead th\s*\{[^}]*font-weight:\s*650/,
    );
    expect(css).toMatch(
      /\.table-pane-head \.ranker-list-table thead th,\s*\.squad-ha-list \.ranker-list-table thead th\s*\{[^}]*letter-spacing:\s*0\.03em/,
    );
    expect(css).toMatch(
      /\.table-pane-head \.ranker-list-table thead th,\s*\.squad-ha-list \.ranker-list-table thead th\s*\{[^}]*vertical-align:\s*middle/,
    );
    expect(css).toMatch(
      /\.table-pane-head \.ranker-list-table thead th,\s*\.squad-ha-list \.ranker-list-table thead th\s*\{[^}]*padding:\s*0\.4rem 0\.45rem/,
    );
  });

  it("drop well geometry is one shared rule; Mentoring empty hides mentee strip", () => {
    expect(css).toMatch(
      /\.table-pane-drop\s*\{[^}]*flex:\s*1 1 auto/,
    );
    expect(css).toMatch(
      /\.table-pane-drop\s*\{[^}]*padding:\s*1rem 1\.25rem/,
    );
    expect(css).toMatch(
      /\.table-pane\.is-empty-pane\s*>\s*\.mentoring-mentees/,
    );
    expect(main).toMatch(/squadHaEmptyHostEl\.hidden = !showDrop/);
    expect(main).toMatch(
      /mentoringMenteesEl\.hidden = true[\s\S]*setMentoringStatusNotice\(""\)/,
    );
    expect(css).not.toMatch(/\.roster-empty\s*\{[^}]*position:\s*absolute/);
  });
});
