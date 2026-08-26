"use client";

import { useMemo } from "react";
import { ExternalLink } from "lucide-react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import { attributeTone } from "@/domain/attribute-tone";
import { groupSquad, positionGroups } from "@/domain/live-data";
import { LiveDataState } from "@/components/live-data-state";
import { PlayerFace } from "@/components/player-face";
import { Button } from "@/components/ui/button";

function shown(value: string | number | null | undefined) {
  return value == null || value === "" ? "—" : value;
}

function abilityRingTone(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "unknown";
  const tone = attributeTone("Ability", value / 10);
  if (tone === "good") return "strong";
  if (tone === "bad") return "poor";
  return "medium";
}

function AbilityRing({ value, label }: { value: number | null | undefined; label: string }) {
  const safeValue = value == null ? 0 : Math.max(0, Math.min(200, value));
  const tone = abilityRingTone(value);
  const attrClass =
    value == null ? "attr-tone-neutral" : `attr-tone-${attributeTone("Ability", value / 10)}`;
  return (
    <span className="squad-ability-cell">
      <span
        className={`fit-score-ring fit-score-${tone}`}
        style={{ "--fit-score": `${safeValue * 1.8}deg` } as React.CSSProperties}
      >
        <strong className={attrClass}>{value ?? "—"}</strong>
      </span>
      <small>{label}</small>
    </span>
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
        <strong>{player.positions.join(" / ") || "—"}</strong>
        <small>{footLine(player)}</small>
      </span>
      <AbilityRing value={player.currentAbility} label="Ability" />
      <AbilityRing value={player.potentialAbility} label="Potential" />
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
