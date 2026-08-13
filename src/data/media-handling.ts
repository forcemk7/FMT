import type { MediaHandlingDefinition } from "../catalog/types.js";

/**
 * Port of `FM HA Calculator - Media Handling Style.csv`.
 * Labels use full spellings; sheet typos (Ouspoken, etc.) are normalized.
 */
export const MEDIA_HANDLING: MediaHandlingDefinition[] = [
  {
    id: "Outspoken, Unflappable",
    styles: ["Outspoken", "Unflappable"],
    bands: {
      pressure: { min: 15, max: 20 },
      temperament: { min: 15, max: 20 },
      controversy: { min: 15, max: 20 },
    },
    cases: [],
  },
  {
    id: "Outspoken, Short-tempered, Confrontational",
    styles: ["Outspoken", "Short-tempered", "Confrontational"],
    bands: {
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 1, max: 2 },
      controversy: { min: 15, max: 20 },
    },
    cases: [],
  },
  {
    id: "Outspoken, Short-tempered",
    styles: ["Outspoken", "Short-tempered"],
    bands: {
      sportsmanship: { min: 8, max: 20 },
      temperament: { min: 1, max: 2 },
      controversy: { min: 15, max: 20 },
    },
    cases: [],
  },
  {
    id: "Outspoken, Volatile, Confrontational",
    styles: ["Outspoken", "Volatile", "Confrontational"],
    bands: {
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 3, max: 6 },
      controversy: { min: 15, max: 20 },
    },
    cases: [],
  },
  {
    id: "Outspoken, Volatile",
    styles: ["Outspoken", "Volatile"],
    bands: {
      sportsmanship: { min: 8, max: 20 },
      temperament: { min: 3, max: 6 },
      controversy: { min: 15, max: 20 },
    },
    cases: [],
  },
  {
    id: "Outspoken, Confrontational",
    styles: ["Outspoken", "Confrontational"],
    bands: {
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 7, max: 7 },
      controversy: { min: 15, max: 20 },
    },
    cases: [],
  },
  {
    id: "Outspoken",
    styles: ["Outspoken"],
    bands: {
      temperament: { min: 7, max: 20 },
      controversy: { min: 15, max: 20 },
    },
    cases: [3, 4],
  },
  {
    id: "Evasive, Unflappable",
    styles: ["Evasive", "Unflappable"],
    bands: {
      professionalism: { min: 15, max: 20 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 15, max: 15 },
      controversy: { min: 1, max: 14 },
    },
    cases: [],
  },
  {
    id: "Evasive, Short-tempered, Confrontational",
    styles: ["Evasive", "Short-tempered", "Confrontational"],
    bands: {
      professionalism: { min: 15, max: 20 },
      sportsmanship: { min: 1, max: 7 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 1, max: 2 },
      controversy: { min: 1, max: 14 },
    },
    cases: [],
  },
  {
    id: "Evasive, Short-tempered",
    styles: ["Evasive", "Short-tempered"],
    bands: {
      professionalism: { min: 15, max: 20 },
      sportsmanship: { min: 8, max: 20 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 1, max: 2 },
      controversy: { min: 1, max: 14 },
    },
    cases: [],
  },
  {
    id: "Evasive, Volatile, Confrontational",
    styles: ["Evasive", "Volatile", "Confrontational"],
    bands: {
      professionalism: { min: 15, max: 20 },
      sportsmanship: { min: 1, max: 7 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 3, max: 6 },
      controversy: { min: 1, max: 14 },
    },
    cases: [],
  },
  {
    id: "Evasive, Volatile",
    styles: ["Evasive", "Volatile"],
    bands: {
      professionalism: { min: 15, max: 20 },
      sportsmanship: { min: 8, max: 20 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 3, max: 6 },
      controversy: { min: 1, max: 14 },
    },
    cases: [],
  },
  {
    id: "Evasive, Confrontational",
    styles: ["Evasive", "Confrontational"],
    bands: {
      professionalism: { min: 15, max: 20 },
      sportsmanship: { min: 1, max: 7 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 7, max: 7 },
      controversy: { min: 1, max: 14 },
    },
    cases: [],
  },
  {
    id: "Evasive, Reserved",
    styles: ["Evasive", "Reserved"],
    bands: {
      professionalism: { min: 15, max: 20 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 7, max: 14 },
      controversy: { min: 1, max: 5 },
    },
    cases: [3],
  },
  {
    id: "Evasive",
    styles: ["Evasive"],
    bands: {
      professionalism: { min: 15, max: 20 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 7, max: 14 },
      controversy: { min: 6, max: 14 },
    },
    cases: [3],
  },
  {
    id: "Unflappable",
    styles: ["Unflappable"],
    bands: {
      loyalty: { min: 11, max: 20 },
      pressure: { min: 15, max: 20 },
      temperament: { min: 15, max: 20 },
      controversy: { min: 1, max: 14 },
    },
    cases: [6],
  },
  {
    id: "Short-tempered, Confrontational",
    styles: ["Short-tempered", "Confrontational"],
    bands: {
      professionalism: { min: 13, max: 20 },
      loyalty: { min: 11, max: 20 },
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 1, max: 2 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1],
  },
  {
    id: "Short-tempered",
    styles: ["Short-tempered"],
    bands: {
      loyalty: { min: 11, max: 20 },
      sportsmanship: { min: 8, max: 20 },
      temperament: { min: 1, max: 2 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 6],
  },
  {
    id: "Volatile, Confrontational",
    styles: ["Volatile", "Confrontational"],
    bands: {
      professionalism: { min: 13, max: 20 },
      loyalty: { min: 11, max: 20 },
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 3, max: 6 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1],
  },
  {
    id: "Volatile",
    styles: ["Volatile"],
    bands: {
      loyalty: { min: 11, max: 20 },
      sportsmanship: { min: 8, max: 20 },
      temperament: { min: 3, max: 6 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 6],
  },
  {
    id: "Confrontational",
    styles: ["Confrontational"],
    bands: {
      professionalism: { min: 13, max: 20 },
      loyalty: { min: 11, max: 20 },
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 7, max: 7 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1],
  },
  {
    id: "Reserved",
    styles: ["Reserved"],
    bands: {
      professionalism: { min: 15, max: 20 },
      loyalty: { min: 11, max: 20 },
      pressure: { min: 1, max: 14 },
      temperament: { min: 7, max: 20 },
      controversy: { min: 1, max: 5 },
    },
    cases: [1, 3],
  },
  {
    id: "Level-Headed",
    styles: ["Level-Headed"],
    bands: {
      loyalty: { min: 11, max: 20 },
      temperament: { min: 7, max: 20 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 3, 4, 5, 6],
  },
  {
    id: "Unflappable, Media-friendly",
    styles: ["Unflappable", "Media-friendly"],
    bands: {
      pressure: { min: 15, max: 20 },
      temperament: { min: 15, max: 20 },
      controversy: { min: 1, max: 14 },
    },
    cases: [2],
  },
  {
    id: "Media-friendly, Short-tempered, Confrontational",
    styles: ["Media-friendly", "Short-tempered", "Confrontational"],
    bands: {
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 1, max: 2 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 2],
  },
  {
    id: "Media-friendly, Short-tempered",
    styles: ["Media-friendly", "Short-tempered"],
    bands: {
      sportsmanship: { min: 8, max: 20 },
      temperament: { min: 1, max: 2 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 2],
  },
  {
    id: "Volatile, Media-friendly, Confrontational",
    styles: ["Volatile", "Media-friendly", "Confrontational"],
    bands: {
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 3, max: 6 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 2],
  },
  {
    id: "Volatile, Media-friendly",
    styles: ["Volatile", "Media-friendly"],
    bands: {
      sportsmanship: { min: 8, max: 20 },
      temperament: { min: 3, max: 6 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 2],
  },
  {
    id: "Media-friendly, Confrontational",
    styles: ["Media-friendly", "Confrontational"],
    bands: {
      sportsmanship: { min: 1, max: 7 },
      temperament: { min: 7, max: 7 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 2],
  },
  {
    id: "Media-friendly, Reserved",
    styles: ["Media-friendly", "Reserved"],
    bands: {
      professionalism: { min: 15, max: 20 },
      loyalty: { min: 1, max: 10 },
      pressure: { min: 1, max: 14 },
      temperament: { min: 7, max: 20 },
      controversy: { min: 1, max: 5 },
    },
    cases: [3],
  },
  {
    id: "Media-friendly",
    styles: ["Media-friendly"],
    bands: {
      temperament: { min: 7, max: 20 },
      controversy: { min: 1, max: 14 },
    },
    cases: [1, 2, 3, 4, 5],
  },
];
