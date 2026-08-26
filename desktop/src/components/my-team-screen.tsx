"use client";

import { useMemo } from "react";
import { ExternalLink } from "lucide-react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import { abilityToneFromScore } from "@/domain/attribute-tone";
import { formatHasScore, hasBand, liveHasScore } from "@/domain/has-score";
import { formatPlayerPositions, groupSquad, positionGroups } from "@/domain/live-data";
import { LiveDataState } from "@/components/live-data-state";
import { PlayerFace } from "@/components/player-face";
import { Button } from "@/components/ui/button";

function shown(value: string | number | null | undefined) {
  return value == null || value === "" ? "—" : value;
}

/** Same outer size as player-face-sm; hairline SVG stroke (not conic/inset donut). */
const SQUAD_RING_SIZE = 40;
const SQUAD_RING_STROKE = 1.25;

function SquadMetricRing({
  display,
  progress,
  tone,
}: {
  display: string | number;
  progress: number;
  tone: string;
}) {
  const r = (SQUAD_RING_SIZE - SQUAD_RING_STROKE) / 2;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, progress));
  const dashOffset = circumference * (1 - clamped);
  return (
    <span className={`squad-ability-cell squad-metric-ring ability-ring-${tone}`}>
      <svg
        width={SQUAD_RING_SIZE}
        height={SQUAD_RING_SIZE}
        viewBox={`0 0 ${SQUAD_RING_SIZE} ${SQUAD_RING_SIZE}`}
        aria-hidden
      >
        <circle
          className="squad-metric-ring-track"
          cx={SQUAD_RING_SIZE / 2}
          cy={SQUAD_RING_SIZE / 2}
          r={r}
          fill="none"
          strokeWidth={SQUAD_RING_STROKE}
          strokeLinecap="round"
        />
        <circle
          className="squad-metric-ring-value"
          cx={SQUAD_RING_SIZE / 2}
          cy={SQUAD_RING_SIZE / 2}
          r={r}
          fill="none"
          strokeWidth={SQUAD_RING_STROKE}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${SQUAD_RING_SIZE / 2} ${SQUAD_RING_SIZE / 2})`}
        />
      </svg>
      <strong className={tone === "unknown" ? "attr-tone-mid" : `attr-tone-${tone}`}>{display}</strong>
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

/** HAS ring — absolute practical range + gold above practical ceiling. */
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

function footLine(player: LivePlayer) {
  const left = player.leftFoot;
  const right = player.rightFoot;
  if (left == null || right == null) {
    return player.preferredFoot ?? "—";
  }
  const side = player.preferredFoot ?? (left === right ? "Either" : left > right ? "Left" : "Right");
  return `${side} · ${left} / ${right}`;
}

function PlayerRow({ player, onOpenPlayer }: { player: LivePlayer; onOpenPlayer: (id: string) => void }) {
  const has = liveHasScore(player);
  return (
    <article className="squad-player-row squad-player-row-mapped" onClick={() => onOpenPlayer(player.id)}>
      <div className="squad-player-identity">
        <PlayerFace playerId={player.id} name={player.name} size="sm" highResolution />
        <span>
          <button type="button" className="player-name-link">{player.name}</button>
          <small>
            {shown(player.nationality)} · {shown(player.age)} yrs
          </small>
        </span>
      </div>
      <span>
        <strong>{formatPlayerPositions(player)}</strong>
        <small>{footLine(player)}</small>
      </span>
      <AbilityRing value={player.currentAbility} />
      <AbilityRing value={player.potentialAbility} />
      <PersonalityRing value={has} />
      <Button variant="outline" size="sm">
        Profile
        <ExternalLink data-icon="inline-end" />
      </Button>
    </article>
  );
}

export function MyTeamScreen({
  snapshot,
  checking,
  onRefresh,
  onOpenPlayer,
}: {
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  onOpenPlayer: (playerId: string) => void;
}) {
  const squad = useMemo(
    () => snapshot.players.filter((player) => player.clubId === snapshot.managedClubId),
    [snapshot.managedClubId, snapshot.players],
  );
  const groups = useMemo(() => groupSquad(squad), [squad]);
  const managedClub = snapshot.clubs.find((club) => club.id === snapshot.managedClubId);
  const ready = snapshot.status.state === "connected" && Boolean(snapshot.managedClubId) && squad.length > 0;

  return (
    <main className="screen my-team-screen">
      <div className="planner-heading">
        <div>
          <h1>Squad</h1>
          <p>
            {ready
              ? `${managedClub?.name} · ${squad.length} players`
              : "First-team desk — load when FM26 has a save open"}
          </p>
        </div>
        {ready ? (
          <div className="live-source-label">
            <span className="live-dot" />
            Live
          </div>
        ) : null}
      </div>
      <section className="squad-live-table squad-live-table-mapped">
        <header>
          <span>Player</span>
          <span>Position</span>
          <span>Ability</span>
          <span>Potential</span>
          <span>Personality</span>
          <span>Details</span>
        </header>
        {!ready ? (
          <div className="squad-table-empty">
            <LiveDataState
              snapshot={snapshot}
              title="Squad"
              checking={checking}
              onRefresh={onRefresh}
              compact
            />
          </div>
        ) : (
          positionGroups.map((group) => {
            const players = groups.get(group) ?? [];
            if (!players.length) return null;
            return (
              <div className="squad-position-group" key={group}>
                <h2>
                  {group}
                  <span>{players.length}</span>
                </h2>
                {players.map((player) => (
                  <PlayerRow key={player.id} player={player} onOpenPlayer={onOpenPlayer} />
                ))}
              </div>
            );
          })
        )}
      </section>
    </main>
  );
}
