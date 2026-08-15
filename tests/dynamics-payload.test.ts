import { describe, expect, it } from "vitest";
import { normalizeRosterPlayer, type PlayerDynamics } from "../web/roster-data.ts";

describe("extract dynamics payload (T002)", () => {
  it("accepts captaincy + social group + list-order rank; hierarchy may be null", () => {
    const dynamics: PlayerDynamics = {
      captaincy: "captain",
      hierarchy: null,
      socialGroup: "core",
      socialRank: 0,
    };
    const player = normalizeRosterPlayer({
      uid: 2000136577,
      name: "Paco Suárez",
      jobId: 106935,
      dynamics,
    });
    expect(player.dynamics).toEqual(dynamics);
    expect(player.dynamics?.hierarchy ?? null).toBeNull();
  });
});
