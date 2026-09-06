"use client";

import type { LiveClubTeam, LivePlayer } from "@/domain/adapters";
import {
  formatDelta,
  type SquadMoverChange,
} from "@/domain/attribute-history";
import { attributeDeltaTone } from "@/domain/attribute-tone";
import { formatPlayerPositions } from "@/domain/live-data";
import {
  dashPersonalityHighlights,
  formatHasScore,
  hasBand,
  type HasTone,
} from "@/domain/has-score";
import {
  dashClubTeamChrome,
  type SquadAbilityRank,
} from "@/domain/squad-ability-rank";
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
      <span className="dash-row-extra">
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
      </span>
      <span className={`dash-row-main dash-has-score tone-${tone}`}>{formatHasScore(score)}</span>
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
      <span className="dash-row-extra">
        <MoverChangeChips changes={changes} peek={compact} />
      </span>
      <span className="dash-row-main dash-mover-count" title={`${changes.length} attribute changes`}>
        {changes.length}
      </span>
    </button>
  );
}

export function DashAbilityRow({
  row,
  mode,
  onOpen,
  compact,
  clubTeams,
  clubs,
}: {
  row: SquadAbilityRank;
  mode: "players" | "talent";
  onOpen: (id: string) => void;
  compact?: boolean;
  clubTeams?: LiveClubTeam[];
  clubs?: Array<{ id: string; name: string }>;
}) {
  const { player, ca, pa } = row;
  const chrome = dashClubTeamChrome(player, clubTeams ?? [], clubs ?? []);
  const secondary =
    mode === "players" ? (
      <>
        <abbr title="Potential ability">PA</abbr> {abilityLabel(pa)}
      </>
    ) : (
      <>
        <abbr title="Current ability">CA</abbr> {abilityLabel(ca)}
      </>
    );
  const main =
    mode === "players" ? (
      <>
        <abbr title="Current ability">CA</abbr> {abilityLabel(ca)}
      </>
    ) : (
      <>
        <abbr title="Potential ability">PA</abbr> {abilityLabel(pa)}
      </>
    );

  return (
    <button
      type="button"
      className={compact ? "dash-peek-row dash-ability-card" : "dash-has-card dash-ability-card"}
      onClick={() => onOpen(player.id)}
    >
      <PlayerFace playerId={player.id} name={player.name} size="sm" />
      <span className="dash-has-card-copy">
        <strong>{player.name}</strong>
        {!compact && player.age != null ? <small>Age {player.age}</small> : null}
      </span>
      <span className="dash-row-extra dash-ability-extra">
        {chrome ? (
          <span className="dash-ability-team" title={`${chrome.clubName} ${chrome.teamType}`}>
            {chrome.clubId ? (
              <ClubLogo clubId={chrome.clubId} name={chrome.clubName} size="sm" />
            ) : (
              <span className="club-logo club-logo-sm club-logo-empty" aria-hidden="true" />
            )}
            <span className="dash-ability-team-type">{chrome.teamType}</span>
          </span>
        ) : null}
        <span className="dash-ability-secondary">{secondary}</span>
      </span>
      <span className="dash-row-main dash-ability-main">{main}</span>
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
      <span className="dash-row-extra dash-me-move-rail" aria-label={moveTitle}>
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
        </span>
      </span>
      <span className="dash-row-main dash-me-opportunity-rank">
        #{focusRank} {position}
      </span>
    </button>
  );
}
