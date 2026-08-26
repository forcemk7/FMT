import type { MediaCase } from "../catalog/types";

/**
 * Media-handling "Cases" from the spreadsheet footer.
 * Each case is an OR of clauses; assigned styles must satisfy every listed case.
 */
export const MEDIA_CASES: MediaCase[] = [
  {
    id: 1,
    label: "Prof 1-14 and/or Press 1-14",
    anyOf: [
      { kind: "range", attribute: "professionalism", range: { min: 1, max: 14 } },
      { kind: "range", attribute: "pressure", range: { min: 1, max: 14 } },
    ],
  },
  {
    id: 2,
    label: "Loy 1-10 and/or (Both Prof 1-12 and Sports 1-11)",
    anyOf: [
      { kind: "range", attribute: "loyalty", range: { min: 1, max: 10 } },
      {
        kind: "all",
        clauses: [
          {
            kind: "range",
            attribute: "professionalism",
            range: { min: 1, max: 12 },
          },
          {
            kind: "range",
            attribute: "sportsmanship",
            range: { min: 1, max: 11 },
          },
        ],
      },
    ],
  },
  {
    id: 3,
    label: "Temp 8-20 and/or Sports 8-20",
    anyOf: [
      { kind: "range", attribute: "temperament", range: { min: 8, max: 20 } },
      { kind: "range", attribute: "sportsmanship", range: { min: 8, max: 20 } },
    ],
  },
  {
    id: 4,
    label: "Temp 1-14 and/or Press 1-14",
    anyOf: [
      { kind: "range", attribute: "temperament", range: { min: 1, max: 14 } },
      { kind: "range", attribute: "pressure", range: { min: 1, max: 14 } },
    ],
  },
  {
    id: 5,
    label: "Cont 6-14 and/or Prof 1-14",
    anyOf: [
      { kind: "range", attribute: "controversy", range: { min: 6, max: 14 } },
      { kind: "range", attribute: "professionalism", range: { min: 1, max: 14 } },
    ],
  },
  {
    id: 6,
    label: "Prof 13-20 and/or Sports 12-20",
    anyOf: [
      { kind: "range", attribute: "professionalism", range: { min: 13, max: 20 } },
      { kind: "range", attribute: "sportsmanship", range: { min: 12, max: 20 } },
    ],
  },
];
