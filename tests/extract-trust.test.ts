import { describe, expect, it } from "vitest";
import {
  formatExtractTrustStatus,
  isMentoringCompleteEnough,
  isRosterNameResolved,
  mentoringAttrSignalCount,
  mentoringSuggestPool,
  playerExtractTrust,
  summarizeExtractTrust,
} from "../web/extract-trust.ts";
import type { RosterPlayer } from "../web/roster-data.ts";

function player(
  partial: Partial<RosterPlayer> & Pick<RosterPlayer, "uid" | "name">,
): RosterPlayer {
  return {
    jobId: 1,
    dateOfBirth: null,
    nation: null,
    secondNation: null,
    positions: null,
    dynamics: { captaincy: null, hierarchy: null, socialGroup: null },
    training: { unit: null },
    attributes: null,
    attributeHistory: null,
    loan: null,
    ...partial,
  };
}

const fullGeneral = {
  professionalism: 14,
  ambition: 12,
  loyalty: 11,
  sportsmanship: 10,
  controversy: 8,
  pressure: 13,
  temperament: 12,
};

describe("isRosterNameResolved", () => {
  it("rejects empty, uid:, and job: fallbacks", () => {
    expect(isRosterNameResolved("")).toBe(false);
    expect(isRosterNameResolved("   ")).toBe(false);
    expect(isRosterNameResolved("uid:2002282661")).toBe(false);
    expect(isRosterNameResolved("uid: 12")).toBe(false);
    expect(isRosterNameResolved("job:437615")).toBe(false);
  });

  it("accepts a real name", () => {
    expect(isRosterNameResolved("Landri Risse")).toBe(true);
  });
});

describe("mentoring attr bar", () => {
  it("needs 3 mentoring signals — two attrs is not done", () => {
    const short = player({
      uid: 1,
      name: "Short Attrs",
      attributes: {
        mental: { determination: 15, leadership: 8 },
        general: { professionalism: 14 },
      },
    });
    expect(mentoringAttrSignalCount(short)).toBe(2);
    expect(isMentoringCompleteEnough(short)).toBe(false);
    expect(playerExtractTrust(short).attrsEnough).toBe(false);
  });

  it("passes at 3 mentoring signals with a resolved name", () => {
    const ready = player({
      uid: 2,
      name: "Ready Kid",
      attributes: {
        mental: { determination: 14 },
        general: { professionalism: 12, ambition: 11 },
      },
    });
    expect(mentoringAttrSignalCount(ready)).toBe(3);
    expect(isMentoringCompleteEnough(ready)).toBe(true);
  });
});

describe("mentoringSuggestPool", () => {
  it("drops loanedOut, uid: names, and attr-short rows", () => {
    const ready = player({
      uid: 10,
      name: "At Club",
      attributes: {
        mental: { determination: 14 },
        general: fullGeneral,
      },
    });
    const loaned = player({
      uid: 11,
      name: "On Loan",
      attributes: {
        mental: { determination: 14 },
        general: fullGeneral,
      },
      loan: {
        status: "loanedOut",
        loanClubId: 904,
        parentClubId: 920,
        loanClubName: null,
        parentClubName: null,
      },
    });
    const nameless = player({
      uid: 12,
      name: "uid:2000000001",
      attributes: {
        mental: { determination: 14 },
        general: fullGeneral,
      },
    });
    const thin = player({
      uid: 13,
      name: "Thin Attrs",
      attributes: { mental: { determination: 18 } },
    });
    expect(mentoringSuggestPool([ready, loaned, nameless, thin]).map((p) => p.uid)).toEqual(
      [10],
    );
  });
});

describe("summarizeExtractTrust", () => {
  it("counts name / attrs / loan holes so complete cannot hide", () => {
    const summary = summarizeExtractTrust([
      player({
        uid: 1,
        name: "Named",
        attributes: {
          mental: { determination: 14 },
          general: fullGeneral,
        },
        loan: {
          status: "atClub",
          loanClubId: null,
          parentClubId: null,
          loanClubName: null,
          parentClubName: null,
        },
      }),
      player({ uid: 2, name: "uid:99" }),
      player({
        uid: 3,
        name: "No Loan Flag",
        attributes: {
          mental: { determination: 14 },
          general: fullGeneral,
        },
      }),
    ]);
    expect(summary.total).toBe(3);
    expect(summary.mentoringReady).toBe(2);
    expect(summary.extractComplete).toBe(1);
    expect(summary.missingName).toBe(1);
    expect(summary.attrsShort).toBe(1);
    expect(summary.loanUnknown).toBe(2);
    expect(formatExtractTrustStatus(summary)).toContain("2/3 mentoring-ready");
    expect(formatExtractTrustStatus(summary)).toContain("name missing");
    expect(formatExtractTrustStatus(summary)).toContain("loan unclassified");
  });
});
