import { describe, expect, it } from "vitest";
import {
  buildMentoringPruneRosterIds,
  canPersistMentoringGroupsToStore,
  decideMentoringPrune,
  isMentoringRosterTrustworthyForPrune,
  loadMentoringStackFromStore,
  mentoringGroupWhyLine,
  normalizeMentoringGroupRecord,
  pruneMentoringGroupRecords,
  sampleMentoringGroup,
  type MentoringStackPersist,
} from "../web/mentoring-stack.ts";
import type { RosterPlayer } from "../web/roster-data.ts";

function player(
  uid: number,
  loanStatus?: "loanedOut",
): RosterPlayer {
  return {
    uid,
    name: `Player ${uid}`,
    kind: "REAL",
    source: "save",
    ...(loanStatus
      ? {
          loan: {
            status: loanStatus,
            loanClubId: 1,
            parentClubId: null,
            loanClubName: "Loan FC",
            parentClubName: null,
          },
        }
      : { loan: null }),
  } as RosterPlayer;
}

const groupA = sampleMentoringGroup("g1", ["101", "102", "103"]);
const groupB = sampleMentoringGroup("g2", ["201", "202", "203"]);

describe("loadMentoringStackFromStore (T026)", () => {
  it("migrates from legacy compound key when direct key has empty groups", () => {
    const store: MentoringStackPersist = {
      "Schalke.fm": {
        groups: [],
        dynamicsByPlayerId: {},
        rejectedGroupKeys: [],
      },
      "Schalke.fm|2026-08-01|2026-08-01T00:00:00.000Z|25|11": {
        groups: [groupA, groupB],
        dynamicsByPlayerId: {
          "101": {
            captaincy: "captain",
            hierarchy: "teamLeader",
            socialGroup: "core",
          },
        },
        rejectedGroupKeys: ["101|102|103"],
      },
    };

    const loaded = loadMentoringStackFromStore(store, "Schalke.fm");
    expect(loaded.groups).toHaveLength(2);
    expect(loaded.groups[0]?.id).toBe("g1");
    expect(loaded.dynamicsByPlayerId["101"]?.captaincy).toBe("captain");
    expect(loaded.rejectedGroupKeys).toEqual(["101|102|103"]);
  });

  it("prefers non-empty direct key over legacy rows", () => {
    const directGroup = sampleMentoringGroup("direct", ["301", "302", "303"]);
    const store: MentoringStackPersist = {
      "Schalke.fm": { groups: [directGroup] },
      "Schalke.fm|old|session|25|11": { groups: [groupA] },
    };
    const loaded = loadMentoringStackFromStore(store, "Schalke.fm");
    expect(loaded.groups).toHaveLength(1);
    expect(loaded.groups[0]?.id).toBe("direct");
  });
});

describe("decideMentoringPrune (T026)", () => {
  it("keeps groups when roster UIDs still match after extract refresh", () => {
    const rosterIds = new Set(["101", "102", "103", "201", "202", "203"]);
    const decision = decideMentoringPrune([groupA, groupB], rosterIds, true);
    expect(decision.applied).toBe(false);
    expect(decision.groups).toHaveLength(2);
  });

  it("prunes a departed member but keeps surviving groups", () => {
    const rosterIds = new Set(["101", "102", "103", "201", "202"]);
    const decision = decideMentoringPrune([groupA, groupB], rosterIds, true);
    expect(decision.applied).toBe(true);
    expect(decision.groups).toHaveLength(1);
    expect(decision.groups[0]?.id).toBe("g1");
  });

  it("fail-closed when prune would delete every group", () => {
    const rosterIds = new Set(["999", "998", "997"]);
    const decision = decideMentoringPrune([groupA, groupB], rosterIds, true);
    expect(decision.applied).toBe(false);
    expect(decision.skippedReason).toBe("would_wipe_all");
    expect(decision.groups).toHaveLength(2);
  });

  it("skips prune on incomplete roster (empty club list)", () => {
    const decision = decideMentoringPrune([groupA], new Set(), false);
    expect(decision.applied).toBe(false);
    expect(decision.skippedReason).toBe("incomplete_roster");
    expect(decision.groups).toHaveLength(1);
  });
});

describe("isMentoringRosterTrustworthyForPrune", () => {
  it("rejects empty club roster and tiny FT headcount", () => {
    expect(isMentoringRosterTrustworthyForPrune([], [player(1)])).toBe(false);
    expect(isMentoringRosterTrustworthyForPrune([player(1)], [])).toBe(false);
    expect(
      isMentoringRosterTrustworthyForPrune(
        [player(1), player(2)],
        [player(1), player(2)],
      ),
    ).toBe(false);
    expect(
      isMentoringRosterTrustworthyForPrune(
        [player(1), player(2), player(3)],
        [player(1), player(2), player(3)],
      ),
    ).toBe(true);
  });
});

describe("buildMentoringPruneRosterIds", () => {
  it("excludes loaned-out club employees from prune roster ids", () => {
    const ids = buildMentoringPruneRosterIds([
      player(1),
      player(2, "loanedOut"),
      player(3),
    ]);
    expect([...ids].sort()).toEqual(["1", "3"]);
  });
});

describe("canPersistMentoringGroupsToStore", () => {
  it("blocks persisting empty groups over a non-empty saved stack", () => {
    const store: MentoringStackPersist = {
      "Schalke.fm": { groups: [groupA] },
    };
    expect(canPersistMentoringGroupsToStore([], store, "Schalke.fm")).toBe(
      false,
    );
    expect(canPersistMentoringGroupsToStore([groupB], store, "Schalke.fm")).toBe(
      true,
    );
  });
});

describe("pruneMentoringGroupRecords", () => {
  it("drops groups with fewer than three roster members", () => {
    const rosterIds = new Set(["101", "102"]);
    const { groups, changed } = pruneMentoringGroupRecords([groupA], rosterIds);
    expect(changed).toBe(true);
    expect(groups).toHaveLength(0);
  });

  it("keeps Suggest reasons on surviving groups", () => {
    const saved = {
      ...groupA,
      reasons: ["Strong A + Strong B overload Weak Kid", "Det lift"],
    };
    const { groups } = pruneMentoringGroupRecords(
      [saved],
      new Set(["101", "102", "103"]),
    );
    expect(groups[0]?.reasons?.[0]).toMatch(/overload/i);
  });
});

describe("mentoring group why (T031)", () => {
  it("persists Suggest reasons and omits manual why", () => {
    const suggested = normalizeMentoringGroupRecord({
      ...groupA,
      reasons: ["Strong A + Strong B overload Weak Kid", "Det lift"],
    });
    expect(suggested?.reasons).toEqual([
      "Strong A + Strong B overload Weak Kid",
      "Det lift",
    ]);
    expect(mentoringGroupWhyLine(suggested?.reasons)).toMatch(/overload/i);
    expect(normalizeMentoringGroupRecord(groupA)?.reasons).toBeUndefined();
    expect(mentoringGroupWhyLine(undefined)).toBeNull();
    expect(mentoringGroupWhyLine([])).toBeNull();
  });
});
