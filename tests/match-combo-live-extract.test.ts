import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import {
  comboFeasibleForAttrs,
  loadCatalog,
  rankPersonalityMediaCombosUnified,
} from "../src/index.js";
import type { MatchableAttrs } from "../src/inference/match-combo.js";

const catalog = loadCatalog();
const rows = JSON.parse(
  readFileSync("tmp/fm-spike/mismatch-attrs-check.json", "utf8"),
) as Array<{
  uid: number;
  name: string;
  ig: { personality: string; media: string; det: number; lea: number };
  ex: MatchableAttrs;
}>;

function matchLikeSquad(attrs: MatchableAttrs) {
  const ranking = rankPersonalityMediaCombosUnified(catalog, {
    population: "mixed",
  });
  const hits = ranking.entries.filter((e) =>
    comboFeasibleForAttrs(catalog, e.personality, e.mediaHandling, attrs),
  );
  if (hits.length === 0) return null;
  // light priority: drop losers via prioritizedBy
  const personalities = new Set(hits.map((h) => h.personality));
  const winners = new Set(personalities);
  for (const id of personalities) {
    const def = catalog.personalities.find((p) => p.id === id);
    if (!def) continue;
    for (const better of def.prioritizedBy) {
      if (personalities.has(better)) winners.delete(id);
    }
  }
  const pool = hits.filter((h) => winners.has(h.personality));
  const use = pool.length > 0 ? pool : hits;
  // tightest
  let best = use[0]!;
  let bestTight = Number.POSITIVE_INFINITY;
  for (const entry of use) {
    let tight = 0;
    for (const band of Object.values(entry.bands)) {
      if (!band || (band.min === 1 && band.max === 20)) continue;
      tight += band.max - band.min;
    }
    if (tight < bestTight || (tight === bestTight && entry.rank < best.rank)) {
      best = entry;
      bestTight = tight;
    }
  }
  return best;
}

describe("live extract attrs → case-feasible labels", () => {
  for (const row of rows) {
    it(`${row.name} → ${row.ig.personality} · ${row.ig.media}`, () => {
      // Koné was the known Det=18 wrong-card bug; require Det parity there.
      // Remaining Det±1 drifts (e.g. Contreras) are separate CA-picker edges.
      if (row.uid === 2002166919) {
        expect(row.ex.determination).toBe(row.ig.det);
        expect(row.ex.leadership).toBe(row.ig.lea);
      }
      const hit = matchLikeSquad(row.ex);
      expect(hit?.personality).toBe(row.ig.personality);
      expect(hit?.mediaHandling).toBe(row.ig.media);
    });
  }
});
