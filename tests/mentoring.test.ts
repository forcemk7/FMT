import { describe, expect, it } from "vitest";
import {
  defaultMentoringUnitRoles,
  evaluateMentoringUnit,
  findInfluenceSafeMentoringGroups,
  findMentoringGroupsForSubject,
  isMentoringInfluenceSubject,
  isMentoringZeroInfluenceGroup,
  MENTORING_DISPLAY_ORDER,
  mentoringFocus,
  mentoringGroupMemberKey,
  mentoringInfluenceEdgeKey,
  mentoringLabeledDisplayInfluence,
  mentoringMenteeAttributeEvidence,
  mentoringMenteeCoverage,
  mentoringMenteeFaceState,
  mentoringReplacementForLow,
  formatMentoringCaPa,
  mentoringCaPaFaceDigits,
  mentoringChevronCount,
  mentoringRolesHaveLabeledDownwardNone,
  mentoringRole,
  mentoringTraitWeight,
  menteePathUnderMentor,
  passesMentoringSuggestGate,
  planMentoringMatrixCellMarks,
  planMentoringSeatPeerMarks,
  planMentoringPairTraitMarks,
  resolveMentoringInfluenceLevel,
  scoreSafeInfluence,
  violatesHaInfluenceSeating,
  type MentoringInfluenceSafeGroup,
  type MentoringUnitMember,
} from "../src/inference/mentoring.ts";

describe("mentoring role + focus", () => {
  it("classifies role by age", () => {
    expect(mentoringRole(18)).toBe("mentee");
    expect(mentoringRole(23)).toBe("mentee");
    expect(mentoringRole(24)).toBe("mentor");
    expect(mentoringRole(undefined)).toBe("unknown");
  });

  it("lists weak traits as focus", () => {
    const focus = mentoringFocus({
      age: 18,
      determination: 12,
      professionalism: 8,
      ambition: 14,
      loyalty: 15,
      sportsmanship: 14,
      controversy: 12,
      pressure: 14,
      temperament: 14,
      bands: {
        determination: { min: 12, max: 12, midpoint: 12 },
        professionalism: { min: 6, max: 10, midpoint: 8 },
        ambition: { min: 12, max: 16, midpoint: 14 },
        loyalty: { min: 13, max: 17, midpoint: 15 },
        sportsmanship: { min: 12, max: 16, midpoint: 14 },
        controversy: { min: 10, max: 14, midpoint: 12 },
        pressure: { min: 12, max: 16, midpoint: 14 },
        temperament: { min: 12, max: 16, midpoint: 14 },
      },
    });
    expect(focus.some((f) => f.trait === "professionalism")).toBe(true);
    expect(focus.some((f) => f.trait === "loyalty")).toBe(false);
  });
});

describe("menteePathUnderMentor", () => {
  it("returns null, specialize, or balance for a labeled mentor combo", () => {
    const path = menteePathUnderMentor(
      {
        id: "kid",
        name: "Prospect",
        age: 17,
        determination: 14,
        professionalism: 13,
        ambition: 12,
        loyalty: 8,
        sportsmanship: 14,
        controversy: 6,
        pressure: 13,
        temperament: 13,
        haScore: 10.8,
        bands: {
          determination: { min: 14, max: 14, midpoint: 14 },
          professionalism: { min: 11, max: 15, midpoint: 13 },
          ambition: { min: 10, max: 14, midpoint: 12 },
          loyalty: { min: 6, max: 10, midpoint: 8 },
          sportsmanship: { min: 12, max: 16, midpoint: 14 },
          controversy: { min: 4, max: 8, midpoint: 6 },
          pressure: { min: 11, max: 15, midpoint: 13 },
          temperament: { min: 11, max: 15, midpoint: 13 },
        },
      },
      {
        id: "mentor",
        name: "Mentor",
        age: 28,
        determination: 17,
        leadership: 15,
        professionalism: 16,
        ambition: 14,
        loyalty: 14,
        sportsmanship: 14,
        controversy: 5,
        pressure: 15,
        temperament: 15,
        haScore: 14,
        personality: "Model Citizen",
        mediaHandling: "Media-friendly",
        bands: {
          determination: { min: 17, max: 17, midpoint: 17 },
          professionalism: { min: 16, max: 16, midpoint: 16 },
          ambition: { min: 14, max: 14, midpoint: 14 },
          loyalty: { min: 14, max: 14, midpoint: 14 },
          sportsmanship: { min: 14, max: 14, midpoint: 14 },
          controversy: { min: 5, max: 5, midpoint: 5 },
          pressure: { min: 15, max: 15, midpoint: 15 },
          temperament: { min: 15, max: 15, midpoint: 15 },
        },
      },
    );
    expect(
      path === null || path === "specialize" || path === "balance",
    ).toBe(true);
  });
});

describe("findMentoringGroupsForSubject", () => {
  const seniorA = {
    id: "senior-a",
    name: "Senior A",
    age: 28,
    determination: 17,
    leadership: 15,
    professionalism: 16,
    ambition: 14,
    loyalty: 14,
    sportsmanship: 14,
    controversy: 5,
    pressure: 15,
    temperament: 15,
    haScore: 14,
    personality: "Model Citizen",
    mediaHandling: "Media-friendly",
    bands: {
      determination: { min: 17, max: 17, midpoint: 17 },
      professionalism: { min: 16, max: 16, midpoint: 16 },
      ambition: { min: 14, max: 14, midpoint: 14 },
      loyalty: { min: 14, max: 14, midpoint: 14 },
      sportsmanship: { min: 14, max: 14, midpoint: 14 },
      controversy: { min: 5, max: 5, midpoint: 5 },
      pressure: { min: 15, max: 15, midpoint: 15 },
      temperament: { min: 15, max: 15, midpoint: 15 },
    },
  };
  const seniorB = {
    ...seniorA,
    id: "senior-b",
    name: "Senior B",
    age: 30,
    leadership: 16,
  };
  const junior = {
    id: "junior",
    name: "Junior",
    age: 20,
    determination: 11,
    leadership: 8,
    professionalism: 10,
    ambition: 11,
    loyalty: 10,
    sportsmanship: 12,
    controversy: 8,
    pressure: 11,
    temperament: 12,
    haScore: 10,
    personality: "Balanced",
    mediaHandling: "Level-headed",
    bands: {
      determination: { min: 11, max: 11, midpoint: 11 },
      professionalism: { min: 10, max: 10, midpoint: 10 },
      ambition: { min: 11, max: 11, midpoint: 11 },
      loyalty: { min: 10, max: 10, midpoint: 10 },
      sportsmanship: { min: 12, max: 12, midpoint: 12 },
      controversy: { min: 8, max: 8, midpoint: 8 },
      pressure: { min: 11, max: 11, midpoint: 11 },
      temperament: { min: 12, max: 12, midpoint: 12 },
    },
  };
  const junior2 = {
    ...junior,
    id: "junior-2",
    name: "Junior Two",
    age: 19,
  };

  it("lists under-24 players as influence subjects", () => {
    expect(isMentoringInfluenceSubject(junior)).toBe(true);
    expect(isMentoringInfluenceSubject(seniorA)).toBe(false);
    expect(isMentoringInfluenceSubject({ ...junior, age: undefined })).toBe(
      false,
    );
  });

  it("suggests 2+1 and 1+2 groups around a young subject", () => {
    const groups = findMentoringGroupsForSubject(junior, [
      seniorA,
      seniorB,
      junior,
      junior2,
    ]);
    expect(groups.some((g) => g.shape === "two_mentors")).toBe(true);
    expect(groups.some((g) => g.shape === "two_mentees")).toBe(true);
    const duoMentors = groups.filter((g) => g.shape === "two_mentors");
    const duoMentees = groups.filter((g) => g.shape === "two_mentees");
    expect(duoMentors.length).toBeLessThanOrEqual(2);
    expect(duoMentees.length).toBeLessThanOrEqual(2);
    expect(duoMentors[0]?.mentors).toHaveLength(2);
    expect(duoMentors[0]?.mentees).toEqual([junior]);
    expect(duoMentees[0]?.mentors).toHaveLength(1);
    expect(duoMentees[0]?.mentees).toHaveLength(2);
    expect(duoMentees[0]?.mentees.map((m) => m.id).sort()).toEqual([
      "junior",
      "junior-2",
    ]);
    // Why lines should lead with trait lifts, not HA.
    for (const group of groups) {
      expect(group.reasons.length).toBeGreaterThan(0);
      expect(group.reasons.some((r) => /\blifts\b/i.test(r))).toBe(true);
      expect(group.reasons.every((r) => !/^[^:]+: HA /.test(r))).toBe(true);
    }
  });

  it("still forms groups when mentor ages are missing", () => {
    const seniorNoAge = { ...seniorA, age: undefined };
    const seniorBNoAge = { ...seniorB, age: undefined };
    const groups = findMentoringGroupsForSubject(junior, [
      seniorNoAge,
      seniorBNoAge,
      junior,
      junior2,
    ]);
    expect(groups.length).toBeGreaterThan(0);
    expect(
      groups.every(
        (g) =>
          g.path === "specialize" ||
          g.path === "balance" ||
          g.path === "avoid",
      ),
    ).toBe(true);
  });

  it("still forms groups for high-HA subjects with several polish traits", () => {
    const driven = {
      ...junior,
      id: "driven",
      name: "Driven Kid",
      age: 17,
      determination: 16,
      professionalism: 15,
      ambition: 15,
      loyalty: 11,
      sportsmanship: 11,
      controversy: 8,
      pressure: 11,
      temperament: 11,
      haScore: 14,
      personality: "Driven",
      mediaHandling: "Level-Headed",
      bands: {
        determination: { min: 16, max: 16, midpoint: 16 },
        professionalism: { min: 15, max: 15, midpoint: 15 },
        ambition: { min: 15, max: 15, midpoint: 15 },
        loyalty: { min: 11, max: 11, midpoint: 11 },
        sportsmanship: { min: 11, max: 11, midpoint: 11 },
        controversy: { min: 8, max: 8, midpoint: 8 },
        pressure: { min: 11, max: 11, midpoint: 11 },
        temperament: { min: 11, max: 11, midpoint: 11 },
      },
    };
    const groups = findMentoringGroupsForSubject(driven, [
      seniorA,
      seniorB,
      driven,
      junior2,
    ]);
    expect(groups.length).toBeGreaterThan(0);
    expect(groups.some((g) => g.shape === "two_mentors")).toBe(true);
  });
});

describe("mentoringMenteeAttributeEvidence", () => {
  it("shows positive deltas where mentors outscore the mentee", () => {
    const mentee = {
      id: "kid",
      name: "Kid",
      professionalism: 10,
      ambition: 11,
      controversy: 9,
      bands: {
        professionalism: { min: 10, max: 10, midpoint: 10 },
        ambition: { min: 11, max: 11, midpoint: 11 },
        controversy: { min: 9, max: 9, midpoint: 9 },
      },
    };
    const mentor = {
      id: "vet",
      name: "Vet",
      professionalism: 16,
      ambition: 14,
      controversy: 4,
      bands: {
        professionalism: { min: 16, max: 16, midpoint: 16 },
        ambition: { min: 14, max: 14, midpoint: 14 },
        controversy: { min: 4, max: 4, midpoint: 4 },
      },
    };
    const rows = mentoringMenteeAttributeEvidence(mentee, [mentor]);
    const pro = rows.find((r) => r.trait === "professionalism");
    const con = rows.find((r) => r.trait === "controversy");
    expect(pro?.value).toBe(10);
    expect(pro?.delta).toBe(6);
    expect(con?.delta).toBe(5);
  });
});

describe("mentoring display order + weighted scoring", () => {
  it("follows checker / HAS rank column order (minus Leadership)", () => {
    expect([...MENTORING_DISPLAY_ORDER]).toEqual([
      "determination",
      "professionalism",
      "pressure",
      "ambition",
      "temperament",
      "loyalty",
      "sportsmanship",
      "controversy",
    ]);
    expect(mentoringTraitWeight("professionalism")).toBeGreaterThan(
      mentoringTraitWeight("sportsmanship"),
    );
  });

  it("rejects mentors that trash Pro for a Spo polish", () => {
    const junior = {
      id: "junior",
      name: "Junior",
      age: 20,
      determination: 11,
      leadership: 8,
      professionalism: 16,
      ambition: 11,
      loyalty: 10,
      sportsmanship: 8,
      controversy: 8,
      pressure: 11,
      temperament: 12,
      haScore: 11,
      personality: "Balanced",
      mediaHandling: "Level-headed",
      bands: {
        determination: { min: 11, max: 11, midpoint: 11 },
        professionalism: { min: 16, max: 16, midpoint: 16 },
        ambition: { min: 11, max: 11, midpoint: 11 },
        loyalty: { min: 10, max: 10, midpoint: 10 },
        sportsmanship: { min: 8, max: 8, midpoint: 8 },
        controversy: { min: 8, max: 8, midpoint: 8 },
        pressure: { min: 11, max: 11, midpoint: 11 },
        temperament: { min: 12, max: 12, midpoint: 12 },
      },
    };
    const badMentor = {
      id: "bad-mentor",
      name: "Bad Mentor",
      age: 28,
      determination: 12,
      leadership: 12,
      professionalism: 6,
      ambition: 12,
      loyalty: 12,
      sportsmanship: 18,
      controversy: 8,
      pressure: 12,
      temperament: 12,
      haScore: 10,
      personality: "Spirited",
      mediaHandling: "Media-friendly",
      bands: {
        determination: { min: 12, max: 12, midpoint: 12 },
        professionalism: { min: 6, max: 6, midpoint: 6 },
        ambition: { min: 12, max: 12, midpoint: 12 },
        loyalty: { min: 12, max: 12, midpoint: 12 },
        sportsmanship: { min: 18, max: 18, midpoint: 18 },
        controversy: { min: 8, max: 8, midpoint: 8 },
        pressure: { min: 12, max: 12, midpoint: 12 },
        temperament: { min: 12, max: 12, midpoint: 12 },
      },
    };
    const goodMentor = {
      ...badMentor,
      id: "good-mentor",
      name: "Good Mentor",
      professionalism: 18,
      sportsmanship: 14,
      haScore: 14,
      bands: {
        ...badMentor.bands,
        professionalism: { min: 18, max: 18, midpoint: 18 },
        sportsmanship: { min: 14, max: 14, midpoint: 14 },
      },
    };
    const goodMentorB = {
      ...goodMentor,
      id: "good-mentor-b",
      name: "Good Mentor B",
      age: 30,
    };
    const groups = findMentoringGroupsForSubject(junior, [
      badMentor,
      goodMentor,
      goodMentorB,
      junior,
    ]);
    const mentorIds = new Set(
      groups.flatMap((g) => g.mentors.map((m) => m.id)),
    );
    expect(mentorIds.has("bad-mentor")).toBe(false);
    expect(mentorIds.has("good-mentor") || mentorIds.has("good-mentor-b")).toBe(
      true,
    );
  });
});

describe("evaluateMentoringUnit", () => {
  const senior = {
    id: "senior",
    name: "Senior",
    age: 29,
    determination: 17,
    leadership: 15,
    professionalism: 16,
    ambition: 14,
    loyalty: 14,
    sportsmanship: 14,
    controversy: 5,
    pressure: 15,
    temperament: 15,
    haScore: 14,
    personality: "Model Citizen",
    mediaHandling: "Media-friendly",
    bands: {
      determination: { min: 17, max: 17, midpoint: 17 },
      professionalism: { min: 16, max: 16, midpoint: 16 },
      ambition: { min: 14, max: 14, midpoint: 14 },
      loyalty: { min: 14, max: 14, midpoint: 14 },
      sportsmanship: { min: 14, max: 14, midpoint: 14 },
      controversy: { min: 5, max: 5, midpoint: 5 },
      pressure: { min: 15, max: 15, midpoint: 15 },
      temperament: { min: 15, max: 15, midpoint: 15 },
    },
  };
  const peer = {
    ...senior,
    id: "peer",
    name: "Peer",
    age: 27,
    leadership: 14,
  };
  const kid = {
    id: "kid",
    name: "Kid",
    age: 19,
    determination: 11,
    leadership: 8,
    professionalism: 10,
    ambition: 11,
    loyalty: 10,
    sportsmanship: 12,
    controversy: 8,
    pressure: 11,
    temperament: 12,
    haScore: 10,
    personality: "Balanced",
    mediaHandling: "Level-headed",
    bands: {
      determination: { min: 11, max: 11, midpoint: 11 },
      professionalism: { min: 10, max: 10, midpoint: 10 },
      ambition: { min: 11, max: 11, midpoint: 11 },
      loyalty: { min: 10, max: 10, midpoint: 10 },
      sportsmanship: { min: 12, max: 12, midpoint: 12 },
      controversy: { min: 8, max: 8, midpoint: 8 },
      pressure: { min: 11, max: 11, midpoint: 11 },
      temperament: { min: 12, max: 12, midpoint: 12 },
    },
  };

  it("defaults seats by influence rank with the kid as Low", () => {
    const seats = defaultMentoringUnitRoles([kid, senior, peer]);
    expect(seats.find((s) => s.role === "low")?.player.id).toBe("kid");
    expect(seats.map((s) => s.role).sort()).toEqual(["high", "low", "mid"]);
  });

  it("scores an overload unit on High→Mid / High→Low / Mid→Low", () => {
    const evaluation = evaluateMentoringUnit([
      { player: senior, role: "high" },
      { player: peer, role: "mid" },
      { player: kid, role: "low" },
    ]);
    expect(evaluation.shape).toBe("overload");
    expect(evaluation.directed.some((e) => e.level !== "none")).toBe(true);
  });
});

describe("findInfluenceSafeMentoringGroups", () => {
  const strongA = {
    id: "strong-a",
    name: "Strong A",
    age: 30,
    determination: 18,
    leadership: 16,
    professionalism: 17,
    ambition: 14,
    loyalty: 15,
    sportsmanship: 14,
    controversy: 5,
    pressure: 15,
    temperament: 15,
    haScore: 15,
    personality: "Model Citizen",
    mediaHandling: "Media-friendly",
    bands: {
      determination: { min: 18, max: 18, midpoint: 18 },
      professionalism: { min: 17, max: 17, midpoint: 17 },
      ambition: { min: 14, max: 14, midpoint: 14 },
      loyalty: { min: 15, max: 15, midpoint: 15 },
      sportsmanship: { min: 14, max: 14, midpoint: 14 },
      controversy: { min: 5, max: 5, midpoint: 5 },
      pressure: { min: 15, max: 15, midpoint: 15 },
      temperament: { min: 15, max: 15, midpoint: 15 },
    },
  };
  const strongB = {
    ...strongA,
    id: "strong-b",
    name: "Strong B",
    age: 28,
    leadership: 15,
    determination: 17,
    bands: {
      ...strongA.bands,
      determination: { min: 17, max: 17, midpoint: 17 },
    },
  };
  const midDrag = {
    id: "lundqvist",
    name: "Lundqvist",
    age: 24,
    determination: 10,
    leadership: 12,
    professionalism: 9,
    ambition: 12,
    loyalty: 11,
    sportsmanship: 10,
    controversy: 10,
    pressure: 11,
    temperament: 11,
    haScore: 10,
    personality: "Balanced",
    mediaHandling: "Level-headed",
    bands: {
      determination: { min: 10, max: 10, midpoint: 10 },
      professionalism: { min: 9, max: 9, midpoint: 9 },
      ambition: { min: 12, max: 12, midpoint: 12 },
      loyalty: { min: 11, max: 11, midpoint: 11 },
      sportsmanship: { min: 10, max: 10, midpoint: 10 },
      controversy: { min: 10, max: 10, midpoint: 10 },
      pressure: { min: 11, max: 11, midpoint: 11 },
      temperament: { min: 11, max: 11, midpoint: 11 },
    },
  };
  const goodKid = {
    id: "lawal",
    name: "Lawal",
    age: 18,
    determination: 14,
    leadership: 7,
    professionalism: 13,
    ambition: 12,
    loyalty: 12,
    sportsmanship: 12,
    controversy: 7,
    pressure: 12,
    temperament: 13,
    haScore: 12,
    personality: "Professional",
    mediaHandling: "Level-headed",
    bands: {
      determination: { min: 14, max: 14, midpoint: 14 },
      professionalism: { min: 13, max: 13, midpoint: 13 },
      ambition: { min: 12, max: 12, midpoint: 12 },
      loyalty: { min: 12, max: 12, midpoint: 12 },
      sportsmanship: { min: 12, max: 12, midpoint: 12 },
      controversy: { min: 7, max: 7, midpoint: 7 },
      pressure: { min: 12, max: 12, midpoint: 12 },
      temperament: { min: 13, max: 13, midpoint: 13 },
    },
  };
  const weakKid = {
    id: "weak-kid",
    name: "Weak Kid",
    age: 19,
    determination: 10,
    leadership: 6,
    professionalism: 9,
    ambition: 10,
    loyalty: 10,
    sportsmanship: 11,
    controversy: 9,
    pressure: 10,
    temperament: 11,
    haScore: 10,
    personality: "Balanced",
    mediaHandling: "Level-headed",
    bands: {
      determination: { min: 10, max: 10, midpoint: 10 },
      professionalism: { min: 9, max: 9, midpoint: 9 },
      ambition: { min: 10, max: 10, midpoint: 10 },
      loyalty: { min: 10, max: 10, midpoint: 10 },
      sportsmanship: { min: 11, max: 11, midpoint: 11 },
      controversy: { min: 9, max: 9, midpoint: 9 },
      pressure: { min: 10, max: 10, midpoint: 10 },
      temperament: { min: 11, max: 11, midpoint: 11 },
    },
  };

  it("rejects Mid→Low when mid would Det-drag a better kid", () => {
    expect(scoreSafeInfluence(midDrag, goodKid)).toBeNull();
    const groups = findInfluenceSafeMentoringGroups([
      strongA,
      midDrag,
      goodKid,
    ]);
    const bad = groups.find((g) =>
      g.members.some((m) => m.player.id === "lundqvist") &&
      g.members.some((m) => m.player.id === "lawal"),
    );
    expect(bad).toBeUndefined();
  });

  it("suggests overload for two strong seniors over a weaker youngling", () => {
    const groups = findInfluenceSafeMentoringGroups([
      strongA,
      strongB,
      weakKid,
    ]);
    const overload = groups.find((g) => g.shape === "overload");
    expect(overload).toBeTruthy();
    expect(overload!.members.find((m) => m.role === "low")?.player.id).toBe(
      "weak-kid",
    );
    expect(overload!.reasons.some((row) => /overload/i.test(row))).toBe(true);
  });

  it("tie-breaks equal overload groups toward the higher-PA Low", () => {
    const highPa = { ...weakKid, id: "high-pa", name: "High PA", pa: 170 };
    const lowPa = { ...weakKid, id: "low-pa", name: "Low PA", pa: 120 };
    const groups = findInfluenceSafeMentoringGroups([
      strongA,
      strongB,
      highPa,
      lowPa,
    ]);
    const overloads = groups.filter((g) => g.shape === "overload");
    expect(overloads.length).toBeGreaterThanOrEqual(2);
    const topScore = overloads[0]!.score;
    const tied = overloads.filter((g) => g.score === topScore);
    expect(tied[0]!.members.find((m) => m.role === "low")?.player.id).toBe(
      "high-pa",
    );
  });

  it("does not crash Suggest when Low PA is missing", () => {
    expect(() =>
      findInfluenceSafeMentoringGroups([strongA, strongB, weakKid]),
    ).not.toThrow();
    expect(() =>
      findInfluenceSafeMentoringGroups([
        strongA,
        strongB,
        { ...weakKid, id: "junk-pa", pa: -1 },
      ]),
    ).not.toThrow();
    const groups = findInfluenceSafeMentoringGroups([
      strongA,
      strongB,
      { ...weakKid, id: "nan-pa", pa: Number.NaN },
    ]);
    expect(Array.isArray(groups)).toBe(true);
  });

  it("requires Mid→Low for cascade suggestions", () => {
    const midSafe = {
      ...midDrag,
      id: "mid-safe",
      name: "Mid Safe",
      determination: 15,
      professionalism: 14,
      leadership: 13,
      controversy: 6,
      bands: {
        ...midDrag.bands,
        determination: { min: 15, max: 15, midpoint: 15 },
        professionalism: { min: 14, max: 14, midpoint: 14 },
        controversy: { min: 6, max: 6, midpoint: 6 },
      },
    };
    const groups = findInfluenceSafeMentoringGroups([
      strongA,
      midSafe,
      weakKid,
    ]);
    for (const group of groups) {
      const mid = group.members.find((m) => m.role === "mid")!.player;
      const low = group.members.find((m) => m.role === "low")!.player;
      expect(scoreSafeInfluence(mid, low)).not.toBeNull();
    }
  });

  it("allows tertiary drag when primary-tier lifts are strong", () => {
    const kid = {
      id: "kid-balanced",
      name: "Kid Balanced",
      age: 18,
      determination: 12,
      leadership: 8,
      professionalism: 10,
      ambition: 11,
      loyalty: 14,
      sportsmanship: 14,
      controversy: 8,
      pressure: 11,
      temperament: 13,
      haScore: 11,
      personality: "Balanced",
      mediaHandling: "Level-headed",
      bands: {
        determination: { min: 12, max: 12, midpoint: 12 },
        professionalism: { min: 10, max: 10, midpoint: 10 },
        ambition: { min: 11, max: 11, midpoint: 11 },
        loyalty: { min: 14, max: 14, midpoint: 14 },
        sportsmanship: { min: 14, max: 14, midpoint: 14 },
        controversy: { min: 8, max: 8, midpoint: 8 },
        pressure: { min: 11, max: 11, midpoint: 11 },
        temperament: { min: 13, max: 13, midpoint: 13 },
      },
    };
    const senior = {
      id: "senior-pro",
      name: "Senior Pro",
      age: 30,
      determination: 16,
      leadership: 15,
      professionalism: 18,
      ambition: 12,
      loyalty: 8,
      sportsmanship: 7,
      controversy: 4,
      pressure: 16,
      temperament: 9,
      haScore: 14,
      personality: "Model Citizen",
      mediaHandling: "Media-friendly",
      bands: {
        determination: { min: 16, max: 16, midpoint: 16 },
        professionalism: { min: 18, max: 18, midpoint: 18 },
        ambition: { min: 12, max: 12, midpoint: 12 },
        loyalty: { min: 8, max: 8, midpoint: 8 },
        sportsmanship: { min: 7, max: 7, midpoint: 7 },
        controversy: { min: 4, max: 4, midpoint: 4 },
        pressure: { min: 16, max: 16, midpoint: 16 },
        temperament: { min: 9, max: 9, midpoint: 9 },
      },
    };
    const edge = scoreSafeInfluence(senior, kid);
    expect(edge).not.toBeNull();
    expect(edge!.weightedHarm).toBeGreaterThan(0);
    expect(edge!.lifts.some((l) => /pro|det|pre|con/i.test(l))).toBe(true);
  });
});

describe("T025 suggest gate — manual influence + bans", () => {
  const strongSenior = {
    id: "senior",
    name: "Senior",
    age: 30,
    determination: 17,
    leadership: 16,
    professionalism: 16,
    ambition: 14,
    loyalty: 14,
    sportsmanship: 14,
    controversy: 5,
    pressure: 15,
    temperament: 15,
    haScore: 14,
    bands: {
      determination: { min: 17, max: 17, midpoint: 17 },
      professionalism: { min: 16, max: 16, midpoint: 16 },
      ambition: { min: 14, max: 14, midpoint: 14 },
      loyalty: { min: 14, max: 14, midpoint: 14 },
      sportsmanship: { min: 14, max: 14, midpoint: 14 },
      controversy: { min: 5, max: 5, midpoint: 5 },
      pressure: { min: 15, max: 15, midpoint: 15 },
      temperament: { min: 15, max: 15, midpoint: 15 },
    },
  };
  const peerSenior = {
    ...strongSenior,
    id: "peer",
    name: "Peer",
    age: 28,
    leadership: 14,
  };
  const weakYoung = {
    id: "weak",
    name: "Weak Kid",
    age: 19,
    determination: 10,
    leadership: 6,
    professionalism: 9,
    ambition: 10,
    loyalty: 10,
    sportsmanship: 11,
    controversy: 9,
    pressure: 10,
    temperament: 11,
    haScore: 9,
    bands: {
      determination: { min: 10, max: 10, midpoint: 10 },
      professionalism: { min: 9, max: 9, midpoint: 9 },
      ambition: { min: 10, max: 10, midpoint: 10 },
      loyalty: { min: 10, max: 10, midpoint: 10 },
      sportsmanship: { min: 11, max: 11, midpoint: 11 },
      controversy: { min: 9, max: 9, midpoint: 9 },
      pressure: { min: 10, max: 10, midpoint: 10 },
      temperament: { min: 11, max: 11, midpoint: 11 },
    },
  };
  const giftedYoung = {
    ...weakYoung,
    id: "gifted",
    name: "Gifted Kid",
    haScore: 13,
    professionalism: 15,
    determination: 14,
    bands: {
      ...weakYoung.bands,
      professionalism: { min: 15, max: 15, midpoint: 15 },
      determination: { min: 14, max: 14, midpoint: 14 },
    },
  };

  function overloadGroup(
    high: typeof strongSenior,
    mid: typeof strongSenior,
    low: typeof weakYoung,
  ): MentoringInfluenceSafeGroup {
    return {
      shape: "overload",
      members: [
        { player: high, role: "high" },
        { player: mid, role: "mid" },
        { player: low, role: "low" },
      ],
      subject: low,
      score: 40,
      path: "balance",
      edges: [],
      reasons: [],
    };
  }

  it("bans zero-influence triangles when manual edges are all none", () => {
    const group = overloadGroup(strongSenior, peerSenior, weakYoung);
    const edges = new Map([
      [
        mentoringInfluenceEdgeKey("senior", "weak"),
        "none" as const,
      ],
      [mentoringInfluenceEdgeKey("peer", "weak"), "none" as const],
    ]);
    expect(isMentoringZeroInfluenceGroup(group.members, edges)).toBe(true);
    expect(passesMentoringSuggestGate(group, { manualInfluenceEdges: edges })).toBe(
      false,
    );
    const key = mentoringGroupMemberKey(["senior", "peer", "weak"]);
    expect(
      findInfluenceSafeMentoringGroups([strongSenior, peerSenior, weakYoung], {
        manualInfluenceEdges: edges,
        rejectedGroupKeys: new Set([key]),
      }).some((g) => mentoringGroupMemberKey(g.members.map((m) => m.player.id)) === key),
    ).toBe(false);
  });

  it("bans HA-inverted seating — gifted kid High over worse-HA senior", () => {
    const weakHaSenior = {
      ...strongSenior,
      id: "weak-senior",
      haScore: 9,
      professionalism: 9,
      determination: 11,
      bands: {
        ...strongSenior.bands,
        professionalism: { min: 9, max: 9, midpoint: 9 },
        determination: { min: 11, max: 11, midpoint: 11 },
      },
    };
    const seats: MentoringUnitMember[] = [
      { player: giftedYoung, role: "high" },
      { player: weakHaSenior, role: "mid" },
      { player: peerSenior, role: "low" },
    ];
    expect(violatesHaInfluenceSeating(seats)).toBe(true);
    const group = {
      ...overloadGroup(giftedYoung, weakHaSenior, peerSenior),
      members: seats,
    };
    expect(passesMentoringSuggestGate(group)).toBe(false);
  });

  it("allows HA-inverted seating when manual hierarchy elevates the kid", () => {
    const hierarchyById = new Map([
      ["gifted", "highlyInfluential" as const],
    ]);
    const seats: MentoringUnitMember[] = [
      { player: giftedYoung, role: "high" },
      { player: strongSenior, role: "mid" },
      { player: peerSenior, role: "low" },
    ];
    expect(violatesHaInfluenceSeating(seats, hierarchyById)).toBe(false);
  });

  it("defaults seats so a gifted kid is not High over seniors without manual label", () => {
    const seats = defaultMentoringUnitRoles([
      giftedYoung,
      strongSenior,
      peerSenior,
    ]);
    expect(seats.find((s) => s.role === "high")?.player.id).not.toBe("gifted");
    expect(seats.find((s) => s.role === "low")?.player.id).toBe("gifted");
  });

  it("rejects bad-influence mid dragging a better-HA kid (negative low)", () => {
    const midDrag = {
      id: "drag",
      name: "Drag Mid",
      age: 24,
      determination: 10,
      leadership: 12,
      professionalism: 9,
      ambition: 12,
      loyalty: 11,
      sportsmanship: 10,
      controversy: 10,
      pressure: 11,
      temperament: 11,
      haScore: 10,
      bands: {
        determination: { min: 10, max: 10, midpoint: 10 },
        professionalism: { min: 9, max: 9, midpoint: 9 },
        ambition: { min: 12, max: 12, midpoint: 12 },
        loyalty: { min: 11, max: 11, midpoint: 11 },
        sportsmanship: { min: 10, max: 10, midpoint: 10 },
        controversy: { min: 10, max: 10, midpoint: 10 },
        pressure: { min: 11, max: 11, midpoint: 11 },
        temperament: { min: 11, max: 11, midpoint: 11 },
      },
    };
    const goodKid = {
      ...giftedYoung,
      id: "good",
      name: "Good Kid",
    };
    const group = overloadGroup(strongSenior, midDrag, goodKid);
    expect(passesMentoringSuggestGate(group)).toBe(false);
    expect(
      findInfluenceSafeMentoringGroups([strongSenior, midDrag, goodKid]).some(
        (g) => g.members.some((m) => m.player.id === "drag"),
      ),
    ).toBe(false);
  });

  it("manual none on one downward edge blocks Suggest even when attrs look fine", () => {
    const group = overloadGroup(strongSenior, peerSenior, weakYoung);
    const edges = new Map([
      [mentoringInfluenceEdgeKey("senior", "weak"), "average" as const],
      [mentoringInfluenceEdgeKey("peer", "weak"), "none" as const],
    ]);
    expect(
      resolveMentoringInfluenceLevel(peerSenior, weakYoung, edges),
    ).toBe("none");
    expect(passesMentoringSuggestGate(group, { manualInfluenceEdges: edges })).toBe(
      false,
    );
  });

  it("prefers overload with strong seniors over weaker youngling", () => {
    const groups = findInfluenceSafeMentoringGroups([
      strongSenior,
      peerSenior,
      weakYoung,
    ]);
    const overload = groups.find((g) => g.shape === "overload");
    expect(overload).toBeTruthy();
    expect(overload!.members.find((m) => m.role === "low")?.player.id).toBe(
      "weak",
    );
    const high = overload!.members.find((m) => m.role === "high")!.player;
    const low = overload!.members.find((m) => m.role === "low")!.player;
    expect((high.haScore ?? 0) > (low.haScore ?? 0)).toBe(true);
  });
});

describe("T029 labeled-none + mentee coverage", () => {
  const strongSenior = {
    id: "senior",
    name: "Senior",
    age: 30,
    determination: 17,
    leadership: 16,
    professionalism: 16,
    ambition: 14,
    loyalty: 14,
    sportsmanship: 14,
    controversy: 5,
    pressure: 15,
    temperament: 15,
    haScore: 14,
    bands: {
      determination: { min: 17, max: 17, midpoint: 17 },
      professionalism: { min: 16, max: 16, midpoint: 16 },
      ambition: { min: 14, max: 14, midpoint: 14 },
      loyalty: { min: 14, max: 14, midpoint: 14 },
      sportsmanship: { min: 14, max: 14, midpoint: 14 },
      controversy: { min: 5, max: 5, midpoint: 5 },
      pressure: { min: 15, max: 15, midpoint: 15 },
      temperament: { min: 15, max: 15, midpoint: 15 },
    },
  };
  const peerSenior = {
    ...strongSenior,
    id: "peer",
    name: "Peer",
    age: 28,
    leadership: 14,
  };
  const spareSenior = {
    ...strongSenior,
    id: "spare",
    name: "Spare",
    age: 29,
    leadership: 15,
  };
  const weakYoung = {
    id: "weak",
    name: "Weak Kid",
    age: 19,
    determination: 10,
    leadership: 6,
    professionalism: 9,
    ambition: 10,
    loyalty: 10,
    sportsmanship: 11,
    controversy: 9,
    pressure: 10,
    temperament: 11,
    haScore: 9,
    bands: {
      determination: { min: 10, max: 10, midpoint: 10 },
      professionalism: { min: 9, max: 9, midpoint: 9 },
      ambition: { min: 10, max: 10, midpoint: 10 },
      loyalty: { min: 10, max: 10, midpoint: 10 },
      sportsmanship: { min: 11, max: 11, midpoint: 11 },
      controversy: { min: 9, max: 9, midpoint: 9 },
      pressure: { min: 10, max: 10, midpoint: 10 },
      temperament: { min: 11, max: 11, midpoint: 11 },
    },
  };

  function overloadGroup(
    high: typeof strongSenior,
    mid: typeof strongSenior,
    low: typeof weakYoung,
  ): MentoringInfluenceSafeGroup {
    return {
      shape: "overload",
      members: [
        { player: high, role: "high" },
        { player: mid, role: "mid" },
        { player: low, role: "low" },
      ],
      subject: low,
      score: 40,
      path: "balance",
      edges: [],
      reasons: [],
    };
  }

  it("never re-Suggests a triple after a labeled downward none (reload-safe key)", () => {
    const group = overloadGroup(strongSenior, peerSenior, weakYoung);
    const edges = new Map([
      [mentoringInfluenceEdgeKey("senior", "weak"), "none" as const],
      [mentoringInfluenceEdgeKey("peer", "weak"), "average" as const],
    ]);
    expect(
      mentoringRolesHaveLabeledDownwardNone(
        { senior: "high", peer: "mid", weak: "low" },
        { "senior>weak": "none", "peer>weak": "average" },
      ),
    ).toBe(true);
    expect(
      passesMentoringSuggestGate(group, { manualInfluenceEdges: edges }),
    ).toBe(false);

    const key = mentoringGroupMemberKey(["senior", "peer", "weak"]);
    const afterDissolve = findInfluenceSafeMentoringGroups(
      [strongSenior, peerSenior, weakYoung],
      { rejectedGroupKeys: new Set([key]) },
    );
    expect(
      afterDissolve.some(
        (g) =>
          mentoringGroupMemberKey(g.members.map((m) => m.player.id)) === key,
      ),
    ).toBe(false);
  });

  it("skip-reason: already elite HA", () => {
    const elite = {
      ...weakYoung,
      id: "elite",
      name: "Elite Kid",
      haScore: 14,
      professionalism: 16,
      determination: 15,
      bands: {
        ...weakYoung.bands,
        professionalism: { min: 16, max: 16, midpoint: 16 },
        determination: { min: 15, max: 15, midpoint: 15 },
      },
    };
    const rows = mentoringMenteeCoverage(
      [strongSenior, peerSenior, elite],
      { seatedIds: new Set() },
    );
    const row = rows.find((r) => r.id === "elite");
    expect(row?.seated).toBe(false);
    expect(row?.skipReason).toBe("already elite HA");
  });

  it("skip-reason: no safe senior", () => {
    const drag = {
      id: "drag",
      name: "Drag Mid",
      age: 24,
      determination: 10,
      leadership: 12,
      professionalism: 9,
      ambition: 12,
      loyalty: 11,
      sportsmanship: 10,
      controversy: 10,
      pressure: 11,
      temperament: 11,
      haScore: 10,
      bands: {
        determination: { min: 10, max: 10, midpoint: 10 },
        professionalism: { min: 9, max: 9, midpoint: 9 },
        ambition: { min: 12, max: 12, midpoint: 12 },
        loyalty: { min: 11, max: 11, midpoint: 11 },
        sportsmanship: { min: 10, max: 10, midpoint: 10 },
        controversy: { min: 10, max: 10, midpoint: 10 },
        pressure: { min: 11, max: 11, midpoint: 11 },
        temperament: { min: 11, max: 11, midpoint: 11 },
      },
    };
    const dragB = { ...drag, id: "drag-b", name: "Drag B" };
    const goodKid = {
      ...weakYoung,
      id: "good",
      name: "Good Kid",
      haScore: 12,
      determination: 14,
      professionalism: 13,
      bands: {
        ...weakYoung.bands,
        determination: { min: 14, max: 14, midpoint: 14 },
        professionalism: { min: 13, max: 13, midpoint: 13 },
      },
    };
    const rows = mentoringMenteeCoverage([drag, dragB, goodKid], {
      seatedIds: new Set(),
    });
    const row = rows.find((r) => r.id === "good");
    expect(row?.seated).toBe(false);
    expect(row?.skipReason).toBe("no safe senior");
  });

  it("after a dead triple is rejected, offers a replacement for the same Low", () => {
    const deadKey = mentoringGroupMemberKey(["senior", "peer", "weak"]);
    const result = mentoringReplacementForLow(
      [strongSenior, peerSenior, spareSenior, weakYoung],
      "weak",
      {
        seatedIds: new Set(),
        rejectedGroupKeys: new Set([deadKey]),
      },
    );
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.group.members.find((m) => m.role === "low")?.player.id).toBe(
      "weak",
    );
    expect(
      mentoringGroupMemberKey(result.group.members.map((m) => m.player.id)),
    ).not.toBe(deadKey);
  });

  it("lists CA/PA on coverage and sorts unseated young by PA desc", () => {
    const highPa = {
      ...weakYoung,
      id: "high-pa",
      name: "Zed Kid",
      ca: 130,
      pa: 180,
    };
    const lowPa = {
      ...weakYoung,
      id: "low-pa",
      name: "Ann Kid",
      ca: 90,
      pa: 110,
    };
    const rows = mentoringMenteeCoverage(
      [strongSenior, peerSenior, highPa, lowPa],
      { seatedIds: new Set() },
    );
    const unseated = rows.filter((row) => !row.seated);
    expect(unseated[0]?.id).toBe("high-pa");
    expect(unseated[0]?.ca).toBe(130);
    expect(unseated[0]?.pa).toBe(180);
    expect(formatMentoringCaPa(128, 160)).toBe("128/160");
    expect(formatMentoringCaPa(undefined, undefined)).toBe("—/—");
    expect(formatMentoringCaPa(-1, 0)).toBe("—/—");
  });
});

describe("T030 HA matrix marks from labeled influence only", () => {
  const high = { id: "high", name: "High", value: 18 };
  const mid = { id: "mid", name: "Mid", value: 15 };
  const low = { id: "low", name: "Low", value: 10 };
  const edges = {
    "high>low": "significant" as const,
    "mid>low": "light" as const,
  };

  it("treats unlabeled and none as no display influence", () => {
    expect(mentoringLabeledDisplayInfluence("high", "low")).toBeNull();
    expect(mentoringLabeledDisplayInfluence("high", "low", {})).toBeNull();
    expect(
      mentoringLabeledDisplayInfluence("high", "low", { "high>low": "none" }),
    ).toBeNull();
    expect(
      mentoringLabeledDisplayInfluence("high", "low", {
        "high>low": "average",
      }),
    ).toBe("average");
  });

  it("paints no Low arrows when High→Low and Mid→Low are none or unlabeled", () => {
    expect(
      planMentoringMatrixCellMarks({
        role: "low",
        playerId: "low",
        trait: "determination",
        value: 10,
        influencers: [high, mid],
        receivers: [low],
      }),
    ).toBeUndefined();
    expect(
      planMentoringMatrixCellMarks({
        role: "low",
        playerId: "low",
        trait: "determination",
        value: 10,
        influencers: [high, mid],
        receivers: [low],
        edges: { "high>low": "none", "mid>low": "none" },
      }),
    ).toBeUndefined();
  });

  it("emits one arrow per incoming non-none, colored by that edge", () => {
    const one = planMentoringMatrixCellMarks({
      role: "low",
      playerId: "low",
      trait: "determination",
      value: 10,
      influencers: [high, mid],
      receivers: [low],
      edges: { "high>low": "average" },
    });
    expect(one).toEqual({
      kind: "arrow",
      items: [{ dir: "up", band: "average", tone: "good" }],
    });

    const two = planMentoringMatrixCellMarks({
      role: "low",
      playerId: "low",
      trait: "determination",
      value: 10,
      influencers: [high, mid],
      receivers: [low],
      edges: edges,
    });
    expect(two).toEqual({
      kind: "arrow",
      items: [
        { dir: "up", band: "significant", tone: "good" },
        { dir: "up", band: "light", tone: "good" },
      ],
    });
  });

  it("shows influencer ± only vs receivers they influence, unweighted by band", () => {
    const otherLow = { id: "low2", name: "Other", value: 10 };
    const marks = planMentoringMatrixCellMarks({
      role: "high",
      playerId: "high",
      trait: "determination",
      value: 18,
      influencers: [high, mid],
      receivers: [low, otherLow],
      edges: {
        "high>low": "light",
        "high>low2": "none",
      },
    });
    expect(marks).toEqual({
      kind: "plus",
      items: [{ delta: 8, label: "Low", band: "light", tone: "good" }],
    });

    const significantSameGap = planMentoringMatrixCellMarks({
      role: "high",
      playerId: "high",
      trait: "determination",
      value: 18,
      influencers: [high],
      receivers: [low],
      edges: { "high>low": "significant" },
    });
    expect(significantSameGap).toEqual({
      kind: "plus",
      items: [{ delta: 8, label: "Low", band: "significant", tone: "good" }],
    });
  });

  it("uses numeric CON gap (no mentor-better invert) for arrows and ±", () => {
    const marks = planMentoringMatrixCellMarks({
      role: "low",
      playerId: "low",
      trait: "controversy",
      value: 12,
      influencers: [{ id: "high", name: "High", value: 5 }],
      receivers: [{ id: "low", name: "Low", value: 12 }],
      edges: { "high>low": "average" },
    });
    expect(marks).toEqual({
      kind: "arrow",
      items: [{ dir: "down", band: "average", tone: "good" }],
    });
  });
});

describe("T032 mentoring tool faces and rank-chevrons", () => {
  const peers = [
    { id: "high", role: "high" as const },
    { id: "mid", role: "mid" as const },
    { id: "low", role: "low" as const },
  ];

  it("maps coverage rows to seated / free / skipped at a glance", () => {
    expect(mentoringMenteeFaceState({ seated: true })).toBe("seated");
    expect(mentoringMenteeFaceState({ seated: false })).toBe("free");
    expect(
      mentoringMenteeFaceState({
        seated: false,
        skipReason: "already elite HA",
      }),
    ).toBe("skipped");
  });

  it("counts 1/2/3 chevrons for light/average/significant; none is 0", () => {
    expect(mentoringChevronCount(null)).toBe(0);
    expect(mentoringChevronCount("light")).toBe(1);
    expect(mentoringChevronCount("average")).toBe(2);
    expect(mentoringChevronCount("significant")).toBe(3);
  });

  it("marks outgoing ▲ only; unlabeled is empty (shown on the other seat)", () => {
    expect(
      planMentoringSeatPeerMarks({
        playerId: "low",
        peers,
        edges: { "high>low": "significant", "low>mid": "light" },
      }),
    ).toEqual([
      { peerId: "high", outgoing: null },
      { peerId: "mid", outgoing: "light" },
    ]);
    expect(
      planMentoringSeatPeerMarks({
        playerId: "high",
        peers,
        edges: { "high>low": "average", "low>high": "light" },
      }),
    ).toEqual([
      { peerId: "mid", outgoing: null },
      { peerId: "low", outgoing: "average" },
    ]);
    expect(
      planMentoringSeatPeerMarks({
        playerId: "high",
        peers,
        edges: { "high>low": "significant" },
      }),
    ).toEqual([
      { peerId: "mid", outgoing: null },
      { peerId: "low", outgoing: "significant" },
    ]);
  });

  it("pair hover: receiver arrows follow the number, exerter ±, mutual both; unlabeled empty", () => {
    const oneWay = planMentoringPairTraitMarks({
      subjectId: "high",
      peerId: "low",
      trait: "determination",
      subjectValue: 18,
      peerValue: 10,
      edges: { "high>low": "average" },
    });
    expect(oneWay.subject).toEqual({
      exert: { delta: 8, band: "average", tone: "good" },
    });
    expect(oneWay.peer).toEqual({
      receive: { dir: "up", band: "average", count: 2, tone: "good" },
    });

    const mutual = planMentoringPairTraitMarks({
      subjectId: "high",
      peerId: "low",
      trait: "determination",
      subjectValue: 18,
      peerValue: 10,
      edges: { "high>low": "significant", "low>high": "light" },
    });
    expect(mutual.subject.exert).toEqual({ delta: 8, band: "significant", tone: "good" });
    expect(mutual.subject.receive).toEqual({
      dir: "down",
      band: "light",
      count: 1,
      tone: "bad",
    });
    expect(mutual.peer.exert).toEqual({ delta: -8, band: "light", tone: "bad" });
    expect(mutual.peer.receive).toEqual({
      dir: "up",
      band: "significant",
      count: 3,
      tone: "good",
    });

    const unlabeled = planMentoringPairTraitMarks({
      subjectId: "high",
      peerId: "low",
      trait: "determination",
      subjectValue: 18,
      peerValue: 10,
    });
    expect(unlabeled).toEqual({ subject: {}, peer: {} });
  });

  it("omits CA/PA face digits when both missing; keeps known values only", () => {
    expect(mentoringCaPaFaceDigits(undefined, undefined)).toBeNull();
    expect(mentoringCaPaFaceDigits(-1, 0)).toBeNull();
    expect(mentoringCaPaFaceDigits(128, 160)).toEqual({ ca: 128, pa: 160 });
    expect(mentoringCaPaFaceDigits(128, undefined)).toEqual({ ca: 128 });
  });
});

describe("T062 mentoring HA arrows follow the number", () => {
  const pair = (menteeValue: number, trait: string, band: "light" | "average" | "significant") =>
    planMentoringPairTraitMarks({
      subjectId: "high",
      peerId: "low",
      trait,
      subjectValue: trait === "controversy" ? 7 : 16,
      peerValue: menteeValue,
      edges: { "high>low": band },
    });

  const matrix = (
    role: "high" | "low",
    menteeValue: number,
    trait: string,
    band: "light" | "average" | "significant",
  ) => {
    const influencerValue = trait === "controversy" ? 7 : 16;
    return planMentoringMatrixCellMarks({
      role,
      playerId: role === "high" ? "high" : "low",
      trait,
      value: role === "high" ? influencerValue : menteeValue,
      influencers: [{ id: "high", name: "High", value: influencerValue }],
      receivers: [{ id: "low", name: "Low", value: menteeValue }],
      edges: { "high>low": band },
    });
  };

  it("light Det 16 vs 15: mentee 1 green ▲; influencer +1 green", () => {
    const hover = pair(15, "determination", "light");
    expect(hover.peer.receive).toEqual({
      dir: "up",
      band: "light",
      count: 1,
      tone: "good",
    });
    expect(hover.subject.exert).toEqual({ delta: 1, band: "light", tone: "good" });
    expect(matrix("low", 15, "determination", "light")).toEqual({
      kind: "arrow",
      items: [{ dir: "up", band: "light", tone: "good" }],
    });
    expect(matrix("high", 15, "determination", "light")).toEqual({
      kind: "plus",
      items: [{ delta: 1, label: "Low", band: "light", tone: "good" }],
    });
  });

  it("light Det 16 vs 17: mentee 1 red ▼; influencer −1 red", () => {
    const hover = pair(17, "determination", "light");
    expect(hover.peer.receive).toEqual({
      dir: "down",
      band: "light",
      count: 1,
      tone: "bad",
    });
    expect(hover.subject.exert).toEqual({ delta: -1, band: "light", tone: "bad" });
    expect(matrix("low", 17, "determination", "light")).toEqual({
      kind: "arrow",
      items: [{ dir: "down", band: "light", tone: "bad" }],
    });
    expect(matrix("high", 17, "determination", "light")).toEqual({
      kind: "plus",
      items: [{ delta: -1, label: "Low", band: "light", tone: "bad" }],
    });
  });

  it("equal Det: value only; no arrows or ±", () => {
    const hover = pair(16, "determination", "light");
    expect(hover).toEqual({ subject: {}, peer: {} });
    expect(matrix("low", 16, "determination", "light")).toBeUndefined();
    expect(matrix("high", 16, "determination", "light")).toBeUndefined();
  });

  it("average → 2 green ▲; significant → 3 red ▼; same direction rule", () => {
    const avg = pair(15, "determination", "average");
    expect(avg.peer.receive).toEqual({
      dir: "up",
      band: "average",
      count: 2,
      tone: "good",
    });
    expect(avg.subject.exert).toEqual({ delta: 1, band: "average", tone: "good" });
    expect(matrix("low", 15, "determination", "average")).toEqual({
      kind: "arrow",
      items: [{ dir: "up", band: "average", tone: "good" }],
    });

    const sigDown = pair(17, "determination", "significant");
    expect(sigDown.peer.receive).toEqual({
      dir: "down",
      band: "significant",
      count: 3,
      tone: "bad",
    });
    expect(sigDown.subject.exert).toEqual({
      delta: -1,
      band: "significant",
      tone: "bad",
    });
    expect(matrix("low", 17, "determination", "significant")).toEqual({
      kind: "arrow",
      items: [{ dir: "down", band: "significant", tone: "bad" }],
    });
  });

  it("CON mentee 10 vs influencer 7: green ▼ (towards lower); influencer −3 green", () => {
    const hover = pair(10, "controversy", "light");
    expect(hover.peer.receive).toEqual({
      dir: "down",
      band: "light",
      count: 1,
      tone: "good",
    });
    expect(hover.subject.exert).toEqual({ delta: -3, band: "light", tone: "good" });
    expect(matrix("low", 10, "controversy", "light")).toEqual({
      kind: "arrow",
      items: [{ dir: "down", band: "light", tone: "good" }],
    });
    expect(matrix("high", 10, "controversy", "light")).toEqual({
      kind: "plus",
      items: [{ delta: -3, label: "Low", band: "light", tone: "good" }],
    });
  });

  it("unlabeled pair: values only, no arrows/±", () => {
    expect(
      planMentoringPairTraitMarks({
        subjectId: "high",
        peerId: "low",
        trait: "determination",
        subjectValue: 16,
        peerValue: 15,
      }),
    ).toEqual({ subject: {}, peer: {} });
    expect(
      planMentoringMatrixCellMarks({
        role: "low",
        playerId: "low",
        trait: "determination",
        value: 15,
        influencers: [{ id: "high", name: "High", value: 16 }],
        receivers: [{ id: "low", name: "Low", value: 15 }],
      }),
    ).toBeUndefined();
    expect(
      planMentoringMatrixCellMarks({
        role: "high",
        playerId: "high",
        trait: "determination",
        value: 16,
        influencers: [{ id: "high", name: "High", value: 16 }],
        receivers: [{ id: "low", name: "Low", value: 15 }],
      }),
    ).toBeUndefined();
  });
});
