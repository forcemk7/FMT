import { describe, expect, it } from "vitest";
import {
  getSquadDeskScrollTop,
  getSquadDeskSelectedTeamUid,
  setSquadDeskScrollTop,
  setSquadDeskSelectedTeamUid,
} from "./squad-desk-session";

describe("squad-desk-session", () => {
  it("remembers selected team uid across remounts", () => {
    setSquadDeskSelectedTeamUid("team-u19");
    expect(getSquadDeskSelectedTeamUid()).toBe("team-u19");
    setSquadDeskSelectedTeamUid(null);
    expect(getSquadDeskSelectedTeamUid()).toBeNull();
  });

  it("clamps invalid scroll to zero", () => {
    setSquadDeskScrollTop(420);
    expect(getSquadDeskScrollTop()).toBe(420);
    setSquadDeskScrollTop(Number.NaN);
    expect(getSquadDeskScrollTop()).toBe(0);
    setSquadDeskScrollTop(-10);
    expect(getSquadDeskScrollTop()).toBe(0);
  });
});
