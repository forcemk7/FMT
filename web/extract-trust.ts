/**
 * Blind extract trust bar (T011).
 *
 * Incomplete name / attr / loan rows must not look finished.
 * Mentoring Suggest seats only name-resolved players with enough HA signals.
 * Personality labels are inferred from attrs — never read as FM text.
 */

import type { PersonalitySignals } from "../shared/save/types.ts";
import {
  rosterPersonalitySignals,
  type RosterPlayer,
} from "./roster-data.ts";

/** Same 8 traits Mentoring uses to judge a candidate. */
export const MENTORING_ATTR_SIGNAL_KEYS = [
  "determination",
  "professionalism",
  "ambition",
  "loyalty",
  "sportsmanship",
  "controversy",
  "pressure",
  "temperament",
] as const satisfies ReadonlyArray<keyof PersonalitySignals>;

/** Minimum finite mentoring attrs before a row is complete-enough to seat. */
export const MENTORING_ATTR_SIGNAL_MIN = 3;

const UNRESOLVED_NAME = /^(uid|job):\s*\d+$/i;

export type ExtractTrustFlags = {
  nameResolved: boolean;
  attrsEnough: boolean;
  loanKnown: boolean;
  /** Name + attrs — the Mentoring Suggest bar. */
  mentoringReady: boolean;
};

export type ExtractTrustSummary = {
  total: number;
  mentoringReady: number;
  extractComplete: number;
  missingName: number;
  attrsShort: number;
  loanUnknown: number;
};

export function isRosterNameResolved(
  name: string | null | undefined,
): boolean {
  const trimmed = (name ?? "").trim();
  if (!trimmed) return false;
  return !UNRESOLVED_NAME.test(trimmed);
}

export function rosterResolvedName(player: RosterPlayer): string | null {
  const trimmed = (player.name ?? "").trim();
  return isRosterNameResolved(trimmed) ? trimmed : null;
}

export function mentoringAttrSignalCount(
  player: RosterPlayer,
): number {
  const pa = rosterPersonalitySignals(player);
  if (!pa) return 0;
  return MENTORING_ATTR_SIGNAL_KEYS.filter((key) => {
    const raw = pa[key];
    return raw != null && Number.isFinite(raw);
  }).length;
}

export function hasMentoringAttrSignals(player: RosterPlayer): boolean {
  return mentoringAttrSignalCount(player) >= MENTORING_ATTR_SIGNAL_MIN;
}

export function isLoanClassificationKnown(player: RosterPlayer): boolean {
  const status = player.loan?.status;
  return status === "atClub" || status === "loanedOut" || status === "loanedIn";
}

export function playerExtractTrust(player: RosterPlayer): ExtractTrustFlags {
  const nameResolved = isRosterNameResolved(player.name);
  const attrsEnough = hasMentoringAttrSignals(player);
  const loanKnown = isLoanClassificationKnown(player);
  return {
    nameResolved,
    attrsEnough,
    loanKnown,
    mentoringReady: nameResolved && attrsEnough,
  };
}

export function isMentoringCompleteEnough(player: RosterPlayer): boolean {
  return playerExtractTrust(player).mentoringReady;
}

/**
 * At-club Mentoring Suggest pool: named + enough attrs, never loanedOut.
 * Unknown loan is still visible in the summary; Suggest does not seat
 * nameless / attr-short rows.
 */
export function mentoringSuggestPool(
  players: readonly RosterPlayer[],
): RosterPlayer[] {
  return players.filter(
    (player) =>
      player.loan?.status !== "loanedOut" && isMentoringCompleteEnough(player),
  );
}

export function extractTrustHoles(flags: ExtractTrustFlags): string[] {
  const holes: string[] = [];
  if (!flags.nameResolved) holes.push("name missing");
  if (!flags.attrsEnough) holes.push("attrs short of mentoring bar");
  if (!flags.loanKnown) holes.push("loan unclassified");
  return holes;
}

export function summarizeExtractTrust(
  players: readonly RosterPlayer[],
): ExtractTrustSummary {
  let mentoringReady = 0;
  let extractComplete = 0;
  let missingName = 0;
  let attrsShort = 0;
  let loanUnknown = 0;
  for (const player of players) {
    const flags = playerExtractTrust(player);
    if (flags.mentoringReady) mentoringReady += 1;
    if (flags.nameResolved && flags.attrsEnough && flags.loanKnown) {
      extractComplete += 1;
    }
    if (!flags.nameResolved) missingName += 1;
    if (!flags.attrsEnough) attrsShort += 1;
    if (!flags.loanKnown) loanUnknown += 1;
  }
  return {
    total: players.length,
    mentoringReady,
    extractComplete,
    missingName,
    attrsShort,
    loanUnknown,
  };
}

export function formatExtractTrustStatus(summary: ExtractTrustSummary): string {
  if (summary.total === 0) return "";
  const holes: string[] = [];
  if (summary.missingName) holes.push(`${summary.missingName} name missing`);
  if (summary.attrsShort) holes.push(`${summary.attrsShort} attrs short`);
  if (summary.loanUnknown) {
    holes.push(`${summary.loanUnknown} loan unclassified`);
  }
  const ready = `${summary.mentoringReady}/${summary.total} mentoring-ready`;
  return holes.length ? `${ready} · ${holes.join(" · ")}` : `${ready}`;
}
