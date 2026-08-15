import { describe, expect, it } from "vitest";
import {
  parseRosterHash,
  rosterHashForView,
} from "../web/squad-route.ts";

describe("rosterHashForView", () => {
  it("writes Progress as #roster/progress", () => {
    expect(rosterHashForView("firstTeam", "attributes")).toBe(
      "#roster/progress",
    );
  });

  it("keeps Squad / Loans / Mentoring hashes", () => {
    expect(rosterHashForView("firstTeam", "personalities")).toBe("#roster");
    expect(rosterHashForView("loans", "personalities")).toBe("#roster/loans");
    expect(rosterHashForView("mentoring", "attributes")).toBe(
      "#roster/mentoring",
    );
  });
});

describe("parseRosterHash", () => {
  it("opens Progress from #roster/progress and legacy attributes hashes", () => {
    expect(parseRosterHash("roster/progress")).toEqual({
      squadView: "firstTeam",
      unitView: "attributes",
    });
    expect(parseRosterHash("#roster/attributes")).toEqual({
      squadView: "firstTeam",
      unitView: "attributes",
    });
    expect(parseRosterHash("roster/under19s/attributes")).toEqual({
      squadView: "firstTeam",
      unitView: "attributes",
    });
  });

  it("round-trips Progress on refresh", () => {
    const hash = rosterHashForView("firstTeam", "attributes");
    expect(parseRosterHash(hash)).toEqual({
      squadView: "firstTeam",
      unitView: "attributes",
    });
  });

  it("keeps Loans and Mentoring; legacy unit hashes land on Squad", () => {
    expect(parseRosterHash("roster")).toEqual({
      squadView: "firstTeam",
      unitView: "personalities",
    });
    expect(parseRosterHash("roster/loans")).toEqual({
      squadView: "loans",
      unitView: null,
    });
    expect(parseRosterHash("roster/mentoring")).toEqual({
      squadView: "mentoring",
      unitView: null,
    });
    expect(parseRosterHash("roster/reserves")).toEqual({
      squadView: "firstTeam",
      unitView: "personalities",
    });
  });
});
