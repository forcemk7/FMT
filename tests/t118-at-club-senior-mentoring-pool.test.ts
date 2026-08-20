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

describe("T118 at-club Senior UniqueIDs → Squad mentoring pool", () => {
  it("roster extract uses club .dat Senior (not +488)", () => {
    expect(extractTs).toMatch(/extract-squad-lists\.py/);
    expect(extractTs).toMatch(/native-club-dat-senior|club `\.dat` intern list/);
    expect(extractTs).not.toMatch(/scripts[/\\]extract-first-team-fast\.py/);
    expect(extractPy).toMatch(/native-club-dat-senior-v1/);
    expect(extractPy).not.toMatch(/native-clubid-plus488-v1/);
    expect(extractPy).not.toMatch(/CLUB_ID_NAMELIST_REL = 488/);
    expect(extractPy).toMatch(/continue-skip-native-club-dat/);
    expect(extractPy).not.toMatch(/2000206937/);
    expect(vite).toMatch(/T118: \+ \/ roster POST runs native club \.dat Senior/);
  });

  it("Squad table accepts unit senior", () => {
    expect(SQUAD_HA_FILTER_KEYS).toContain("name");
    expect(SQUAD_HA_FILTER_KEYS).toContain("uid");
    expect(SQUAD_HA_FILTER_KEYS).toContain("unit");
    expect(SQUAD_HA_UNIT_ORDER).toContain("senior");
    const row: SquadHaRow = {
      uid: 19024412,
      name: "Neymar",
      unit: "senior",
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
        value: "senior",
      }),
    ).toBe(true);
  });
});
