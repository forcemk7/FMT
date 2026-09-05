import { describe, expect, it } from "vitest";
import {
  clearSquadDeskRosterFilters,
  getSquadDeskRosterFilters,
  getSquadDeskScrollTop,
  getSquadDeskSelectedTeamUid,
  setSquadDeskRosterFilters,
  setSquadDeskScrollTop,
  setSquadDeskSelectedTeamUid,
  stashSquadScroll,
  unfreezeSquadScroll,
} from "./squad-desk-session";

describe("squad-desk-session", () => {
  it("remembers selected team uid across remounts", () => {
    setSquadDeskSelectedTeamUid("team-u19");
    expect(getSquadDeskSelectedTeamUid()).toBe("team-u19");
    setSquadDeskSelectedTeamUid(null);
    expect(getSquadDeskSelectedTeamUid()).toBeNull();
  });

  it("remembers roster filters per team within the session", () => {
    clearSquadDeskRosterFilters();
    setSquadDeskRosterFilters("team-1", ["atClub", "loanedIn"]);
    expect(getSquadDeskRosterFilters("team-1")).toEqual(["atClub", "loanedIn"]);
    expect(getSquadDeskRosterFilters("team-2")).toBeNull();
    setSquadDeskRosterFilters("team-1", ["loanedOut"]);
    expect(getSquadDeskRosterFilters("team-1")).toEqual(["loanedOut"]);
    clearSquadDeskRosterFilters();
    expect(getSquadDeskRosterFilters("team-1")).toBeNull();
  });

  it("clamps invalid scroll to zero", () => {
    unfreezeSquadScroll();
    setSquadDeskScrollTop(420);
    expect(getSquadDeskScrollTop()).toBe(420);
    setSquadDeskScrollTop(Number.NaN);
    expect(getSquadDeskScrollTop()).toBe(0);
    setSquadDeskScrollTop(-10);
    expect(getSquadDeskScrollTop()).toBe(0);
  });

  it("freezes stash so later writes cannot clobber squad scroll", () => {
    unfreezeSquadScroll();
    setSquadDeskScrollTop(640);
    stashSquadScroll();
    setSquadDeskScrollTop(0);
    expect(getSquadDeskScrollTop()).toBe(640);
    unfreezeSquadScroll();
    setSquadDeskScrollTop(12);
    expect(getSquadDeskScrollTop()).toBe(12);
  });
});
