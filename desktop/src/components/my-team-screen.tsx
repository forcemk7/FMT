"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import { abilityProgress, abilityToneFromScore } from "@/domain/attribute-tone";
import { formatHasScore, hasBand, hasProgress, liveHasScore } from "@/domain/has-score";
import {
  formatPlayerPositions,
  gmAdvice,
  groupSquad,
  countSquadTeamRoster,
  isAtClubEmployee,
  isHoydProspect,
  isLoanedOutSquadPlayer,
  isOnClubTeamRosterPlayer,
  playerMatchesSquadRosterFilters,
  positionGroups,
  sortClubTeamsForSquadDesk,
  squadMedianCA,
  squadRosterStatus,
  squadTeamTabLabel,
  type GmAdvice,
  type SquadRosterStatus,
  type SquadTeamRosterCounts,
} from "@/domain/live-data";
import {
  clearSquadDeskRosterFilters,
  getSquadDeskRosterFilters,
  getSquadDeskSelectedTeamUid,
  restoreSquadScrollToMain,
  setSquadDeskRosterFilters,
  setSquadDeskScrollTop,
  setSquadDeskSelectedTeamUid,
  stashSquadScroll,
  unfreezeSquadScroll,
  writeAppMainScrollTop,
} from "@/domain/squad-desk-session";
import { ClubLogo } from "@/components/club-logo";
import { LiveDataState } from "@/components/live-data-state";
import { HasBreakdownGridFromPlayer } from "@/components/has-breakdown-grid";
import { PlayerFace } from "@/components/player-face";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const CARD_RING_SIZE = 28;
const CARD_RING_STROKE = 1.25;

export type SquadDeskMode = "at-club" | "loaned-out" | "move-on" | "hoyd";

const SQUAD_ROSTER_FILTER_OPTIONS: Array<{
  status: SquadRosterStatus;
  label: string;
  countKey: keyof SquadTeamRosterCounts;
}> = [
  { status: "atClub", label: "At club", countKey: "atClub" },
  { status: "loanedIn", label: "On loan", countKey: "loanedIn" },
  { status: "loanedOut", label: "Loaned out", countKey: "loanedOut" },
];

/** Default: At club when present; else first available. Multi-select after that. */
function defaultEnabledRosterStatuses(
  counts: SquadTeamRosterCounts,
): Set<SquadRosterStatus> {
  const next = new Set<SquadRosterStatus>();
  if (counts.atClub > 0) next.add("atClub");
  if (next.size === 0) {
    for (const { status, countKey } of SQUAD_ROSTER_FILTER_OPTIONS) {
      if (counts[countKey] > 0) next.add(status);
    }
  }
  return next;
}

function resolveEnabledRosterStatuses(
  teamUid: string,
  counts: SquadTeamRosterCounts,
): Set<SquadRosterStatus> {
  const available = new Set(
    SQUAD_ROSTER_FILTER_OPTIONS.filter(
      ({ countKey }) => counts[countKey] > 0,
    ).map(({ status }) => status),
  );
  const remembered = getSquadDeskRosterFilters(teamUid);
  if (remembered?.length) {
    const kept = new Set(
      remembered.filter((status): status is SquadRosterStatus =>
        available.has(status),
      ),
    );
    if (kept.size > 0) return kept;
  }
  return defaultEnabledRosterStatuses(counts);
}

const GM_ADVICE_LANES: Array<{ advice: GmAdvice; title: string; empty: string }> = [
  { advice: "sell", title: "Sell", empty: "No sell candidates." },
  { advice: "loan", title: "Loan", empty: "No loan candidates." },
];

function sortByCurrentAbility(players: LivePlayer[]) {
  return [...players].sort((a, b) => {
    const ca = a.currentAbility ?? -Infinity;
    const cb = b.currentAbility ?? -Infinity;
    if (cb !== ca) return cb - ca;
    return a.name.localeCompare(b.name);
  });
}

function sortByPotentialAbility(players: LivePlayer[]) {
  return [...players].sort((a, b) => {
    const pa = a.potentialAbility ?? -Infinity;
    const pb = b.potentialAbility ?? -Infinity;
    if (pb !== pa) return pb - pa;
    return a.name.localeCompare(b.name);
  });
}

function SquadMetricRing({
  display,
  progress,
  tone,
}: {
  display: string | number;
  progress: number;
  tone: string;
}) {
  const size = CARD_RING_SIZE;
  const r = (size - CARD_RING_STROKE) / 2;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, progress));
  const dashOffset = circumference * (1 - clamped);

  return (
    <span
      className={`squad-metric-ring ability-ring-${tone}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          className="squad-metric-ring-track"
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={CARD_RING_STROKE}
          strokeLinecap="round"
        />
        <circle
          className="squad-metric-ring-value"
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={CARD_RING_STROKE}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className={`squad-metric-ring-label${tone === "unknown" ? " is-unknown" : ""}`}>
        {display}
      </span>
    </span>
  );
}

function AbilityRing({ value }: { value: number | null | undefined }) {
  const tone = value == null || !Number.isFinite(value) ? "unknown" : abilityToneFromScore(value);
  return (
    <SquadMetricRing
      display={value ?? "—"}
      progress={value == null ? 0 : abilityProgress(value)}
      tone={tone}
    />
  );
}

function PersonalityRing({ value }: { value: number | null }) {
  const tone = value == null || !Number.isFinite(value) ? "unknown" : hasBand(value);
  return (
    <SquadMetricRing
      display={formatHasScore(value)}
      progress={value == null ? 0 : hasProgress(value)}
      tone={tone}
    />
  );
}

function preferredFootDisplay(player: LivePlayer) {
  const pref = player.preferredFoot;
  if (!pref) return "—";
  if (/either/i.test(pref)) return "Either";
  if (/left/i.test(pref)) return "Left Foot";
  if (/right/i.test(pref)) return "Right Foot";
  return pref;
}

function MetricTip({
  label,
  detail,
  children,
}: {
  label: string;
  detail?: string;
  children: ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span
            className="squad-metric-tip"
            tabIndex={-1}
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
          >
            {children}
          </span>
        }
      />
      <TooltipContent side="top" className="squad-metric-tooltip">
        <strong>{label}</strong>
        {detail ? <span>{detail}</span> : null}
      </TooltipContent>
    </Tooltip>
  );
}

function SquadPlayerCard({
  player,
  onOpenPlayer,
  showLoanClub,
  rosterStatus,
}: {
  player: LivePlayer;
  onOpenPlayer: (id: string) => void;
  showLoanClub?: boolean;
  rosterStatus?: "atClub" | "loanedIn" | "loanedOut" | null;
}) {
  const has = liveHasScore(player);
  const foot = preferredFootDisplay(player);
  const ageLine =
    player.age == null ? "—" : `${player.age} years old`;
  const isLoanedOut =
    rosterStatus === "loanedOut" || player.loanedOut === true;
  const isLoanedIn =
    rosterStatus === "loanedIn" || player.loanedIn === true;
  const showLoanBadge = showLoanClub === true || isLoanedOut;
  const loanClubName = showLoanBadge
    ? player.loanClubName?.trim() || "On loan"
    : null;
  const loanClubId = showLoanBadge ? player.loanClubId?.trim() || null : null;
  const employerClubName = isLoanedIn
    ? player.employerClubName?.trim() || "Loan in"
    : null;
  const employerClubId = isLoanedIn ? player.employerClubId?.trim() || null : null;
  const nameClass = isLoanedIn ? "squad-player-name-loaned-in" : undefined;
  const faceBadge = loanClubName
    ? { kind: "loan-out" as const, clubId: loanClubId, clubName: loanClubName }
    : employerClubName
      ? { kind: "loan-in" as const, clubId: employerClubId, clubName: employerClubName }
      : null;
  return (
    <button type="button" className="squad-player-card" onClick={() => onOpenPlayer(player.id)}>
      <span className="squad-player-card-face">
        <PlayerFace playerId={player.id} name={player.name} size="sm" highResolution />
        {faceBadge ? (
          <Tooltip>
            <TooltipTrigger
              render={
                <span
                  className={`squad-loan-club-badge${faceBadge.kind === "loan-in" ? " is-loan-in" : ""}`}
                  tabIndex={-1}
                  aria-label={
                    faceBadge.kind === "loan-in"
                      ? `Parent club: ${faceBadge.clubName}`
                      : `Loan club: ${faceBadge.clubName}`
                  }
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => event.stopPropagation()}
                >
                  {faceBadge.clubId ? (
                    <ClubLogo clubId={faceBadge.clubId} name={faceBadge.clubName} size="sm" />
                  ) : (
                    <span className="club-logo club-logo-sm club-logo-empty" aria-hidden="true" />
                  )}
                </span>
              }
            />
            <TooltipContent side="bottom" align="center" className="squad-metric-tooltip">
              <strong>{faceBadge.kind === "loan-in" ? "Parent club" : "Loan club"}</strong>
              <span>{faceBadge.clubName}</span>
            </TooltipContent>
          </Tooltip>
        ) : null}
      </span>
      <span className="squad-player-card-copy">
        <strong className={nameClass} title={player.name}>{player.name}</strong>
        <span>{ageLine}</span>
        <span className="squad-player-card-pos">{formatPlayerPositions(player)}</span>
        <span>{foot}</span>
      </span>
      <span className="squad-player-card-metrics" aria-label="Ability, potential, personality">
        <MetricTip label="Ability" detail="Current ability (CA)">
          <AbilityRing value={player.currentAbility} />
        </MetricTip>
        <MetricTip label="Potential" detail="Potential ability (PA)">
          <AbilityRing value={player.potentialAbility} />
        </MetricTip>
        <Tooltip>
          <TooltipTrigger
            render={
              <span
                className="squad-metric-tip"
                tabIndex={-1}
                onClick={(event) => event.stopPropagation()}
                onKeyDown={(event) => event.stopPropagation()}
              >
                <PersonalityRing value={has} />
              </span>
            }
          />
          <TooltipContent side="top" align="end" className="dash-has-tooltip squad-metric-tooltip-wide">
            <strong>Personality (HAS)</strong>
            <HasBreakdownGridFromPlayer player={player} />
          </TooltipContent>
        </Tooltip>
      </span>
    </button>
  );
}

export function MyTeamScreen({
  snapshot,
  checking,
  onRefresh,
  onOpenPlayer,
  mode = "at-club",
}: {
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  onOpenPlayer: (playerId: string) => void;
  mode?: SquadDeskMode;
}) {
  const loanedMode = mode === "loaned-out";
  const moveOnMode = mode === "move-on";
  const hoydMode = mode === "hoyd";
  const squadDeskMode = !loanedMode && !moveOnMode && !hoydMode;
  const clubTeams = useMemo(
    () =>
      sortClubTeamsForSquadDesk(
        (snapshot.clubTeams ?? []).filter(
          (team) => team.rosterLen > 0 || team.isManagerTeam,
        ),
      ),
    [snapshot.clubTeams],
  );
  const managedClubName = useMemo(() => {
    const clubId = snapshot.managedClubId;
    if (!clubId) return null;
    return snapshot.clubs.find((club) => club.id === clubId)?.name ?? null;
  }, [snapshot.clubs, snapshot.managedClubId]);
  const rosterCountsByTeamUid = useMemo(() => {
    const counts = new Map<string, ReturnType<typeof countSquadTeamRoster>>();
    for (const team of clubTeams) {
      counts.set(
        team.teamUid,
        countSquadTeamRoster(snapshot.players, snapshot.managedClubId, team.teamUid),
      );
    }
    return counts;
  }, [clubTeams, snapshot.managedClubId, snapshot.players]);
  const defaultTeamUid =
    clubTeams.find((team) => team.isManagerTeam)?.teamUid ??
    clubTeams[0]?.teamUid ??
    null;
  const [selectedTeamUid, setSelectedTeamUid] = useState<string | null>(() => {
    if (!squadDeskMode) return defaultTeamUid;
    const remembered = getSquadDeskSelectedTeamUid();
    return remembered ?? defaultTeamUid;
  });
  const [enabledRosterStatuses, setEnabledRosterStatuses] = useState(() => {
    if (!squadDeskMode) return new Set<SquadRosterStatus>(["atClub"]);
    const teamUid = getSquadDeskSelectedTeamUid() ?? defaultTeamUid;
    if (!teamUid) return new Set<SquadRosterStatus>(["atClub"]);
    const remembered = getSquadDeskRosterFilters(teamUid);
    if (remembered?.length) {
      return new Set(remembered as SquadRosterStatus[]);
    }
    return new Set<SquadRosterStatus>(["atClub"]);
  });
  const [rosterFilterOpen, setRosterFilterOpen] = useState(false);
  const rosterFilterRef = useRef<HTMLDivElement | null>(null);
  const sessionClubIdRef = useRef(snapshot.managedClubId);
  useEffect(() => {
    if (sessionClubIdRef.current === snapshot.managedClubId) return;
    sessionClubIdRef.current = snapshot.managedClubId;
    clearSquadDeskRosterFilters();
  }, [snapshot.managedClubId]);
  useEffect(() => {
    if (!rosterFilterOpen) return;
    const onPointer = (event: MouseEvent) => {
      if (!(event.target instanceof Node)) return;
      if (rosterFilterRef.current?.contains(event.target)) return;
      setRosterFilterOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setRosterFilterOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [rosterFilterOpen]);
  useEffect(() => {
    setSelectedTeamUid((current) => {
      const candidate =
        current && clubTeams.some((team) => team.teamUid === current)
          ? current
          : squadDeskMode
            ? getSquadDeskSelectedTeamUid()
            : null;
      if (candidate && clubTeams.some((team) => team.teamUid === candidate)) {
        return candidate;
      }
      return defaultTeamUid;
    });
  }, [clubTeams, defaultTeamUid, squadDeskMode]);
  useEffect(() => {
    if (!squadDeskMode) return;
    setSquadDeskSelectedTeamUid(selectedTeamUid);
  }, [selectedTeamUid, squadDeskMode]);
  useLayoutEffect(() => {
    if (!squadDeskMode) return;
    return restoreSquadScrollToMain();
  }, [squadDeskMode]);
  useEffect(() => {
    if (!squadDeskMode) return;
    const main = document.querySelector(".app-main");
    if (!(main instanceof HTMLElement)) return;
    const onScroll = () => setSquadDeskScrollTop(main.scrollTop);
    main.addEventListener("scroll", onScroll, { passive: true });
    // Do not re-read scroll on unmount — Profile content may have already
    // clamped `.app-main` to 0 and would wipe the stash.
    return () => main.removeEventListener("scroll", onScroll);
  }, [squadDeskMode]);
  const selectedTeam =
    clubTeams.find((team) => team.teamUid === selectedTeamUid) ?? clubTeams[0] ?? null;
  const selectedTeamCounts =
    (selectedTeam
      ? rosterCountsByTeamUid.get(selectedTeam.teamUid)
      : null) ?? { atClub: 0, loanedIn: 0, loanedOut: 0 };
  const availableRosterFilters = useMemo(
    () =>
      SQUAD_ROSTER_FILTER_OPTIONS.filter(
        ({ countKey }) => selectedTeamCounts[countKey] > 0,
      ),
    [
      selectedTeamCounts.atClub,
      selectedTeamCounts.loanedIn,
      selectedTeamCounts.loanedOut,
    ],
  );
  useEffect(() => {
    if (!squadDeskMode || !selectedTeam) return;
    const next = resolveEnabledRosterStatuses(
      selectedTeam.teamUid,
      selectedTeamCounts,
    );
    setEnabledRosterStatuses(next);
    if (next.size > 0) {
      setSquadDeskRosterFilters(selectedTeam.teamUid, next);
    }
  }, [
    squadDeskMode,
    selectedTeam?.teamUid,
    selectedTeamCounts.atClub,
    selectedTeamCounts.loanedIn,
    selectedTeamCounts.loanedOut,
  ]);
  const teamRoster = useMemo(
    () =>
      snapshot.players.filter((player) => {
        if (squadDeskMode && selectedTeam) {
          if (
            !isOnClubTeamRosterPlayer(
              player,
              snapshot.managedClubId,
              selectedTeam.teamUid,
            )
          ) {
            return false;
          }
          return playerMatchesSquadRosterFilters(
            player,
            snapshot.managedClubId,
            enabledRosterStatuses,
          );
        }
        return isAtClubEmployee(player, snapshot.managedClubId);
      }),
    [
      enabledRosterStatuses,
      selectedTeam,
      snapshot.managedClubId,
      snapshot.players,
      squadDeskMode,
    ],
  );
  const medianCA = useMemo(
    () => (moveOnMode || hoydMode ? squadMedianCA(teamRoster) : null),
    [teamRoster, hoydMode, moveOnMode],
  );
  const gmByAdvice = useMemo(() => {
    const empty: Record<GmAdvice, LivePlayer[]> = { sell: [], loan: [] };
    if (!moveOnMode || medianCA == null) return empty;
    for (const player of teamRoster) {
      const advice = gmAdvice(player, medianCA);
      if (advice) empty[advice].push(player);
    }
    return empty;
  }, [teamRoster, medianCA, moveOnMode]);
  const hoydProspects = useMemo(() => {
    if (!hoydMode || medianCA == null) return [];
    return teamRoster.filter((player) => isHoydProspect(player, medianCA));
  }, [teamRoster, hoydMode, medianCA]);
  const squad = useMemo(
    () =>
      loanedMode
        ? snapshot.players.filter((player) =>
            isLoanedOutSquadPlayer(player, snapshot.managedClubId),
          )
        : moveOnMode
          ? [...gmByAdvice.sell, ...gmByAdvice.loan]
          : hoydMode
            ? hoydProspects
            : teamRoster,
    [teamRoster, gmByAdvice.loan, gmByAdvice.sell, hoydMode, hoydProspects, loanedMode, moveOnMode, snapshot.managedClubId, snapshot.players],
  );
  const managedClub = snapshot.clubs.find((club) => club.id === snapshot.managedClubId);
  const connected =
    snapshot.status.state === "connected" && Boolean(snapshot.managedClubId);
  const allowEmpty = loanedMode || moveOnMode || hoydMode || (squadDeskMode && connected);
  const ready = connected && (allowEmpty || squad.length > 0);
  const title = loanedMode ? "Loans" : moveOnMode ? "GM" : hoydMode ? "HoYD" : "Squad";
  const emptyHint = loanedMode
    ? "Outgoing loans — load when FM26 has a save open"
    : moveOnMode
      ? "Sell / Loan advice — load when FM26 has a save open"
      : hoydMode
        ? "Top talent to groom (age ≤24) — load when FM26 has a save open"
        : "Load when FM26 has a save open";
  const medianLabel =
    medianCA == null ? null : Number.isInteger(medianCA) ? String(medianCA) : medianCA.toFixed(1);
  const readyBlurb = loanedMode
    ? `${managedClub?.name} · ${squad.length} out on loan`
    : moveOnMode
      ? `${managedClub?.name} · squad median CA ${medianLabel ?? "—"} · ${gmByAdvice.sell.length} sell · ${gmByAdvice.loan.length} loan`
      : hoydMode
        ? `${managedClub?.name} · squad median CA ${medianLabel ?? "—"} · ${squad.length} to groom`
        : `${managedClub?.name} · ${selectedTeam?.name.trim() || "Squad"} · ${teamRoster.length} on roster`;
  const emptyConnectedMessage = loanedMode
    ? "No players out on loan."
    : moveOnMode
      ? "No Sell or Loan candidates vs squad median CA."
      : hoydMode
        ? "No high-PA groom prospects (age ≤24) vs squad median CA."
        : selectedTeam && squad.length === 0
          ? selectedTeamCounts.atClub +
                selectedTeamCounts.loanedIn +
                selectedTeamCounts.loanedOut >
              0
            ? "No players match the selected roster filters."
            : `No players loaded for ${selectedTeam.name.trim() || "this team"} — check FM squad screen vs FMT read.`
          : null;

  function toggleRosterStatus(status: SquadRosterStatus) {
    setEnabledRosterStatuses((current) => {
      const next = new Set(current);
      if (next.has(status)) {
        const enabledVisible = availableRosterFilters.filter(({ status: option }) =>
          next.has(option),
        );
        if (enabledVisible.length <= 1) return current;
        next.delete(status);
      } else {
        next.add(status);
      }
      if (selectedTeam) {
        setSquadDeskRosterFilters(selectedTeam.teamUid, next);
      }
      return next;
    });
  }

  function openPlayerFromDesk(playerId: string) {
    if (squadDeskMode) {
      // Freeze before navigate so unmount/Profile clamp cannot clear the stash.
      stashSquadScroll();
    }
    onOpenPlayer(playerId);
  }

  function renderPositionMatrix(players: LivePlayer[], showLoanClub: boolean) {
    const byGroup = groupSquad(players);
    const sortPlayers = hoydMode ? sortByPotentialAbility : sortByCurrentAbility;
    return positionGroups.map((group) => {
      const groupPlayers = sortPlayers(byGroup.get(group) ?? []);
      if (!groupPlayers.length) return null;
      return (
        <section className="squad-position-group" key={group}>
          <header className="squad-position-head">
            <h2>{group}</h2>
            <span>{groupPlayers.length}</span>
          </header>
          <div className="squad-position-matrix">
            {groupPlayers.map((player) => (
              <SquadPlayerCard
                key={player.id}
                player={player}
                onOpenPlayer={openPlayerFromDesk}
                showLoanClub={showLoanClub}
                rosterStatus={squadRosterStatus(player, snapshot.managedClubId)}
              />
            ))}
          </div>
        </section>
      );
    });
  }

  return (
    <main
      className={`screen my-team-screen${loanedMode ? " is-loans-desk" : ""}${moveOnMode ? " is-gm-desk" : ""}${hoydMode ? " is-hoyd-desk" : ""}${squadDeskMode && connected ? " is-squad-desk-compact" : ""}`}
    >
      {squadDeskMode && connected && clubTeams.length > 0 ? (
        <div className="squad-desk-toolbar" role="toolbar" aria-label="Club teams">
          <div className="squad-unit-tabs" role="tablist" aria-label="Club teams">
            {clubTeams.map((team) => {
              const active = selectedTeam?.teamUid === team.teamUid;
              return (
                <button
                  key={team.teamUid}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={`squad-unit-tab${active ? " is-active" : ""}`}
                  onClick={() => {
                    if (team.teamUid === selectedTeamUid) return;
                    unfreezeSquadScroll();
                    setSquadDeskScrollTop(0);
                    writeAppMainScrollTop(0);
                    setRosterFilterOpen(false);
                    setSelectedTeamUid(team.teamUid);
                  }}
                >
                  {squadTeamTabLabel(
                    team,
                    managedClubName,
                    rosterCountsByTeamUid.get(team.teamUid),
                  )}
                </button>
              );
            })}
          </div>
          {availableRosterFilters.length > 0 ? (
            <div className="squad-roster-filter-menu" ref={rosterFilterRef}>
              <button
                type="button"
                className={`squad-roster-filter-trigger${rosterFilterOpen ? " is-open" : ""}`}
                aria-expanded={rosterFilterOpen}
                aria-haspopup="true"
                aria-label="Roster status filter"
                onClick={() => setRosterFilterOpen((open) => !open)}
              >
                <span>Filter</span>
                <span className="squad-roster-filter-chevron" aria-hidden>
                  ▾
                </span>
              </button>
              {rosterFilterOpen ? (
                <div
                  className="squad-roster-filter-panel"
                  role="group"
                  aria-label="Roster status"
                >
                  <div className="squad-roster-filter-section">Status</div>
                  {availableRosterFilters.map(({ status, label, countKey }) => {
                    const checked = enabledRosterStatuses.has(status);
                    const count = selectedTeamCounts[countKey];
                    const lastChecked =
                      checked &&
                      availableRosterFilters.filter(({ status: option }) =>
                        enabledRosterStatuses.has(option),
                      ).length <= 1;
                    return (
                      <button
                        key={status}
                        type="button"
                        role="checkbox"
                        aria-checked={checked}
                        aria-disabled={lastChecked}
                        disabled={lastChecked}
                        className={`squad-roster-filter-option${checked ? " is-selected" : ""}${lastChecked ? " is-locked" : ""}`}
                        onClick={() => {
                          if (lastChecked) return;
                          toggleRosterStatus(status);
                        }}
                      >
                        <span
                          className={`squad-roster-filter-check${checked ? " is-on" : ""}`}
                          aria-hidden
                        />
                        <span className="squad-roster-filter-option-label">
                          {label} <b>({count})</b>
                        </span>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="planner-heading">
          <div>
            <h1>{title}</h1>
            <p>{ready ? readyBlurb : emptyHint}</p>
          </div>
          {ready ? (
            <div className="live-source-label">
              <span className="live-dot" />
              Live
            </div>
          ) : null}
        </div>
      )}
      <section className="squad-matrix">
        {!connected ? (
          <div className="squad-table-empty">
            <LiveDataState
              snapshot={snapshot}
              title={title}
              checking={checking}
              onRefresh={onRefresh}
              compact
            />
          </div>
        ) : allowEmpty && squad.length === 0 ? (
          <div className="squad-table-empty">
            <p className="squad-loans-empty">{emptyConnectedMessage}</p>
          </div>
        ) : !ready ? (
          <div className="squad-table-empty">
            <LiveDataState
              snapshot={snapshot}
              title={title}
              checking={checking}
              onRefresh={onRefresh}
              compact
            />
          </div>
        ) : moveOnMode ? (
          GM_ADVICE_LANES.map(({ advice, title: laneTitle, empty }) => {
            const lanePlayers = gmByAdvice[advice];
            return (
              <section className="gm-advice-lane" key={advice}>
                <header className="squad-position-head">
                  <h2>{laneTitle}</h2>
                  <span>{lanePlayers.length}</span>
                </header>
                {lanePlayers.length === 0 ? (
                  <p className="squad-loans-empty">{empty}</p>
                ) : (
                  renderPositionMatrix(lanePlayers, false)
                )}
              </section>
            );
          })
        ) : (
          renderPositionMatrix(squad, loanedMode)
        )}
      </section>
    </main>
  );
}
