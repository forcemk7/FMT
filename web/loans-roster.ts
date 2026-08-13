/**
 * Pure Loans-tab roster helpers (T005A).
 * Filters / buckets loaned-out players; no DOM or main.ts wiring.
 */

import type { RosterPlayer } from "./roster-data.ts";

export type LoansByUnitInput = {
  firstTeam: readonly RosterPlayer[];
  reserves: readonly RosterPlayer[];
  under19s: readonly RosterPlayer[];
};

export type LoansByUnit = {
  firstTeam: RosterPlayer[];
  reserves: RosterPlayer[];
  under19s: RosterPlayer[];
};

function compareName(a: RosterPlayer, b: RosterPlayer): number {
  return (a.name || "").localeCompare(b.name || "", undefined, {
    sensitivity: "base",
  });
}

/** Players with `loan.status === "loanedOut"` only (excludes loanedIn / atClub / missing). */
export function loanedOutPlayers(
  unitPlayers: readonly RosterPlayer[],
): RosterPlayer[] {
  return unitPlayers
    .filter((p) => p.loan?.status === "loanedOut")
    .slice()
    .sort(compareName);
}

/**
 * Club-wide loaned-out lists split by training unit.
 * Each unit array is name-sorted (base localeCompare). HAS ranking lives in
 * main.ts (`estimatesFromPersonalitySignals` + `hiddenQualityScore`) — not
 * duplicated here; T005 may re-sort at render if desired.
 */
export function loansByUnit(units: LoansByUnitInput): LoansByUnit {
  return {
    firstTeam: loanedOutPlayers(units.firstTeam),
    reserves: loanedOutPlayers(units.reserves),
    under19s: loanedOutPlayers(units.under19s),
  };
}

/**
 * Club id for the loan crest badge.
 * Contract matches `playerLoanBadgeClubId` in main.ts for loanedOut:
 * `loan.loanClubId` when finite; otherwise null.
 * loanedIn / atClub / missing loan → null (Loans tab only shows loanedOut).
 */
export function loanCrestClubId(player: RosterPlayer): number | null {
  const loan = player.loan;
  if (!loan || loan.status !== "loanedOut") return null;
  return loan.loanClubId != null && Number.isFinite(loan.loanClubId)
    ? loan.loanClubId
    : null;
}
