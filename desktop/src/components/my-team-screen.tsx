"use client";

import { useMemo, useState, type ReactNode } from "react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import { abilityToneFromScore } from "@/domain/attribute-tone";
import { formatHasScore, hasBand, liveHasScore } from "@/domain/has-score";
import {
  countAtClubSquadUnit,
  formatPlayerPositions,
  gmAdvice,
  groupSquad,
  isAtClubSquadPlayer,
  isHoydProspect,
  isLoanedOutSquadPlayer,
  positionGroups,
  squadMedianCA,
  type GmAdvice,
  type SquadUnit,
} from "@/domain/live-data";
import { ClubLogo } from "@/components/club-logo";
import { LiveDataState } from "@/components/live-data-state";
import { HasBreakdownGridFromPlayer } from "@/components/has-breakdown-grid";
import { PlayerFace } from "@/components/player-face";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const CARD_RING_SIZE = 28;
const CARD_RING_STROKE = 1.25;

export type SquadDeskMode = "at-club" | "loaned-out" | "move-on" | "hoyd";

const SQUAD_UNIT_TABS: Array<{ unit: SquadUnit; label: string }> = [
  { unit: "firstTeam", label: "First Team" },
  { unit: "under19s", label: "Under 19s" },
];

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
  const safeValue = value == null ? 0 : Math.max(0, Math.min(200, value));
  const tone = value == null || !Number.isFinite(value) ? "unknown" : abilityToneFromScore(value);
  return (
    <SquadMetricRing
      display={value ?? "—"}
      progress={value == null ? 0 : safeValue / 200}
      tone={tone}
    />
  );
}

function PersonalityRing({ value }: { value: number | null }) {
  const safeValue = value == null ? 0 : Math.max(0, Math.min(20, value));
  const tone = value == null || !Number.isFinite(value) ? "unknown" : hasBand(value);
  return (
    <SquadMetricRing
      display={formatHasScore(value)}
      progress={value == null ? 0 : safeValue / 20}
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
}: {
  player: LivePlayer;
  onOpenPlayer: (id: string) => void;
  showLoanClub?: boolean;
}) {
  const has = liveHasScore(player);
  const foot = preferredFootDisplay(player);
  const ageLine =
    player.age == null ? "—" : `${player.age} years old`;
  const loanClubName = showLoanClub
    ? player.loanClubName?.trim() || "On loan"
    : null;
  const loanClubId = showLoanClub ? player.loanClubId?.trim() || null : null;
  return (
    <button type="button" className="squad-player-card" onClick={() => onOpenPlayer(player.id)}>
      <span className="squad-player-card-face">
        <PlayerFace playerId={player.id} name={player.name} size="sm" highResolution />
        {loanClubName ? (
          <Tooltip>
            <TooltipTrigger
              render={
                <span
                  className="squad-loan-club-badge"
                  tabIndex={-1}
                  aria-label={`Loan club: ${loanClubName}`}
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => event.stopPropagation()}
                >
                  {loanClubId ? (
                    <ClubLogo clubId={loanClubId} name={loanClubName} size="sm" />
                  ) : (
                    <span className="club-logo club-logo-sm club-logo-empty" aria-hidden="true" />
                  )}
                </span>
              }
            />
            <TooltipContent side="bottom" align="center" className="squad-metric-tooltip">
              <strong>Loan Club</strong>
              <span>{loanClubName}</span>
            </TooltipContent>
          </Tooltip>
        ) : null}
      </span>
      <span className="squad-player-card-copy">
        <strong title={player.name}>{player.name}</strong>
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
  const [squadUnit, setSquadUnit] = useState<SquadUnit>("firstTeam");
  const atClub = useMemo(
    () =>
      snapshot.players.filter((player) =>
        isAtClubSquadPlayer(
          player,
          snapshot.managedClubId,
          squadDeskMode ? squadUnit : "firstTeam",
        ),
      ),
    [snapshot.managedClubId, snapshot.players, squadDeskMode, squadUnit],
  );
  const squadUnitCounts = useMemo(
    () =>
      SQUAD_UNIT_TABS.map(({ unit }) => ({
        unit,
        count: countAtClubSquadUnit(snapshot.players, snapshot.managedClubId, unit),
      })),
    [snapshot.managedClubId, snapshot.players],
  );
  const medianCA = useMemo(
    () => (moveOnMode || hoydMode ? squadMedianCA(atClub) : null),
    [atClub, hoydMode, moveOnMode],
  );
  const gmByAdvice = useMemo(() => {
    const empty: Record<GmAdvice, LivePlayer[]> = { sell: [], loan: [] };
    if (!moveOnMode || medianCA == null) return empty;
    for (const player of atClub) {
      const advice = gmAdvice(player, medianCA);
      if (advice) empty[advice].push(player);
    }
    return empty;
  }, [atClub, medianCA, moveOnMode]);
  const hoydProspects = useMemo(() => {
    if (!hoydMode || medianCA == null) return [];
    return atClub.filter((player) => isHoydProspect(player, medianCA));
  }, [atClub, hoydMode, medianCA]);
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
            : atClub,
    [atClub, gmByAdvice.loan, gmByAdvice.sell, hoydMode, hoydProspects, loanedMode, moveOnMode, snapshot.managedClubId, snapshot.players],
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
        : "First Team · Under 19s — load when FM26 has a save open";
  const activeUnitLabel =
    SQUAD_UNIT_TABS.find((tab) => tab.unit === squadUnit)?.label ?? "Squad";
  const medianLabel =
    medianCA == null ? null : Number.isInteger(medianCA) ? String(medianCA) : medianCA.toFixed(1);
  const readyBlurb = loanedMode
    ? `${managedClub?.name} · ${squad.length} out on loan`
    : moveOnMode
      ? `${managedClub?.name} · squad median CA ${medianLabel ?? "—"} · ${gmByAdvice.sell.length} sell · ${gmByAdvice.loan.length} loan`
      : hoydMode
        ? `${managedClub?.name} · squad median CA ${medianLabel ?? "—"} · ${squad.length} to groom`
        : `${managedClub?.name} · ${activeUnitLabel} · ${squad.length} at club`;
  const emptyConnectedMessage = loanedMode
    ? "No players out on loan."
    : moveOnMode
      ? "No Sell or Loan candidates vs squad median CA."
      : hoydMode
        ? "No high-PA groom prospects (age ≤24) vs squad median CA."
        : squadUnit === "under19s"
          ? "No Under 19s at club loaded yet — check FM squad screen vs FMT read."
          : null;

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
                onOpenPlayer={onOpenPlayer}
                showLoanClub={showLoanClub}
              />
            ))}
          </div>
        </section>
      );
    });
  }

  return (
    <main
      className={`screen my-team-screen${loanedMode ? " is-loans-desk" : ""}${moveOnMode ? " is-gm-desk" : ""}${hoydMode ? " is-hoyd-desk" : ""}`}
    >
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
      {squadDeskMode && connected ? (
        <div className="squad-unit-tabs" role="tablist" aria-label="Squad unit">
          {SQUAD_UNIT_TABS.map(({ unit, label }) => {
            const count =
              squadUnitCounts.find((entry) => entry.unit === unit)?.count ?? 0;
            const active = squadUnit === unit;
            return (
              <button
                key={unit}
                type="button"
                role="tab"
                aria-selected={active}
                className={`squad-unit-tab${active ? " is-active" : ""}`}
                onClick={() => setSquadUnit(unit)}
              >
                {label}
                <span className="squad-unit-tab-count">{count}</span>
              </button>
            );
          })}
        </div>
      ) : null}
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
