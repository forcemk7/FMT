"use client";

import type { LivePlayer } from "@/domain/adapters";
import {
  formatDelta,
  type SquadMoverChange,
} from "@/domain/attribute-history";
import { attributeDeltaTone } from "@/domain/attribute-tone";
import { formatPlayerPositions } from "@/domain/live-data";
import { formatHasScore, hasBand, type HasTone } from "@/domain/has-score";
import type { SquadProspect } from "@/domain/squad-prospects";
import { HasBreakdownGridFromPlayer } from "@/components/has-breakdown-grid";
import { PlayerFace } from "@/components/player-face";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export function DashHasRow({
  player,
  score,
  onOpen,
  compact,
}: {
  player: LivePlayer;
  score: number;
  onOpen: (id: string) => void;
  compact?: boolean;
}) {
  const tone: HasTone = hasBand(score);
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
      <span className={`dash-has-score tone-${tone}`}>{formatHasScore(score)}</span>
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
  const shown = changes.slice(0, peek ? 2 : 4);
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
}: {
  row: SquadProspect;
  onOpen: (id: string) => void;
  compact?: boolean;
}) {
  const { player, pa, professionalism, mentor, mentorPro, proGap } = row;
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
          {player.age != null ? `Age ${player.age} · ` : ""}
          PA {Math.round(pa)}
          {compact ? ` · Pro ${professionalism}→${mentorPro}` : null}
        </small>
        {!compact ? (
          <small className="dash-prospect-mentor">
            Pro {professionalism} → {mentor.name} (+{proGap}, {mentorPro})
          </small>
        ) : null}
      </span>
    </button>
  );
}
