import type { AttributeRange } from "../domain/attributes.js";
import { TRACKED_ATTRIBUTES, FULL_RANGE } from "../domain/attributes.js";
import { intersect } from "../domain/range.js";
import type { CaseClause, MediaCase } from "../catalog/types.js";
import type { BandMap } from "./bands.js";

/**
 * Case application strategy.
 *
 * `union_feasible` (default): treat each case as an OR constraint and take the
 * attribute-wise union of feasible branches — preserves possibility ranges.
 *
 * `naive_and` (experimental): treat every mentioned range as a hard intersect,
 * matching one reading of the Outspoken 3+4 example (Temp 8-14, etc.).
 * Kept for comparison while we lock spreadsheet parity.
 */
export type CaseMode = "union_feasible" | "naive_and";

function clauseToBands(clause: CaseClause): BandMap[] {
  if (clause.kind === "range") {
    return [{ [clause.attribute]: { ...clause.range } }];
  }

  // AND of sub-clauses → cartesian product of their band options
  let acc: BandMap[] = [{}];
  for (const sub of clause.clauses) {
    const options = clauseToBands(sub);
    const next: BandMap[] = [];
    for (const left of acc) {
      for (const right of options) {
        const merged: BandMap = { ...left };
        let ok = true;
        for (const attribute of TRACKED_ATTRIBUTES) {
          const a = left[attribute];
          const b = right[attribute];
          if (a && b) {
            const both = intersect(a, b);
            if (!both) {
              ok = false;
              break;
            }
            merged[attribute] = both;
          } else if (b) {
            merged[attribute] = { ...b };
          }
        }
        if (ok) next.push(merged);
      }
    }
    acc = next;
  }
  return acc;
}

/** Expand a case into alternative BandMaps (OR branches). */
export function caseBranches(mediaCase: MediaCase): BandMap[] {
  return mediaCase.anyOf.flatMap((clause) => clauseToBands(clause));
}

function mergeUnion(
  a: AttributeRange | undefined,
  b: AttributeRange,
): AttributeRange {
  if (!a) return { ...b };
  return { min: Math.min(a.min, b.min), max: Math.max(a.max, b.max) };
}

/**
 * Restrict `bands` so that every listed case is satisfiable.
 * Returns the projected possibility ranges per attribute.
 */
export function applyCases(
  bands: BandMap,
  cases: readonly MediaCase[],
  mode: CaseMode = "union_feasible",
): { bands: BandMap; unsatisfiable: number[] } {
  if (cases.length === 0) {
    return { bands, unsatisfiable: [] };
  }

  if (mode === "naive_and") {
    return applyCasesNaiveAnd(bands, cases);
  }

  let worlds: BandMap[] = [materialize(bands)];
  const unsatisfiable: number[] = [];

  for (const mediaCase of cases) {
    const branches = caseBranches(mediaCase);
    const nextWorlds: BandMap[] = [];

    for (const world of worlds) {
      for (const branch of branches) {
        const merged = tryMergeWorld(world, branch);
        if (merged) nextWorlds.push(merged);
      }
    }

    if (nextWorlds.length === 0) {
      unsatisfiable.push(mediaCase.id);
      continue;
    }
    worlds = nextWorlds;
  }

  return { bands: projectWorlds(worlds), unsatisfiable };
}

function materialize(bands: BandMap): BandMap {
  const world: BandMap = {};
  for (const attribute of TRACKED_ATTRIBUTES) {
    world[attribute] = bands[attribute]
      ? { ...bands[attribute]! }
      : { ...FULL_RANGE };
  }
  return world;
}

function tryMergeWorld(world: BandMap, branch: BandMap): BandMap | null {
  const next: BandMap = {};
  for (const attribute of TRACKED_ATTRIBUTES) {
    const base = world[attribute] ?? { ...FULL_RANGE };
    const extra = branch[attribute];
    if (!extra) {
      next[attribute] = { ...base };
      continue;
    }
    const merged = intersect(base, extra);
    if (!merged) return null;
    next[attribute] = merged;
  }
  return next;
}

function projectWorlds(worlds: BandMap[]): BandMap {
  if (worlds.length === 0) return {};

  const projected: BandMap = {};
  for (const attribute of TRACKED_ATTRIBUTES) {
    let union: AttributeRange | undefined;
    for (const world of worlds) {
      const range = world[attribute];
      if (!range) continue;
      union = mergeUnion(union, range);
    }
    if (union) projected[attribute] = union;
  }
  return projected;
}

/** Experimental: intersect every range mentioned in every case clause. */
function applyCasesNaiveAnd(
  bands: BandMap,
  cases: readonly MediaCase[],
): { bands: BandMap; unsatisfiable: number[] } {
  const next: BandMap = { ...bands };
  const unsatisfiable: number[] = [];

  for (const mediaCase of cases) {
    for (const clause of flattenClauses(mediaCase.anyOf)) {
      if (clause.kind !== "range") continue;
      const existing = next[clause.attribute] ?? { ...FULL_RANGE };
      const merged = intersect(existing, clause.range);
      if (!merged) {
        unsatisfiable.push(mediaCase.id);
        continue;
      }
      next[clause.attribute] = merged;
    }
  }

  return { bands: next, unsatisfiable: [...new Set(unsatisfiable)] };
}

function flattenClauses(clauses: readonly CaseClause[]): CaseClause[] {
  const out: CaseClause[] = [];
  for (const clause of clauses) {
    if (clause.kind === "all") {
      out.push(...flattenClauses(clause.clauses));
    } else {
      out.push(clause);
    }
  }
  return out;
}
