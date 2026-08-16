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

describe("T111 Senior Squad — club → squad object → player ids", () => {
  it("roster extract uses Senior object-path script (not T108/T110 namelist)", () => {
    expect(extractTs).toMatch(/extract-squad-lists\.py/);
    expect(extractTs).toMatch(/Senior Squad object path/);
    expect(extractTs).not.toMatch(/scripts[/\\]extract-first-team-fast\.py/);
    expect(extractPy).toMatch(/senior-squad-object-v1/);
    expect(extractPy).toMatch(/T110 identity-neighborhood namelist/);
    expect(extractPy).not.toMatch(/NAME_LIST_WINDOW/);
    expect(extractPy).not.toMatch(/find_native_identity_namelist/);
    expect(vite).toMatch(/T111: \+ \/ roster POST runs Senior Squad object-path extract/);
  });

  it("Squad table keys include name, uid, and Senior unit", () => {
    expect(SQUAD_HA_FILTER_KEYS).toContain("name");
    expect(SQUAD_HA_FILTER_KEYS).toContain("uid");
    expect(SQUAD_HA_FILTER_KEYS).toContain("unit");
    expect(SQUAD_HA_UNIT_ORDER).toContain("Senior");
    const row: SquadHaRow = {
      uid: 2000175080,
      name: "Example Player",
      unit: "Senior",
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
        key: "uid",
        op: "eq",
        value: "2000175080",
      }),
    ).toBe(true);
    expect(
      matchSquadHaFilter(row, {
        id: "2",
        key: "unit",
        op: "eq",
        value: "Senior",
      }),
    ).toBe(true);
  });
});
