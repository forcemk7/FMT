"use client";

import type { LiveClubTeam, LivePlayer } from "@/domain/adapters";
import {
  formatDelta,
  type SquadMoverChange,
} from "@/domain/attribute-history";
import { attributeDeltaTone } from "@/domain/attribute-tone";
import { formatPlayerPositions, squadTeamDisplayName } from "@/domain/live-data";
import {
  dashPersonalityHighlights,
  formatHasScore,
  hasBand,
  type HasTone,
} from "@/domain/has-score";
import type { SquadProspect } from "@/domain/squad-prospects";
import type { MatchExperienceOpportunity } from "@/domain/match-experience-opportunities";
import { HasBreakdownGridFromPlayer } from "@/components/has-breakdown-grid";
import { ClubLogo } from "@/components/club-logo";
import { PlayerFace } from "@/components/player-face";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

function abilityLabel(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? String(Math.round(value)) : "—";
}

export function DashHasRow({
  player,
  score,
  onOpen,
  compact,
  highlight = "top",
}: {
  player: LivePlayer;
  score: number;
  onOpen: (id: string) => void;
  compact?: boolean;
  highlight?: "top" | "bottom";
}) {
  const tone: HasTone = hasBand(score);
  const chips = dashPersonalityHighlights(player, highlight, 3);
  const row = (
    <button
      type="button"
      className={compact ? "dash-peek-row" : "dash-has-card"}
      onClick={() => onOpen(player.id)}
    >
      <PlayerFace playerId={player.id} name={player.name} size="sm" />
      <span className="dash-has-card-copy">
        <strong>{player.name}</strong>
        {!compact ? <small>{formatPlayerPositions(player)}</small> : null}
      </span>
      <span className="dash-has-right">
        <span className="dash-personality-chips">
          {chips.map((chip) => (
            <span
              key={chip.label}
              className={`dash-personality-chip attr-tone attr-tone-${chip.tone}`}
              title={`${chip.label} ${chip.value}`}
            >
              {chip.abbr.toUpperCase()} {chip.value}
            </span>
          ))}
        </span>
        <span className={`dash-has-score tone-${tone}`}>{formatHasScore(score)}</span>
      </span>
    </button>
  );

  if (compact) return row;

  return (
    <Tooltip>
      <TooltipTrigger render={row} />
      <TooltipContent side="bottom" align="start" className="dash-has-tooltip">
        <HasBreakdownGridFromPlayer player={player} />
      </TooltipContent>
    </Tooltip>
  );
}

function MoverChangeChips({
  changes,
  peek,
}: {
  changes: SquadMoverChange[];
  peek?: boolean;
}) {
  const shownCount = peek ? 3 : 4;
  const shown = changes.slice(0, shownCount);
  const extra = changes.length - shown.length;
  return (
    <span className="dash-mover-chips">
      {shown.map((change) => {
        const tone = attributeDeltaTone(change.field, change.delta) ?? "mid";
        return (
          <span
            key={change.field}
            className={`dash-mover-chip attr-tone attr-tone-${tone}`}
            title={`${change.field} ${formatDelta(change.delta)}`}
          >
            <small>{change.field}</small> {formatDelta(change.delta)}
          </span>
        );
      })}
      {extra > 0 ? <span className="dash-mover-chip is-more">+{extra}</span> : null}
    </span>
  );
}

export function DashMoverRow({
  player,
  changes,
  onOpen,
  compact,
}: {
  player: LivePlayer;
  changes: SquadMoverChange[];
  onOpen: (id: string) => void;
  compact?: boolean;
}) {
  return (
    <button
      type="button"
      className={compact ? "dash-peek-row dash-mover-card" : "dash-has-card dash-mover-card"}
      onClick={() => onOpen(player.id)}
    >
      <PlayerFace playerId={player.id} name={player.name} size="sm" />
      <span className="dash-has-card-copy">
        <strong>{player.name}</strong>
        {!compact ? <small>{formatPlayerPositions(player)}</small> : null}
      </span>
      <MoverChangeChips changes={changes} peek={compact} />
    </button>
  );
}

export function DashProspectRow({
  row,
  onOpen,
  compact,
  clubTeams,
  managedClubName,
}: {
  row: SquadProspect;
  onOpen: (id: string) => void;
  compact?: boolean;
  clubTeams?: LiveClubTeam[];
  managedClubName?: string | null;
}) {
  const { player, pa, professionalism, mentor, mentorPro, proGap } = row;
  const ca = player.currentAbility;
  const team = clubTeams?.find((item) => item.teamUid === player.squadTeamUid);
  const teamLabel = team
    ? squadTeamDisplayName(team, managedClubName)
    : player.squadUnit === "under19s"
      ? "Under 19s"
      : player.squadUnit === "reserves"
        ? "Reserves"
        : null;

  return (
    <button
      type="button"
      className={compact ? "dash-peek-row dash-prospect-card" : "dash-has-card dash-prospect-card"}
      onClick={() => onOpen(player.id)}
    >
      <PlayerFace playerId={player.id} name={player.name} size="sm" />
      <span className="dash-has-card-copy">
        <strong>{player.name}</strong>
        <small>
          {player.age != null ? `Age ${player.age}` : null}
          {!compact ? (
            <>
              {player.age != null ? " · " : null}
              Pro {professionalism} → {mentor.name} (+{proGap}, {mentorPro})
            </>
          ) : null}
        </small>
      </span>
      <span className="dash-prospect-right">
        {teamLabel ? <span className="dash-prospect-team">{teamLabel}</span> : null}
        <span className="dash-prospect-ability">
          <abbr title="Current ability">CA</abbr> {abilityLabel(ca)}
          <span aria-hidden="true">·</span>
          <abbr title="Potential ability">PA</abbr> {abilityLabel(pa)}
        </span>
      </span>
    </button>
  );
}

export function DashMatchExperienceRow({
  row,
  onOpen,
  compact,
}: {
  row: MatchExperienceOpportunity;
  onOpen: (id: string) => void;
  compact?: boolean;
}) {
  const {
    player,
    position,
    focusRank,
    fromClubName,
    fromTeamLabel,
    fromClubId,
    toClubName,
    toTeamLabel,
    toClubId,
  } = row;
  const moveTitle = `${fromClubName} · ${fromTeamLabel} → ${toClubName} · ${toTeamLabel}`;

  return (
    <button
      type="button"
      className={
        compact ? "dash-peek-row dash-me-opportunity-card" : "dash-has-card dash-me-opportunity-card"
      }
      onClick={() => onOpen(player.id)}
      title={moveTitle}
    >
      <PlayerFace playerId={player.id} name={player.name} size="sm" />
      <span className="dash-has-card-copy">
        <strong>{player.name}</strong>
        {!compact ? <small>{formatPlayerPositions(player)}</small> : null}
      </span>
      <span className="dash-me-move-rail" aria-label={moveTitle}>
        <span className="dash-me-move-side">
          {fromClubId ? <ClubLogo clubId={fromClubId} name={fromClubName} size="sm" /> : null}
          <span className="dash-me-move-type">{fromTeamLabel}</span>
        </span>
        <span className="dash-me-move-arrow" aria-hidden="true">
          →
        </span>
        <span className="dash-me-move-side">
          {toClubId ? <ClubLogo clubId={toClubId} name={toClubName} size="sm" /> : null}
          <span className="dash-me-move-type">{toTeamLabel}</span>
          <span className="dash-me-opportunity-rank">
            #{focusRank} {position}
          </span>
        </span>
      </span>
    </button>
  );
}
