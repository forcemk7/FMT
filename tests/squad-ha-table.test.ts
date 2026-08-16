import { describe, expect, it } from "vitest";
import type { PersonalitySignals } from "../shared/save/types.ts";
import { ageFromDateOfBirth } from "../shared/save/types.ts";
import {
  formatSquadHaCell,
  matchSquadHaFilter,
  mentoringGroupNumberByUid,
  mergeClubWideAtClubPlayers,
  mergeClubWideEmployedPlayers,
  newSquadHaManualFilter,
  nudgeSquadHaFilterBy,
  nudgeSquadHaFiltersBy,
  SQUAD_HA_AGE_FILTER_MAX,
  SQUAD_HA_AGE_FILTER_MIN,
  SQUAD_HA_AGE_GAP,
  SQUAD_HA_ATTR_FILTER_MAX,
  SQUAD_HA_ATTR_FILTER_MIN,
  SQUAD_HA_COL_META,
  SQUAD_HA_ELLIPSIS_KEYS,
  SQUAD_HA_FILTER_KEYS,
  SQUAD_HA_GROUP_HEADER,
  SQUAD_HA_GROUP_HEADER_TIP,
  SQUAD_HA_YOUNG_AGE,
  squadHaAddMentoringUnitGate,
  squadHaAttrsFromSignals,
  squadHaCheckCompletesUnit,
  squadHaClickPreset,
  squadHaEllipsisCellText,
  squadHaEllipsisCellTitle,
  squadHaFilterKeyLabel,
  squadHaNotWorsePreset,
  squadHaNumericFilterValueOptions,
  squadHaRowVisible,
  squadHaTableHeaderLabel,
  squadHaTextOverflows,
  toggleSquadHaSelection,
  toggleSquadHaUnitCheck,
  type SquadHaFilter,
  type SquadHaFilterJoin,
  type SquadHaRow,
  type SquadHaUnit,
} from "../web/squad-ha-table.ts";

function signals(
  partial: Partial<PersonalitySignals>,
): PersonalitySignals {
  return {
    determination: null,
    leadership: null,
    ambition: null,
    controversy: null,
    loyalty: null,
    pressure: null,
    professionalism: null,
    sportsmanship: null,
    temperament: null,
    ...partial,
  };
}

let seq = 0;
function nextId(): string {
  seq += 1;
  return `f-${seq}`;
}

function row(
  uid: number,
  name: string,
  pa: Partial<PersonalitySignals>,
  extra?: Partial<SquadHaRow>,
): SquadHaRow {
  return {
    uid,
    name,
    unit: extra?.unit ?? "FT",
    age: extra?.age ?? null,
    personality: extra?.personality ?? "Fairly Determined",
    mediaHandling: extra?.mediaHandling ?? "Media-friendly",
    attrs: squadHaAttrsFromSignals(signals(pa)),
    has: extra?.has ?? null,
  };
}

describe("squadHaAttrsFromSignals", () => {
  it("extracts integers and leaves holes as null — never invents", () => {
    const attrs = squadHaAttrsFromSignals(
      signals({ professionalism: 14, determination: 12 }),
    );
    expect(attrs.professionalism).toBe(14);
    expect(attrs.determination).toBe(12);
    expect(attrs.ambition).toBeNull();
    expect(formatSquadHaCell(attrs.ambition)).toBe("—");
    expect(formatSquadHaCell(attrs.professionalism)).toBe("14");
  });
});

describe("one-click not-worse-than preset", () => {
  it("writes ≥ floors and CON ≤ from one kid's extract, not HAS", () => {
    const kid = row(1, "Kid", {
      determination: 12,
      professionalism: 10,
      pressure: 11,
      ambition: 8,
      temperament: 13,
      leadership: 6,
      loyalty: 14,
      sportsmanship: 9,
      controversy: 7,
    }, { has: 11.2 });
    const { filters } = squadHaNotWorsePreset([kid], nextId);
    expect(filters.some((f) => f.key === "has")).toBe(false);
    const byKey = Object.fromEntries(filters.map((f) => [f.key, f]));
    expect(byKey.determination).toMatchObject({ op: "gte", value: 12 });
    expect(byKey.professionalism).toMatchObject({ op: "gte", value: 10 });
    expect(byKey.pressure).toMatchObject({ op: "gte", value: 11 });
    expect(byKey.ambition).toMatchObject({ op: "gte", value: 8 });
    expect(byKey.temperament).toMatchObject({ op: "gte", value: 13 });
    expect(byKey.leadership).toMatchObject({ op: "gte", value: 6 });
    expect(byKey.loyalty).toMatchObject({ op: "gte", value: 14 });
    expect(byKey.sportsmanship).toMatchObject({ op: "gte", value: 9 });
    expect(byKey.controversy).toMatchObject({ op: "lte", value: 7 });
  });

  it("T014 Gilson tip Det14/Lea16 writes Det ≥ and Lea ≥ into the preset", () => {
    const gilson = row(
      2002200653,
      "Domenico Gilson",
      {
        determination: 14,
        leadership: 16,
        ambition: 15,
        loyalty: 15,
        pressure: 18,
        professionalism: 16,
        sportsmanship: 16,
        temperament: 13,
        controversy: 5,
      },
      {
        personality: "Light-Hearted",
        mediaHandling: "Evasive, Reserved",
      },
    );
    const { filters } = squadHaNotWorsePreset([gilson], nextId);
    const byKey = Object.fromEntries(filters.map((f) => [f.key, f]));
    expect(byKey.determination).toMatchObject({ op: "gte", value: 14 });
    expect(byKey.leadership).toMatchObject({ op: "gte", value: 16 });
  });

  it("pair uses per-attr max and CON min so a mentor cannot pull either down", () => {
    const a = row(1, "A", {
      determination: 12,
      professionalism: 10,
      controversy: 8,
      sportsmanship: 15,
    });
    const b = row(2, "B", {
      determination: 15,
      professionalism: 11,
      controversy: 5,
      sportsmanship: 9,
    });
    const { filters } = squadHaNotWorsePreset([a, b], nextId);
    const byKey = Object.fromEntries(filters.map((f) => [f.key, f]));
    expect(byKey.determination).toMatchObject({ op: "gte", value: 15 });
    expect(byKey.professionalism).toMatchObject({ op: "gte", value: 11 });
    expect(byKey.sportsmanship).toMatchObject({ op: "gte", value: 15 });
    expect(byKey.controversy).toMatchObject({ op: "lte", value: 5 });
  });

  it("skips an attr when every selected extract is missing it", () => {
    const kid = row(1, "Kid", { professionalism: 14, controversy: 6 });
    const { filters } = squadHaNotWorsePreset([kid], nextId);
    expect(filters.some((f) => f.key === "determination")).toBe(false);
    expect(filters.some((f) => f.key === "professionalism")).toBe(true);
  });
});

describe("filter matching", () => {
  const kid = row(1, "Kid", {
    determination: 12,
    professionalism: 10,
    pressure: 11,
    ambition: 8,
    temperament: 13,
    leadership: 6,
    loyalty: 14,
    sportsmanship: 9,
    controversy: 7,
  }, { has: 9.5 });

  const seniorOk = row(2, "Senior Ok", {
    determination: 12,
    professionalism: 10,
    pressure: 11,
    ambition: 8,
    temperament: 13,
    leadership: 6,
    loyalty: 14,
    sportsmanship: 9,
    controversy: 7,
  }, { has: 8.0 });

  const seniorLowPro = row(3, "Low Pro", {
    determination: 18,
    professionalism: 9,
    pressure: 18,
    ambition: 18,
    temperament: 18,
    leadership: 18,
    loyalty: 18,
    sportsmanship: 18,
    controversy: 2,
  }, { has: 16.0 });

  const missingPro = row(4, "Hole", {
    determination: 18,
    pressure: 18,
    ambition: 18,
    temperament: 18,
    leadership: 18,
    loyalty: 18,
    sportsmanship: 18,
    controversy: 2,
  });

  const preset = squadHaNotWorsePreset([kid], nextId);

  it("keeps equal Pro when nothing else is worse", () => {
    expect(squadHaRowVisible(seniorOk, preset.filters, preset.joins, [1])).toBe(
      true,
    );
  });

  it("hides a senior with lower Det than the clicked kid", () => {
    const gabor = row(1, "Gabor", {
      determination: 18,
      professionalism: 15,
      pressure: 13,
      ambition: 17,
      temperament: 16,
      leadership: 15,
      loyalty: 14,
      sportsmanship: 8,
      controversy: 13,
    });
    const radovic = row(2, "Radovic", {
      determination: 16,
      professionalism: 15,
      pressure: 6,
      ambition: 13,
      temperament: 17,
      leadership: 16,
      loyalty: 10,
      sportsmanship: 12,
      controversy: 8,
    });
    const preset = squadHaNotWorsePreset([gabor], nextId);
    expect(preset.filters.some((f) => f.key === "determination" && f.value === 18)).toBe(
      true,
    );
    expect(preset.filters.some((f) => f.key === "leadership" && f.value === 15)).toBe(
      true,
    );
    expect(squadHaRowVisible(radovic, preset.filters, preset.joins, [1])).toBe(
      false,
    );
    expect(squadHaRowVisible(gabor, preset.filters, preset.joins, [1])).toBe(true);
  });

  it("hides a senior with lower Pro than the floor even if HAS is higher", () => {
    expect(
      squadHaRowVisible(seniorLowPro, preset.filters, preset.joins, [1]),
    ).toBe(false);
  });

  it("hides a candidate missing a required attr (fail closed)", () => {
    expect(
      squadHaRowVisible(missingPro, preset.filters, preset.joins, [1]),
    ).toBe(false);
  });

  it("keeps the selected kid visible", () => {
    expect(squadHaRowVisible(kid, preset.filters, preset.joins, [1])).toBe(true);
  });

  it("keeps both selected pair rows visible even when one is below the pair max", () => {
    const a = row(10, "A", {
      determination: 12,
      professionalism: 14,
      controversy: 8,
    });
    const b = row(11, "B", {
      determination: 16,
      professionalism: 10,
      controversy: 4,
    });
    const pair = squadHaNotWorsePreset([a, b], nextId);
    expect(squadHaRowVisible(a, pair.filters, pair.joins, [10, 11])).toBe(true);
    expect(squadHaRowVisible(b, pair.filters, pair.joins, [10, 11])).toBe(true);
  });

  it("lets the user drop one filter without resetting the rest", () => {
    const withoutSpo = preset.filters.filter((f) => f.key !== "sportsmanship");
    const joins = withoutSpo.slice(1).map(() => "and" as const);
    const lowSpo = row(5, "Low Spo", {
      determination: 12,
      professionalism: 10,
      pressure: 11,
      ambition: 8,
      temperament: 13,
      leadership: 6,
      loyalty: 14,
      sportsmanship: 1,
      controversy: 7,
    });
    const stillLowPro = row(6, "Still Low Pro", {
      determination: 12,
      professionalism: 9,
      pressure: 11,
      ambition: 8,
      temperament: 13,
      leadership: 6,
      loyalty: 14,
      sportsmanship: 20,
      controversy: 7,
    });
    expect(squadHaRowVisible(lowSpo, withoutSpo, joins, [1])).toBe(true);
    expect(squadHaRowVisible(stillLowPro, withoutSpo, joins, [1])).toBe(false);
  });

  it("does not treat HAS as the better-than test", () => {
    const hasFilter: SquadHaFilter = {
      id: "has",
      key: "has",
      op: "gte",
      value: 12,
    };
    expect(matchSquadHaFilter(seniorLowPro, hasFilter)).toBe(true);
    expect(
      squadHaRowVisible(seniorLowPro, preset.filters, preset.joins, [1]),
    ).toBe(false);
  });
});

describe("toggleSquadHaSelection", () => {
  it("selects one, then two, then a third click starts over", () => {
    expect(toggleSquadHaSelection([], 1)).toEqual([1]);
    expect(toggleSquadHaSelection([1], 2)).toEqual([1, 2]);
    expect(toggleSquadHaSelection([1, 2], 3)).toEqual([3]);
    expect(toggleSquadHaSelection([1, 2], 1)).toEqual([2]);
  });
});

describe("HA table mentoring unit check (T036)", () => {
  it("caps checkbox selection at mentoring unit size 3", () => {
    expect(toggleSquadHaUnitCheck([], 1)).toEqual([1]);
    expect(toggleSquadHaUnitCheck([1], 2)).toEqual([1, 2]);
    expect(toggleSquadHaUnitCheck([1, 2], 3)).toEqual([1, 2, 3]);
    expect(toggleSquadHaUnitCheck([1, 2, 3], 4)).toEqual([1, 2, 3]);
    expect(toggleSquadHaUnitCheck([1, 2, 3], 2)).toEqual([1, 3]);
  });

  it("maps assigned uids to 1-based group numbers", () => {
    const map = mentoringGroupNumberByUid([
      { memberIds: ["10", "11", "12"] },
      { memberIds: ["20", "21", "22"] },
    ]);
    expect(map.get(10)).toBe(1);
    expect(map.get(21)).toBe(2);
    expect(map.has(99)).toBe(false);
  });

  it("gates Add on exactly 3 eligible unassigned players and create slot", () => {
    const eligible = new Set([1, 2, 3, 4]);
    const assigned = new Set<number>();
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: [1, 2],
        assignedUids: assigned,
        eligibleUids: eligible,
        canCreateSlot: true,
        maxGroupsReached: false,
      }),
    ).toMatchObject({ ok: false, reason: "Need 3 players (2/3)" });
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: [1, 2, 3],
        assignedUids: assigned,
        eligibleUids: eligible,
        canCreateSlot: true,
        maxGroupsReached: false,
      }),
    ).toEqual({ ok: true, reason: "" });
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: [1, 2, 9],
        assignedUids: assigned,
        eligibleUids: eligible,
        canCreateSlot: true,
        maxGroupsReached: false,
      }).ok,
    ).toBe(false);
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: [1, 2, 3],
        assignedUids: new Set([2]),
        eligibleUids: eligible,
        canCreateSlot: true,
        maxGroupsReached: false,
      }).ok,
    ).toBe(false);
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: [1, 2, 3],
        assignedUids: assigned,
        eligibleUids: eligible,
        canCreateSlot: false,
        maxGroupsReached: true,
      }).reason,
    ).toBe("Max groups for this squad");
  });
});

describe("HA table Group column (T049)", () => {
  it("header is Group with Mentoring group tooltip, not an Add button", () => {
    expect(SQUAD_HA_GROUP_HEADER).toBe("Group");
    expect(SQUAD_HA_GROUP_HEADER_TIP).toBe("Mentoring group");
    expect(SQUAD_HA_GROUP_HEADER.toLowerCase()).not.toContain("add");
  });

  it("only the third check completes a unit; 1–2 and uncheck do not", () => {
    expect(squadHaCheckCompletesUnit([], [1])).toBe(false);
    expect(squadHaCheckCompletesUnit([1], [1, 2])).toBe(false);
    expect(squadHaCheckCompletesUnit([1, 2], [1, 2, 3])).toBe(true);
    expect(squadHaCheckCompletesUnit([1, 2, 3], [1, 3])).toBe(false);
    expect(squadHaCheckCompletesUnit([1, 2, 3], [1, 2, 3])).toBe(false);
  });

  it("1 or 2 checks do not pass the create gate", () => {
    const eligible = new Set([1, 2, 3, 4]);
    const assigned = new Set<number>();
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: [1],
        assignedUids: assigned,
        eligibleUids: eligible,
        canCreateSlot: true,
        maxGroupsReached: false,
      }).ok,
    ).toBe(false);
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: [1, 2],
        assignedUids: assigned,
        eligibleUids: eligible,
        canCreateSlot: true,
        maxGroupsReached: false,
      }).ok,
    ).toBe(false);
  });

  it("invalid third check (grouped / ineligible / max groups) does not create", () => {
    const eligible = new Set([1, 2, 3, 4]);
    const previous = [1, 2];
    const next = toggleSquadHaUnitCheck(previous, 3);
    expect(squadHaCheckCompletesUnit(previous, next)).toBe(true);
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: next,
        assignedUids: new Set([3]),
        eligibleUids: eligible,
        canCreateSlot: true,
        maxGroupsReached: false,
      }),
    ).toMatchObject({ ok: false, reason: "Player already in a group" });
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: [1, 2, 9],
        assignedUids: new Set(),
        eligibleUids: eligible,
        canCreateSlot: true,
        maxGroupsReached: false,
      }),
    ).toMatchObject({ ok: false, reason: "Need Mentoring-eligible players" });
    expect(
      squadHaAddMentoringUnitGate({
        checkedUids: next,
        assignedUids: new Set(),
        eligibleUids: eligible,
        canCreateSlot: false,
        maxGroupsReached: true,
      }),
    ).toMatchObject({ ok: false, reason: "Max groups for this squad" });
  });
});

describe("mergeClubWideAtClubPlayers", () => {
  it("merges FT + II + U19, tags unit, and excludes loaned-out", () => {
    const merged = mergeClubWideAtClubPlayers({
      firstTeam: [
        { uid: 1, name: "FT Senior" },
        { uid: 2, name: "FT Loan", loan: { status: "loanedOut" } },
      ],
      reserves: [{ uid: 3, name: "II Mentor" }],
      under19s: [
        { uid: 4, name: "U19 Kid" },
        { uid: 5, name: "U19 Loan", loan: { status: "loanedOut" } },
      ],
    });
    expect(merged.map((e) => [e.player.uid, e.unit] as const)).toEqual([
      [1, "FT"],
      [3, "II"],
      [4, "U19"],
    ]);
  });

  it("Progress picker keeps outgoing; Squad / Group checks stay at-club", () => {
    const lists = {
      firstTeam: [
        { uid: 1, name: "At Club" },
        { uid: 2, name: "Out On Loan", loan: { status: "loanedOut" as const } },
      ],
      reserves: [{ uid: 3, name: "II Body" }],
      under19s: [],
    };
    const atClub = mergeClubWideAtClubPlayers(lists);
    const employed = mergeClubWideEmployedPlayers(lists);
    expect(atClub.map((e) => e.player.uid)).toEqual([1, 3]);
    expect(employed.map((e) => e.player.uid)).toEqual([1, 2, 3]);
    const squadNames = new Set(atClub.map((e) => e.player.name));
    const loanNames = new Set(
      employed
        .filter((e) => e.player.loan?.status === "loanedOut")
        .map((e) => e.player.name),
    );
    for (const name of loanNames) {
      expect(squadNames.has(name)).toBe(false);
    }
  });

  it("dedupes by uid with FT winning over II/U19", () => {
    const merged = mergeClubWideAtClubPlayers({
      firstTeam: [{ uid: 10, name: "On FT" }],
      reserves: [{ uid: 10, name: "Also II" }],
      under19s: [{ uid: 10, name: "Also U19" }],
    });
    expect(merged).toHaveLength(1);
    expect(merged[0]?.unit).toBe("FT");
    expect(merged[0]?.player.name).toBe("On FT");
  });

  it("drops nameless uid / uid: / job: ghosts; named with no Det still included", () => {
    const merged = mergeClubWideAtClubPlayers({
      firstTeam: [
        { uid: 1, name: "Domenico Gilson" },
        { uid: 2, name: "" },
        { uid: 3, name: "uid:2002282661" },
        { uid: 4, name: "job:437615" },
        { uid: 5, name: "   " },
      ],
      reserves: [{ uid: 6, name: "II Named" }],
      under19s: [{ uid: 7, name: "U19 Named" }],
    });
    expect(merged.map((e) => [e.player.uid, e.unit] as const)).toEqual([
      [1, "FT"],
      [6, "II"],
      [7, "U19"],
    ]);
    const gilson = row(1, "Domenico Gilson", { professionalism: 14 });
    expect(gilson.name).toBe("Domenico Gilson");
    expect(formatSquadHaCell(gilson.attrs.determination)).toBe("—");
    expect(formatSquadHaCell(gilson.attrs.leadership)).toBe("—");
    expect(squadHaRowVisible(gilson, [], [], [])).toBe(true);
  });

  it("lets a U19 kid preset keep an FT senior who passes ≥ floors", () => {
    const kid = row(
      4,
      "U19 Kid",
      {
        determination: 12,
        professionalism: 10,
        pressure: 11,
        ambition: 8,
        temperament: 13,
        leadership: 6,
        loyalty: 14,
        sportsmanship: 9,
        controversy: 7,
      },
      { unit: "U19" },
    );
    const senior = row(
      1,
      "FT Senior",
      {
        determination: 14,
        professionalism: 12,
        pressure: 12,
        ambition: 10,
        temperament: 14,
        leadership: 12,
        loyalty: 15,
        sportsmanship: 11,
        controversy: 5,
      },
      { unit: "FT" },
    );
    const lowPro = row(
      3,
      "II Low Pro",
      {
        determination: 18,
        professionalism: 8,
        pressure: 18,
        ambition: 18,
        temperament: 18,
        leadership: 18,
        loyalty: 18,
        sportsmanship: 18,
        controversy: 2,
      },
      { unit: "II" },
    );
    const preset = squadHaNotWorsePreset([kid], nextId);
    expect(squadHaRowVisible(senior, preset.filters, preset.joins, [4])).toBe(
      true,
    );
    expect(squadHaRowVisible(lowPro, preset.filters, preset.joins, [4])).toBe(
      false,
    );
    expect(squadHaRowVisible(kid, preset.filters, preset.joins, [4])).toBe(true);
    const units: SquadHaUnit[] = [kid.unit, senior.unit, lowPro.unit];
    expect(units).toEqual(["U19", "FT", "II"]);
  });
});

describe("T039 Age column + one-click mentor/mentee preset", () => {
  const kidHa = {
    determination: 12,
    professionalism: 10,
    pressure: 11,
    ambition: 8,
    temperament: 13,
    leadership: 6,
    loyalty: 14,
    sportsmanship: 9,
    controversy: 7,
  };

  it("uses DOB + game date for age; blank DOB is — not 0", () => {
    expect(ageFromDateOfBirth("2007-07-01", "2026-07-01")).toBe(19);
    expect(ageFromDateOfBirth(null, "2026-07-01")).toBeNull();
    expect(ageFromDateOfBirth("", "2026-07-01")).toBeNull();
    expect(formatSquadHaCell(ageFromDateOfBirth(null, "2026-07-01"))).toBe("—");
    expect(formatSquadHaCell(0)).not.toBe("—");
    expect(SQUAD_HA_YOUNG_AGE).toBe(24);
    expect(SQUAD_HA_AGE_GAP).toBe(3);
  });

  it("lists every data column in table order for filters", () => {
    expect([...SQUAD_HA_FILTER_KEYS]).toEqual([
      "name",
      "unit",
      "age",
      "personality",
      "mediaHandling",
      "determination",
      "professionalism",
      "pressure",
      "ambition",
      "temperament",
      "leadership",
      "loyalty",
      "sportsmanship",
      "controversy",
      "has",
    ]);
  });

  it("click age 19 writes Age ≥ 22 and T033 HA ≥; same-age peers drop; selected stays", () => {
    const kid = row(1, "Kid", kidHa, { age: 19 });
    const peer = row(2, "Peer", kidHa, { age: 19 });
    const mentor = row(3, "Mentor", {
      ...kidHa,
      determination: 14,
      professionalism: 12,
      controversy: 5,
    }, { age: 22 });
    const { filters, joins } = squadHaClickPreset([kid], nextId);
    const ageFilter = filters.find((f) => f.key === "age");
    expect(ageFilter).toMatchObject({ op: "gte", value: 22 });
    expect(filters.some((f) => f.key === "determination" && f.op === "gte" && f.value === 12)).toBe(
      true,
    );
    expect(filters.some((f) => f.key === "controversy" && f.op === "lte" && f.value === 7)).toBe(
      true,
    );
    expect(squadHaRowVisible(kid, filters, joins, [1])).toBe(true);
    expect(squadHaRowVisible(peer, filters, joins, [1])).toBe(false);
    expect(squadHaRowVisible(mentor, filters, joins, [1])).toBe(true);
  });

  it("click age 27 writes Age ≤ 24 and inverted HA; better 30yo hides; 21yo not-better remains", () => {
    const senior = row(10, "Senior", {
      determination: 15,
      professionalism: 14,
      pressure: 12,
      ambition: 11,
      temperament: 13,
      leadership: 16,
      loyalty: 14,
      sportsmanship: 10,
      controversy: 8,
    }, { age: 27 });
    const olderBetter = row(11, "Older Better", {
      determination: 16,
      professionalism: 18,
      pressure: 12,
      ambition: 11,
      temperament: 13,
      leadership: 16,
      loyalty: 14,
      sportsmanship: 10,
      controversy: 8,
    }, { age: 30 });
    const menteeOk = row(12, "Mentee Ok", {
      determination: 12,
      professionalism: 12,
      pressure: 10,
      ambition: 9,
      temperament: 12,
      leadership: 8,
      loyalty: 12,
      sportsmanship: 8,
      controversy: 10,
    }, { age: 21 });
    const { filters, joins } = squadHaClickPreset([senior], nextId);
    expect(filters.find((f) => f.key === "age")).toMatchObject({
      op: "lte",
      value: 24,
    });
    expect(filters.some((f) => f.key === "determination" && f.op === "lte" && f.value === 15)).toBe(
      true,
    );
    expect(filters.some((f) => f.key === "controversy" && f.op === "gte" && f.value === 8)).toBe(
      true,
    );
    expect(squadHaRowVisible(senior, filters, joins, [10])).toBe(true);
    expect(squadHaRowVisible(olderBetter, filters, joins, [10])).toBe(false);
    expect(squadHaRowVisible(menteeOk, filters, joins, [10])).toBe(true);
  });

  it("lets the user drop only the Age row without resetting HA filters", () => {
    const kid = row(1, "Kid", kidHa, { age: 19 });
    const peer = row(2, "Peer", kidHa, { age: 19 });
    const lowPro = row(3, "Low Pro", { ...kidHa, professionalism: 8 }, { age: 25 });
    const { filters } = squadHaClickPreset([kid], nextId);
    const withoutAge = filters.filter((f) => f.key !== "age");
    const joins = withoutAge.slice(1).map(() => "and" as const);
    expect(withoutAge.some((f) => f.key === "age")).toBe(false);
    expect(withoutAge.some((f) => f.key === "professionalism")).toBe(true);
    expect(squadHaRowVisible(peer, withoutAge, joins, [1])).toBe(true);
    expect(squadHaRowVisible(lowPro, withoutAge, joins, [1])).toBe(false);
  });

  it("accepts Age filter values above 20", () => {
    const age22: SquadHaFilter = { id: "age", key: "age", op: "gte", value: 22 };
    expect(
      matchSquadHaFilter(row(1, "A", kidHa, { age: 22 }), age22),
    ).toBe(true);
    expect(
      matchSquadHaFilter(row(2, "B", kidHa, { age: 19 }), age22),
    ).toBe(false);
    expect(
      matchSquadHaFilter(row(3, "C", kidHa, { age: 30 }), age22),
    ).toBe(true);
  });

  it("Name and Unit filters match like other text keys", () => {
    const kid = row(1, "Kid", kidHa, { unit: "U19", age: 19 });
    expect(
      matchSquadHaFilter(kid, { id: "n", key: "name", op: "eq", value: "Kid" }),
    ).toBe(true);
    expect(
      matchSquadHaFilter(kid, { id: "u", key: "unit", op: "eq", value: "U19" }),
    ).toBe(true);
    expect(
      matchSquadHaFilter(kid, { id: "ft", key: "unit", op: "eq", value: "FT" }),
    ).toBe(false);
  });

  it("skips Age filter when DOB is missing; HA preset still runs", () => {
    const kid = row(1, "No Age", kidHa, { age: null });
    const { filters } = squadHaClickPreset([kid], nextId);
    expect(filters.some((f) => f.key === "age")).toBe(false);
    expect(filters.some((f) => f.key === "determination" && f.op === "gte")).toBe(
      true,
    );
  });

  it("pair click stays T033 HA-only with no Age row", () => {
    const a = row(1, "A", kidHa, { age: 19 });
    const b = row(2, "B", kidHa, { age: 27 });
    const { filters } = squadHaClickPreset([a, b], nextId);
    expect(filters.some((f) => f.key === "age")).toBe(false);
    expect(filters.some((f) => f.key === "determination" && f.op === "gte")).toBe(
      true,
    );
  });
});

describe("T041 filter labels + ± / loosen-all", () => {
  it("spells out filter keys; table headers stay short", () => {
    expect(squadHaFilterKeyLabel("determination")).toBe("Determination");
    expect(squadHaFilterKeyLabel("professionalism")).toBe("Professionalism");
    expect(squadHaFilterKeyLabel("pressure")).toBe("Pressure");
    expect(squadHaFilterKeyLabel("ambition")).toBe("Ambition");
    expect(squadHaFilterKeyLabel("temperament")).toBe("Temperament");
    expect(squadHaFilterKeyLabel("leadership")).toBe("Leadership");
    expect(squadHaFilterKeyLabel("loyalty")).toBe("Loyalty");
    expect(squadHaFilterKeyLabel("sportsmanship")).toBe("Sportsmanship");
    expect(squadHaFilterKeyLabel("controversy")).toBe("Controversy");
    expect(squadHaFilterKeyLabel("unit")).toBe("Squad");
    expect(squadHaFilterKeyLabel("mediaHandling")).toBe("Media Handling");
    expect(squadHaFilterKeyLabel("name")).toBe("Name");
    expect(squadHaFilterKeyLabel("age")).toBe("Age");
    expect(squadHaFilterKeyLabel("personality")).toBe("Personality");
    expect(squadHaFilterKeyLabel("has")).toBe("HAS");

    expect(squadHaTableHeaderLabel("determination")).toBe("DET");
    expect(squadHaTableHeaderLabel("unit")).toBe("Unit");
    expect(squadHaTableHeaderLabel("mediaHandling")).toBe("Media");
    expect(SQUAD_HA_COL_META.determination.header).toBe("DET");
    expect(squadHaTableHeaderLabel("name")).toBe("Name");
    expect(squadHaTableHeaderLabel("age")).toBe("Age");
    expect(squadHaTableHeaderLabel("personality")).toBe("Personality");
    expect(squadHaTableHeaderLabel("has")).toBe("HAS");
  });

  it("per-row +/− changes DET ≥ 15 by 1 without a new op", () => {
    const det: SquadHaFilter = {
      id: "det",
      key: "determination",
      op: "gte",
      value: 15,
    };
    expect(nudgeSquadHaFilterBy(det, 1)).toMatchObject({
      op: "gte",
      value: 16,
    });
    expect(nudgeSquadHaFilterBy(det, -1)).toMatchObject({
      op: "gte",
      value: 14,
    });
    expect(nudgeSquadHaFilterBy(det, 1).key).toBe("determination");
  });

  it("clamps HA/HAS to 1–20 and Age to a wider band", () => {
    expect(SQUAD_HA_ATTR_FILTER_MIN).toBe(1);
    expect(SQUAD_HA_ATTR_FILTER_MAX).toBe(20);
    expect(SQUAD_HA_AGE_FILTER_MIN).toBe(0);
    expect(SQUAD_HA_AGE_FILTER_MAX).toBe(50);
    expect(
      nudgeSquadHaFilterBy(
        { id: "d", key: "determination", op: "gte", value: 20 },
        1,
      ).value,
    ).toBe(20);
    expect(
      nudgeSquadHaFilterBy(
        { id: "d", key: "determination", op: "gte", value: 1 },
        -1,
      ).value,
    ).toBe(1);
    expect(
      nudgeSquadHaFilterBy({ id: "h", key: "has", op: "gte", value: 20 }, 1)
        .value,
    ).toBe(20);
    expect(
      nudgeSquadHaFilterBy({ id: "a", key: "age", op: "gte", value: 22 }, 1)
        .value,
    ).toBe(23);
    expect(
      nudgeSquadHaFilterBy({ id: "a", key: "age", op: "gte", value: 50 }, 1)
        .value,
    ).toBe(50);
    expect(
      nudgeSquadHaFilterBy({ id: "a", key: "age", op: "gte", value: 0 }, -1)
        .value,
    ).toBe(0);
  });

  it("Age is at most 24: row + is 25, row − is 23", () => {
    const age: SquadHaFilter = { id: "a", key: "age", op: "lte", value: 24 };
    expect(nudgeSquadHaFilterBy(age, 1)).toMatchObject({
      op: "lte",
      value: 25,
    });
    expect(nudgeSquadHaFilterBy(age, -1)).toMatchObject({
      op: "lte",
      value: 23,
    });
  });

  it("DET is at least 18: row − is 17, row + is 19", () => {
    const det: SquadHaFilter = {
      id: "det",
      key: "determination",
      op: "gte",
      value: 18,
    };
    expect(nudgeSquadHaFilterBy(det, -1)).toMatchObject({
      op: "gte",
      value: 17,
    });
    expect(nudgeSquadHaFilterBy(det, 1)).toMatchObject({
      op: "gte",
      value: 19,
    });
  });
});

describe("T045 footer ± is the number, not the operator", () => {
  it("18 gte and 18 lte both −1 → 17; both +1 → 19; ops stay", () => {
    const filters: SquadHaFilter[] = [
      { id: "det", key: "determination", op: "gte", value: 18 },
      { id: "has", key: "has", op: "lte", value: 18 },
      { id: "name", key: "name", op: "eq", value: "Kid" },
      { id: "unit", key: "unit", op: "eq", value: "FT" },
    ];
    const down = nudgeSquadHaFiltersBy(filters, -1);
    expect(down.find((f) => f.id === "det")).toMatchObject({
      op: "gte",
      value: 17,
    });
    expect(down.find((f) => f.id === "has")).toMatchObject({
      op: "lte",
      value: 17,
    });
    expect(down.find((f) => f.id === "name")).toMatchObject({
      op: "eq",
      value: "Kid",
    });
    expect(down.find((f) => f.id === "unit")).toMatchObject({
      op: "eq",
      value: "FT",
    });
    const up = nudgeSquadHaFiltersBy(filters, 1);
    expect(up.find((f) => f.id === "det")).toMatchObject({
      op: "gte",
      value: 19,
    });
    expect(up.find((f) => f.id === "has")).toMatchObject({
      op: "lte",
      value: 19,
    });
  });

  it("kid one-click: footer −1 drops DET/HAS-style floors; Age stays; CON inverts (T047/T060)", () => {
    const kidHa = {
      determination: 12,
      professionalism: 10,
      pressure: 11,
      ambition: 8,
      temperament: 13,
      leadership: 6,
      loyalty: 14,
      sportsmanship: 9,
      controversy: 7,
    };
    const kid = row(1, "Kid", kidHa, { age: 19 });
    const { filters } = squadHaClickPreset([kid], nextId);
    const down = nudgeSquadHaFiltersBy(filters, -1);
    const byKey = Object.fromEntries(down.map((f) => [f.key, f]));
    expect(byKey.age).toMatchObject({ op: "gte", value: 22 });
    expect(byKey.determination).toMatchObject({ op: "gte", value: 11 });
    expect(byKey.professionalism).toMatchObject({ op: "gte", value: 9 });
    expect(byKey.pressure).toMatchObject({ op: "gte", value: 10 });
    expect(byKey.ambition).toMatchObject({ op: "gte", value: 7 });
    expect(byKey.temperament).toMatchObject({ op: "gte", value: 12 });
    expect(byKey.leadership).toMatchObject({ op: "gte", value: 5 });
    expect(byKey.loyalty).toMatchObject({ op: "gte", value: 13 });
    expect(byKey.sportsmanship).toMatchObject({ op: "gte", value: 8 });
    expect(byKey.controversy).toMatchObject({ op: "lte", value: 8 });
    expect(down.some((f) => f.key === "has")).toBe(false);
  });
});

describe("T047 footer ± inverts Controversy only", () => {
  it("CON ≤ 18 + footer +1 → 17; DET ≥ 18 → 19", () => {
    const filters: SquadHaFilter[] = [
      { id: "det", key: "determination", op: "gte", value: 18 },
      { id: "con", key: "controversy", op: "lte", value: 18 },
    ];
    const up = nudgeSquadHaFiltersBy(filters, 1);
    expect(up.find((f) => f.id === "con")).toMatchObject({
      op: "lte",
      value: 17,
    });
    expect(up.find((f) => f.id === "det")).toMatchObject({
      op: "gte",
      value: 19,
    });
  });

  it("same mix + footer −1 → CON 19, DET 17", () => {
    const filters: SquadHaFilter[] = [
      { id: "det", key: "determination", op: "gte", value: 18 },
      { id: "con", key: "controversy", op: "lte", value: 18 },
    ];
    const down = nudgeSquadHaFiltersBy(filters, -1);
    expect(down.find((f) => f.id === "con")).toMatchObject({
      op: "lte",
      value: 19,
    });
    expect(down.find((f) => f.id === "det")).toMatchObject({
      op: "gte",
      value: 17,
    });
  });

  it("CON row’s own + → 19, − → 17", () => {
    const con: SquadHaFilter = {
      id: "con",
      key: "controversy",
      op: "lte",
      value: 18,
    };
    expect(nudgeSquadHaFilterBy(con, 1)).toMatchObject({
      op: "lte",
      value: 19,
    });
    expect(nudgeSquadHaFilterBy(con, -1)).toMatchObject({
      op: "lte",
      value: 17,
    });
  });

  it("HAS is at most 18 follows footer number, not CON invert", () => {
    const filters: SquadHaFilter[] = [
      { id: "has", key: "has", op: "lte", value: 18 },
      { id: "con", key: "controversy", op: "lte", value: 18 },
    ];
    const down = nudgeSquadHaFiltersBy(filters, -1);
    expect(down.find((f) => f.id === "has")).toMatchObject({
      op: "lte",
      value: 17,
    });
    expect(down.find((f) => f.id === "con")).toMatchObject({
      op: "lte",
      value: 19,
    });
  });
});

describe("T060 footer ± skips Age", () => {
  it("Age is at least 21 + footer +1 → Age still 21; DET ≥ 18 → 19", () => {
    const filters: SquadHaFilter[] = [
      { id: "age", key: "age", op: "gte", value: 21 },
      { id: "det", key: "determination", op: "gte", value: 18 },
    ];
    const up = nudgeSquadHaFiltersBy(filters, 1);
    expect(up.find((f) => f.id === "age")).toMatchObject({
      op: "gte",
      value: 21,
    });
    expect(up.find((f) => f.id === "det")).toMatchObject({
      op: "gte",
      value: 19,
    });
  });

  it("Age is at most 24 + footer −1 → Age still 24; DET ≥ 18 → 17", () => {
    const filters: SquadHaFilter[] = [
      { id: "age", key: "age", op: "lte", value: 24 },
      { id: "det", key: "determination", op: "gte", value: 18 },
    ];
    const down = nudgeSquadHaFiltersBy(filters, -1);
    expect(down.find((f) => f.id === "age")).toMatchObject({
      op: "lte",
      value: 24,
    });
    expect(down.find((f) => f.id === "det")).toMatchObject({
      op: "gte",
      value: 17,
    });
  });

  it("Age row’s own + → 22 / 25, − → 20 / 23", () => {
    const gte: SquadHaFilter = { id: "a", key: "age", op: "gte", value: 21 };
    expect(nudgeSquadHaFilterBy(gte, 1)).toMatchObject({
      op: "gte",
      value: 22,
    });
    expect(nudgeSquadHaFilterBy(gte, -1)).toMatchObject({
      op: "gte",
      value: 20,
    });
    const lte: SquadHaFilter = { id: "a", key: "age", op: "lte", value: 24 };
    expect(nudgeSquadHaFilterBy(lte, 1)).toMatchObject({
      op: "lte",
      value: 25,
    });
    expect(nudgeSquadHaFilterBy(lte, -1)).toMatchObject({
      op: "lte",
      value: 23,
    });
  });

  it("CON invert unchanged: CON ≤ 18 + footer +1 → 17", () => {
    const filters: SquadHaFilter[] = [
      { id: "age", key: "age", op: "gte", value: 21 },
      { id: "con", key: "controversy", op: "lte", value: 18 },
    ];
    const up = nudgeSquadHaFiltersBy(filters, 1);
    expect(up.find((f) => f.id === "con")).toMatchObject({
      op: "lte",
      value: 17,
    });
    expect(up.find((f) => f.id === "age")).toMatchObject({
      op: "gte",
      value: 21,
    });
  });
});

describe("T044 Add filter Squad FT; one-click stays HA-only", () => {
  const kidHa = {
    determination: 12,
    professionalism: 10,
    pressure: 11,
    ambition: 8,
    temperament: 13,
    leadership: 6,
    loyalty: 14,
    sportsmanship: 9,
    controversy: 7,
  };

  it("+ Add filter is Squad eq FT; table shows FT only", () => {
    const filter = newSquadHaManualFilter("add");
    expect(filter).toMatchObject({ key: "unit", op: "eq", value: "FT" });
    const filters = [filter];
    const joins: SquadHaFilterJoin[] = [];
    expect(
      squadHaRowVisible(row(1, "FT", kidHa, { unit: "FT" }), filters, joins, []),
    ).toBe(true);
    expect(
      squadHaRowVisible(row(2, "II", kidHa, { unit: "II" }), filters, joins, []),
    ).toBe(false);
    expect(
      squadHaRowVisible(row(3, "U19", kidHa, { unit: "U19" }), filters, joins, []),
    ).toBe(false);
  });

  it("kid/senior one-click does not add a Squad row", () => {
    const kid = row(1, "Kid", kidHa, { age: 19 });
    const senior = row(2, "Senior", kidHa, { age: 27 });
    expect(squadHaClickPreset([kid], nextId).filters.some((f) => f.key === "unit")).toBe(
      false,
    );
    expect(
      squadHaClickPreset([senior], nextId).filters.some((f) => f.key === "unit"),
    ).toBe(false);
  });

  it("empty filter list stays empty — Clear All / no Add", () => {
    expect(squadHaClickPreset([], nextId)).toEqual({ filters: [], joins: [] });
  });
});

describe("T046 Age filter dropdown matches HAS/attr select band", () => {
  it("Age options are 0–50 inclusive; 24 and 33 are in the list; 20 is not the max", () => {
    const ageOpts = squadHaNumericFilterValueOptions("age");
    const values = ageOpts.map((o) => o.value);
    expect(values[0]).toBe("0");
    expect(values.at(-1)).toBe("50");
    expect(values).toContain("24");
    expect(values).toContain("33");
    expect(values).not.toContain("51");
    expect(values.at(-1)).not.toBe("20");
    expect(ageOpts).toHaveLength(51);
  });

  it("HAS / DET stay 1–20", () => {
    const hasOpts = squadHaNumericFilterValueOptions("has").map((o) => o.value);
    const detOpts = squadHaNumericFilterValueOptions("determination").map(
      (o) => o.value,
    );
    expect(hasOpts[0]).toBe("1");
    expect(hasOpts.at(-1)).toBe("20");
    expect(hasOpts).toHaveLength(20);
    expect(detOpts).toEqual(hasOpts);
  });

  it("one-click Age floors land on a dropdown option", () => {
    const kidHa = {
      determination: 12,
      professionalism: 10,
      pressure: 11,
      ambition: 8,
      temperament: 13,
      leadership: 6,
      loyalty: 14,
      sportsmanship: 9,
      controversy: 7,
    };
    const ageValues = new Set(
      squadHaNumericFilterValueOptions("age").map((o) => Number(o.value)),
    );
    const kid = squadHaClickPreset([row(1, "Kid", kidHa, { age: 19 })], nextId);
    const senior = squadHaClickPreset(
      [row(2, "Senior", kidHa, { age: 36 })],
      nextId,
    );
    const kidAge = kid.filters.find((f) => f.key === "age");
    const seniorAge = senior.filters.find((f) => f.key === "age");
    expect(kidAge).toMatchObject({ op: "gte", value: 22 });
    expect(seniorAge).toMatchObject({ op: "lte", value: 33 });
    expect(ageValues.has(Number(kidAge?.value))).toBe(true);
    expect(ageValues.has(Number(seniorAge?.value))).toBe(true);
  });
});

describe("HA truncated-cell tooltip (T052)", () => {
  it("covers Name, Personality, and Media — not only Name", () => {
    expect([...SQUAD_HA_ELLIPSIS_KEYS]).toEqual([
      "name",
      "personality",
      "mediaHandling",
    ]);
    const gilson = row(
      1,
      "Santiago Contreras",
      {},
      {
        personality: "Fairly Determined",
        mediaHandling: "Evasive, Reserved",
      },
    );
    expect(squadHaEllipsisCellText(gilson, "name")).toBe("Santiago Contreras");
    expect(squadHaEllipsisCellText(gilson, "personality")).toBe(
      "Fairly Determined",
    );
    expect(squadHaEllipsisCellText(gilson, "mediaHandling")).toBe(
      "Evasive, Reserved",
    );
    expect(squadHaEllipsisCellTitle(gilson.name)).toBe("Santiago Contreras");
    expect(squadHaEllipsisCellTitle(gilson.personality)).toBe(
      "Fairly Determined",
    );
    expect(squadHaEllipsisCellTitle(gilson.mediaHandling)).toBe(
      "Evasive, Reserved",
    );
  });

  it("empty and — cells have no tooltip", () => {
    expect(squadHaEllipsisCellTitle(null)).toBe("");
    expect(squadHaEllipsisCellTitle(undefined)).toBe("");
    expect(squadHaEllipsisCellTitle("")).toBe("");
    expect(squadHaEllipsisCellTitle("   ")).toBe("");
    expect(squadHaEllipsisCellTitle("—")).toBe("");
  });

  it("tooltip only when the painted label is clipped", () => {
    expect(
      squadHaTextOverflows({ scrollWidth: 140, clientWidth: 80 }),
    ).toBe(true);
    expect(squadHaTextOverflows({ scrollWidth: 80, clientWidth: 80 })).toBe(
      false,
    );
    expect(squadHaTextOverflows({ scrollWidth: 81, clientWidth: 80 })).toBe(
      false,
    );
  });
});

