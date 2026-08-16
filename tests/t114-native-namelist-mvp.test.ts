import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  SQUAD_HA_FILTER_KEYS,
  SQUAD_HA_UNIT_ORDER,
  matchSquadHaFilter,
  type SquadHaRow,
} from "../web/squad-ha-table.ts";

const root = process.cwd();
const vite = fs.readFileSync(path.join(root, "vite.config.ts"), "utf8");
const extractTs = fs.readFileSync(
  path.join(root, "shared", "save", "extract-first-team.ts"),
  "utf8",
);
const extractPy = fs.readFileSync(
  path.join(root, "scripts", "extract-squad-lists.py"),
  "utf8",
);

describe("T114 native clubIdAbs+488 namelist → Squad", () => {
  it("roster extract uses +488 namelist (not T108/T111 Senior)", () => {
    expect(extractTs).toMatch(/extract-squad-lists\.py/);
    expect(extractTs).toMatch(/clubIdAbs\+488/);
    expect(extractTs).not.toMatch(/scripts[/\\]extract-first-team-fast\.py/);
    expect(extractPy).toMatch(/native-clubid-plus488-v1/);
    expect(extractPy).toMatch(/CLUB_ID_NAMELIST_REL = 488/);
    expect(extractPy).toMatch(/continue-skip-native-plus488/);
    expect(extractPy).not.toMatch(/senior-squad-object-v1/);
    expect(extractPy).not.toMatch(/NAME_LIST_WINDOW/);
    expect(vite).toMatch(/T114: \+ \/ roster POST runs native clubIdAbs\+488/);
  });

  it("Squad table accepts unit list (not Senior claim)", () => {
    expect(SQUAD_HA_FILTER_KEYS).toContain("name");
    expect(SQUAD_HA_FILTER_KEYS).toContain("uid");
    expect(SQUAD_HA_FILTER_KEYS).toContain("unit");
    expect(SQUAD_HA_UNIT_ORDER).toContain("list");
    const row: SquadHaRow = {
      uid: 1,
      name: "Alisson",
      unit: "list",
      age: null,
      personality: null,
      mediaHandling: null,
      attrs: {
        determination: null,
        professionalism: null,
        pressure: null,
        ambition: null,
        temperament: null,
        leadership: null,
        loyalty: null,
        sportsmanship: null,
        controversy: null,
      },
      has: null,
    };
    expect(
      matchSquadHaFilter(row, {
        id: "1",
        key: "unit",
        op: "eq",
        value: "list",
      }),
    ).toBe(true);
  });
});
