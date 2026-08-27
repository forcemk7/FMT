"use client";

import { useMemo, type ReactNode } from "react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import { abilityToneFromScore } from "@/domain/attribute-tone";
import { formatHasScore, hasBand, liveHasScore } from "@/domain/has-score";
import { formatPlayerPositions, groupSquad, isAtClubSquadPlayer, isLoanedOutSquadPlayer, isMoveOnCandidate, positionGroups } from "@/domain/live-data";
import { ClubLogo } from "@/components/club-logo";
import { LiveDataState } from "@/components/live-data-state";
import { HasBreakdownGridFromPlayer } from "@/components/has-breakdown-grid";
import { PlayerFace } from "@/components/player-face";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const CARD_RING_SIZE = 28;
const CARD_RING_STROKE = 1.25;

export type SquadDeskMode = "at-club" | "loaned-out" | "move-on";

function sortByCurrentAbility(players: LivePlayer[]) {
  return [...players].sort((a, b) => {
    const ca = a.currentAbility ?? -Infinity;
    const cb = b.currentAbility ?? -Infinity;
    if (cb !== ca) return cb - ca;
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
      </span>
      <span className="squad-player-card-copy">
        <strong title={player.name}>{player.name}</strong>
        <span>{ageLine}</span>
        <span className="squad-player-card-pos">{formatPlayerPositions(player)}</span>
        <span>{foot}</span>
      </span>
      <span className="squad-player-card-side">
        {loanClubName ? (
          <span className="squad-loan-club-pill" title={loanClubName}>
            {loanClubId ? (
              <ClubLogo clubId={loanClubId} name={loanClubName} size="sm" />
            ) : (
              <span className="club-logo club-logo-sm club-logo-empty" aria-hidden="true" />
            )}
            <span className="squad-loan-club-pill-name">{loanClubName}</span>
          </span>
        ) : null}
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
  const squad = useMemo(
    () =>
      snapshot.players.filter((player) => {
        if (loanedMode) {
          return isLoanedOutSquadPlayer(player, snapshot.managedClubId);
        }
        if (!isAtClubSquadPlayer(player, snapshot.managedClubId)) return false;
        if (moveOnMode) return isMoveOnCandidate(player);
        return true;
      }),
    [loanedMode, moveOnMode, snapshot.managedClubId, snapshot.players],
  );
  const groups = useMemo(() => groupSquad(squad), [squad]);
  const managedClub = snapshot.clubs.find((club) => club.id === snapshot.managedClubId);
  const connected =
    snapshot.status.state === "connected" && Boolean(snapshot.managedClubId);
  const allowEmpty = loanedMode || moveOnMode;
  const ready = connected && (allowEmpty || squad.length > 0);
  const title = loanedMode ? "Loans" : moveOnMode ? "GM" : "Squad";
  const emptyHint = loanedMode
    ? "Outgoing loans — load when FM26 has a save open"
    : moveOnMode
      ? "Move-on queue — load when FM26 has a save open"
      : "First-team desk — load when FM26 has a save open";
  const readyBlurb = loanedMode
    ? `${managedClub?.name} · ${squad.length} out on loan`
    : moveOnMode
      ? `${managedClub?.name} · ${squad.length} to move on`
      : `${managedClub?.name} · ${squad.length} players`;
  const emptyConnectedMessage = loanedMode
    ? "No players out on loan."
    : moveOnMode
      ? "No move-on candidates (low PA + CA near PA)."
      : null;

  return (
    <main
      className={`screen my-team-screen${loanedMode ? " is-loans-desk" : ""}${moveOnMode ? " is-gm-desk" : ""}`}
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
        ) : (
          positionGroups.map((group) => {
            const players = sortByCurrentAbility(groups.get(group) ?? []);
            if (!players.length) return null;
            return (
              <section className="squad-position-group" key={group}>
                <header className="squad-position-head">
                  <h2>{group}</h2>
                  <span>{players.length}</span>
                </header>
                <div className="squad-position-matrix">
                  {players.map((player) => (
                    <SquadPlayerCard
                      key={player.id}
                      player={player}
                      onOpenPlayer={onOpenPlayer}
                      showLoanClub={loanedMode}
                    />
                  ))}
                </div>
              </section>
            );
          })
        )}
      </section>
    </main>
  );
}
