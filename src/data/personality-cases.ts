import type { MediaCase } from "../catalog/types.js";

export type PersonalityCaseFlags = {
  det: number[];
  other: number[];
  detNewgen: number[];
  otherNewgen: number[];
};

/** Personality other-case OR rules from Evaluation. */
export const PERSONALITY_OTHER_CASES: MediaCase[] = [
  {
    id: 1,
    label: "Pro 1-17 and/or Tem 1-9",
    anyOf: [
      {
        kind: "range",
        attribute: "professionalism",
        range: { min: 1, max: 17 },
      },
      {
        kind: "range",
        attribute: "temperament",
        range: { min: 1, max: 9 },
      },
    ],
  },
  {
    id: 2,
    label: "Amb 1-15 and/or Loy 10-20",
    anyOf: [
      {
        kind: "range",
        attribute: "ambition",
        range: { min: 1, max: 15 },
      },
      {
        kind: "range",
        attribute: "loyalty",
        range: { min: 10, max: 20 },
      },
    ],
  },
  {
    id: 3,
    label: "Amb 6-20 and/or Loy 1-10",
    anyOf: [
      {
        kind: "range",
        attribute: "ambition",
        range: { min: 6, max: 20 },
      },
      {
        kind: "range",
        attribute: "loyalty",
        range: { min: 1, max: 10 },
      },
    ],
  },
  {
    id: 4,
    label: "Loy 1-17 and/or Amb 8-20",
    anyOf: [
      {
        kind: "range",
        attribute: "loyalty",
        range: { min: 1, max: 17 },
      },
      {
        kind: "range",
        attribute: "ambition",
        range: { min: 8, max: 20 },
      },
    ],
  },
  {
    id: 5,
    label: "Tem 1-9 and/or Pre 1-14",
    anyOf: [
      {
        kind: "range",
        attribute: "temperament",
        range: { min: 1, max: 9 },
      },
      {
        kind: "range",
        attribute: "pressure",
        range: { min: 1, max: 14 },
      },
    ],
  },
  {
    id: 6,
    label: "Tem 10-20 and/or Amb 1-13",
    anyOf: [
      {
        kind: "range",
        attribute: "temperament",
        range: { min: 10, max: 20 },
      },
      {
        kind: "range",
        attribute: "ambition",
        range: { min: 1, max: 13 },
      },
    ],
  },
];

/**
 * Cases (det) case 5 template: Spo 5-20.
 * Empirically the only det flag applied as a forward clamp in the sheet.
 */
export const DET_CASE_SPORTSMANSHIP = {
  id: 5,
  range: { min: 5, max: 20 },
} as const;

/** Case flags from Personalities / Newgen Personalities sheets. */
export const PERSONALITY_CASE_FLAGS: Record<string, PersonalityCaseFlags> = {
  "Ambitious": {
    det: [],
    other: [1],
    detNewgen: [2],
    otherNewgen: [1, 1],
  },
  "Balanced": {
    det: [],
    other: [5],
    detNewgen: [1, 2, 3, 5],
    otherNewgen: [1, 3, 5],
  },
  "Born Leader": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [1],
  },
  "Casual": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [],
  },
  "Charismatic Leader": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [],
  },
  "Determined": {
    det: [],
    other: [1],
    detNewgen: [],
    otherNewgen: [1, 1],
  },
  "Driven": {
    det: [],
    other: [1],
    detNewgen: [],
    otherNewgen: [1, 1],
  },
  "Easily Discouraged": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [1, 1, 3],
  },
  "Fairly Ambitious": {
    det: [4],
    other: [5],
    detNewgen: [2, 3, 4, 5],
    otherNewgen: [1, 5],
  },
  "Fairly Determined": {
    det: [],
    other: [4, 5],
    detNewgen: [],
    otherNewgen: [1, 3, 4, 5],
  },
  "Fairly Loyal": {
    det: [4],
    other: [4, 5],
    detNewgen: [1, 2, 3, 4, 5],
    otherNewgen: [1, 4, 5],
  },
  "Fairly Professional": {
    det: [4],
    other: [1, 4, 5, 6],
    detNewgen: [1, 3, 4, 5],
    otherNewgen: [1, 3, 4, 5, 6],
  },
  "Fairly Sporting": {
    det: [4],
    other: [5],
    detNewgen: [1, 2, 3, 4],
    otherNewgen: [1, 3, 5],
  },
  "Fickle": {
    det: [],
    other: [],
    detNewgen: [2],
    otherNewgen: [1, 1],
  },
  "Honest": {
    det: [],
    other: [1],
    detNewgen: [],
    otherNewgen: [1, 1, 3],
  },
  "Iron Willed": {
    det: [],
    other: [1, 4],
    detNewgen: [],
    otherNewgen: [1, 1, 3, 4],
  },
  "Jovial": {
    det: [],
    other: [4],
    detNewgen: [1, 2, 5, 6],
    otherNewgen: [3, 4],
  },
  "Leader": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [1],
  },
  "Light-Hearted": {
    det: [4],
    other: [4],
    detNewgen: [1, 2, 4, 6],
    otherNewgen: [3, 4],
  },
  "Lacking in Determination": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [1, 1, 3],
  },
  "Lacking in Self-Belief": {
    det: [],
    other: [],
    detNewgen: [1],
    otherNewgen: [1, 1, 3, 4],
  },
  "Loyal": {
    det: [4],
    other: [1],
    detNewgen: [2, 4, 5],
    otherNewgen: [1, 1],
  },
  "Mercenary": {
    det: [],
    other: [1],
    detNewgen: [2],
    otherNewgen: [1, 1],
  },
  "Model Citizen": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [],
  },
  "Model Professional": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [],
  },
  "Perfectionist": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [],
  },
  "Professional": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [],
  },
  "Realist": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [1, 1, 3],
  },
  "Resilient": {
    det: [],
    other: [1, 4],
    detNewgen: [],
    otherNewgen: [1, 1, 3, 4],
  },
  "Resolute": {
    det: [],
    other: [1, 4, 5, 6],
    detNewgen: [],
    otherNewgen: [1, 3, 4, 5, 6],
  },
  "Slack": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [],
  },
  "Spineless": {
    det: [],
    other: [],
    detNewgen: [1],
    otherNewgen: [1, 1, 3, 4],
  },
  "Spirited": {
    det: [],
    other: [4],
    detNewgen: [1, 5, 6],
    otherNewgen: [3, 4],
  },
  "Sporting": {
    det: [],
    other: [1],
    detNewgen: [],
    otherNewgen: [1, 1, 3],
  },
  "Temperamental": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [],
  },
  "Unambitious": {
    det: [],
    other: [],
    detNewgen: [2],
    otherNewgen: [1, 1],
  },
  "Unsporting": {
    det: [],
    other: [],
    detNewgen: [],
    otherNewgen: [1, 1, 3],
  },
  "Very Ambitious": {
    det: [],
    other: [1],
    detNewgen: [2],
    otherNewgen: [1, 1],
  },
  "Very Loyal": {
    det: [4],
    other: [1],
    detNewgen: [2, 4, 5],
    otherNewgen: [1, 1],
  },
};

export function caseFlagsFor(
  personalityId: string,
  isRegen: boolean,
): { det: number[]; other: number[] } {
  const flags = PERSONALITY_CASE_FLAGS[personalityId];
  if (!flags) return { det: [], other: [] };
  const raw = isRegen
    ? { det: flags.detNewgen, other: flags.otherNewgen }
    : { det: flags.det, other: flags.other };
  return {
    det: [...new Set(raw.det)],
    other: [...new Set(raw.other)],
  };
}

