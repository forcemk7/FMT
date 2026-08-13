import { describe, expect, it } from "vitest";
import {
  defaultMentoringUnitRoles,
  evaluateMentoringUnit,
  findInfluenceSafeMentoringGroups,
  findMentoringGroupsForSubject,
  isMentoringInfluenceSubject,
  MENTORING_DISPLAY_ORDER,
  mentoringFocus,
  mentoringMenteeAttributeEvidence,
  mentoringRole,
  mentoringTraitWeight,
  menteePathUnderMentor,
  scoreSafeInfluence,
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
