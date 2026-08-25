"use client";

import { useMemo } from "react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import {
  fieldDeltas,
  formatDelta,
  getPlayerAttrHistory,
} from "@/domain/attribute-history";
import { LiveDataState } from "@/components/live-data-state";
import { PlayerFace } from "@/components/player-face";

function ability(value: number | null | undefined) {
  return typeof value === "number" ? String(value) : "—";
}

function SquadGlanceRow({
  player,
  onOpen,
}: {
  player: LivePlayer;
  onOpen: (id: string) => void;
}) {
  const points = getPlayerAttrHistory(player.id);
  const ca = fieldDeltas(points, "CA");
  const det = fieldDeltas(points, "Determination");
  const pro = fieldDeltas(points, "Professionalism");

  return (
    <button type="button" className="dash-player-row" onClick={() => onOpen(player.id)}>
      <PlayerFace playerId={player.id} name={player.name} size="sm" />
      <span className="dash-player-id">
        <strong>{player.name}</strong>
        <small>
          {player.positions?.slice(0, 2).join(" / ") || "—"} · {player.age ?? "—"}y
        </small>
      </span>
      <span>
        <small>CA</small>
        <strong>
          {ability(player.currentAbility)}
          {ca.recent != null ? <em> {formatDelta(ca.recent)}</em> : null}
        </strong>
      </span>
      <span>
        <small>PA</small>
        <strong>{ability(player.potentialAbility)}</strong>
      </span>
      <span>
        <small>DET</small>
        <strong>
          {ability(player.attributes?.Determination)}
          {det.recent != null ? <em> {formatDelta(det.recent)}</em> : null}
        </strong>
      </span>
      <span>
        <small>PRO</small>
        <strong>
          {ability(player.personalityAttributes?.Professionalism)}
          {pro.recent != null ? <em> {formatDelta(pro.recent)}</em> : null}
        </strong>
      </span>
    </button>
  );
}

/** Loop B — collective squad/profile glance; drills into player desk. */
export function DashboardScreen({
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
  const club = snapshot.clubs.find((item) => item.id === snapshot.managedClubId);

  const movers = useMemo(() => {
    return squad
      .map((player) => {
        const ca = fieldDeltas(getPlayerAttrHistory(player.id), "CA");
        return { player, move: ca.recent ?? 0, abs: Math.abs(ca.recent ?? 0) };
      })
      .filter((row) => row.abs > 0)
      .sort((a, b) => b.abs - a.abs)
      .slice(0, 5);
  }, [squad]);

  if (snapshot.status.state !== "connected" || !snapshot.managedClubId || squad.length === 0) {
    return (
      <main className="screen">
        <LiveDataState snapshot={snapshot} title="Dashboard" checking={checking} onRefresh={onRefresh} />
      </main>
    );
  }

  return (
    <main className="screen dashboard-squad-screen">
      <header className="dash-intro">
        <div>
          <p className="section-kicker">Loop B · squad at a glance</p>
          <h1>{club?.name ?? "Squad"}</h1>
          <p>
            Same live players as Squad — rolled up for CA/PA and recent history moves. Open a
            row for the full desk.
          </p>
        </div>
        <div className="dash-stat">
          <small>Players</small>
          <strong>{squad.length}</strong>
        </div>
      </header>

      {movers.length > 0 ? (
        <section className="dash-movers" aria-label="Recent CA movers">
          <h2>Recent CA movers</h2>
          <ul>
            {movers.map(({ player, move }) => (
              <li key={player.id}>
                <button type="button" onClick={() => onOpenPlayer(player.id)}>
                  <strong>{player.name}</strong>
                  <span>{formatDelta(move)} CA</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className="evidence-caption">
          No CA change-points yet. Reload after in-game development days to feed history.
        </p>
      )}

      <section className="dash-squad-table" aria-label="Squad glance">
        <header>
          <span>Player</span>
          <span />
          <span>CA</span>
          <span>PA</span>
          <span>DET</span>
          <span>PRO</span>
        </header>
        {squad.map((player) => (
          <SquadGlanceRow key={player.id} player={player} onOpen={onOpenPlayer} />
        ))}
      </section>
    </main>
  );
}
