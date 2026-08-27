"use client";

import { useMemo } from "react";
import { ArrowRight } from "lucide-react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import {
  formatDelta,
  rankSquadMovers,
  type SquadMoverChange,
} from "@/domain/attribute-history";
import { formatPlayerPositions } from "@/domain/live-data";
import { formatHasScore, hasBand, squadHasRankings, type HasTone } from "@/domain/has-score";
import { attributeDeltaTone } from "@/domain/attribute-tone";
import { rankSquadProspects, type SquadProspect } from "@/domain/squad-prospects";
import { LiveDataState } from "@/components/live-data-state";
import { HasBreakdownGridFromPlayer } from "@/components/has-breakdown-grid";
import { PlayerFace } from "@/components/player-face";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

function HasCard({
  player,
  score,
  tone,
  onOpen,
}: {
  player: LivePlayer;
  score: number;
  tone: HasTone;
  onOpen: (id: string) => void;
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <button type="button" className="dash-has-card" onClick={() => onOpen(player.id)}>
            <PlayerFace playerId={player.id} name={player.name} size="sm" />
            <span className="dash-has-card-copy">
              <strong>{player.name}</strong>
              <small>{formatPlayerPositions(player)}</small>
            </span>
            <span className={`dash-has-score tone-${tone}`}>{formatHasScore(score)}</span>
          </button>
        }
      />
      <TooltipContent side="bottom" align="start" className="dash-has-tooltip">
        <HasBreakdownGridFromPlayer player={player} />
      </TooltipContent>
    </Tooltip>
  );
}

function MoverChangeChips({ changes }: { changes: SquadMoverChange[] }) {
  const shown = changes.slice(0, 4);
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

function MoverCard({
  player,
  changes,
  onOpen,
}: {
  player: LivePlayer;
  changes: SquadMoverChange[];
  onOpen: (id: string) => void;
}) {
  return (
    <button type="button" className="dash-has-card dash-mover-card" onClick={() => onOpen(player.id)}>
      <PlayerFace playerId={player.id} name={player.name} size="sm" />
      <span className="dash-has-card-copy">
        <strong>{player.name}</strong>
        <small>{formatPlayerPositions(player)}</small>
      </span>
      <MoverChangeChips changes={changes} />
    </button>
  );
}

function ProspectCard({
  row,
  onOpen,
}: {
  row: SquadProspect;
  onOpen: (id: string) => void;
}) {
  const { player, pa, professionalism, mentor, mentorPro, proGap } = row;
  return (
    <button
      type="button"
      className="dash-has-card dash-prospect-card"
      onClick={() => onOpen(player.id)}
    >
      <PlayerFace playerId={player.id} name={player.name} size="sm" />
      <span className="dash-has-card-copy">
        <strong>{player.name}</strong>
        <small>
          {player.age != null ? `Age ${player.age} · ` : ""}
          PA {Math.round(pa)}
        </small>
        <small className="dash-prospect-mentor">
          Pro {professionalism} → {mentor.name} (+{proGap}, {mentorPro})
        </small>
      </span>
    </button>
  );
}

export function DashboardScreen({
  snapshot,
  checking,
  onRefresh,
  onOpenPlayer,
  onOpenSquad,
}: {
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  onOpenPlayer: (playerId: string) => void;
  onOpenSquad: () => void;
}) {
  const squad = useMemo(
    () => snapshot.players.filter((player) => player.clubId === snapshot.managedClubId),
    [snapshot.managedClubId, snapshot.players],
  );
  const club = snapshot.clubs.find((item) => item.id === snapshot.managedClubId);
  const has = useMemo(() => squadHasRankings(squad), [squad]);
  const movers = useMemo(
    () => rankSquadMovers(squad),
    [squad, snapshot.status.lastSync, snapshot.status.lastSuccessfulRead],
  );
  const prospects = useMemo(() => rankSquadProspects(squad), [squad]);
  const ready =
    snapshot.status.state === "connected" && Boolean(snapshot.managedClubId) && squad.length > 0;

  return (
    <main className="screen">
      <div className="planner-heading">
        <div>
          <h1>Dashboard</h1>
          <p>
            {ready
              ? `${club?.name ?? "Squad"} · ${squad.length} players`
              : "Collective squad signals — load when FM26 has a save open"}
          </p>
        </div>
        <div className="heading-actions">
          <Button variant="outline" onClick={onOpenSquad} disabled={!ready}>
            Squad
            <ArrowRight data-icon="inline-end" />
          </Button>
        </div>
      </div>

      <section className="screen-panel dash-has-widget" aria-label="Movers since last change">
        <header className="screen-panel__head">
          <h2>Movers</h2>
        </header>
        <div className="screen-panel__body">
          {!ready ? (
            <LiveDataState
              snapshot={snapshot}
              title="Dashboard"
              checking={checking}
              onRefresh={onRefresh}
              compact
            />
          ) : movers.length ? (
            <div className="dash-has-list dash-movers-list">
              {movers.map(({ player, changes }) => (
                <MoverCard
                  key={player.id}
                  player={player}
                  changes={changes}
                  onOpen={onOpenPlayer}
                />
              ))}
            </div>
          ) : (
            <p className="evidence-caption">
              No attribute moves since the last recorded change-point. Load again after training or
              matches.
            </p>
          )}
        </div>
      </section>

      <section className="screen-panel dash-has-widget" aria-label="Prospects with Pro mentor room">
        <header className="screen-panel__head">
          <h2>Prospects</h2>
        </header>
        <div className="screen-panel__body">
          {!ready ? (
            <LiveDataState
              snapshot={snapshot}
              title="Dashboard"
              checking={checking}
              onRefresh={onRefresh}
              compact
            />
          ) : prospects.length ? (
            <div className="dash-has-list dash-movers-list">
              {prospects.map((row) => (
                <ProspectCard key={row.player.id} row={row} onOpen={onOpenPlayer} />
              ))}
            </div>
          ) : (
            <p className="evidence-caption">
              No young high-PA players with a clear Professionalism mentor on squad.
            </p>
          )}
        </div>
      </section>

      <section className="screen-panel dash-has-widget" aria-label="Personality overview">
        <header className="screen-panel__head">
          <h2>Hidden attribute score</h2>
        </header>

        <div className="screen-panel__body">
          {!ready ? (
            <LiveDataState
              snapshot={snapshot}
              title="Dashboard"
              checking={checking}
              onRefresh={onRefresh}
              compact
            />
          ) : has.ranked.length ? (
            <div className="dash-has-columns">
              <div>
                <h3>Top 10</h3>
                <div className="dash-has-list">
                  {has.top.map(({ player, score }) => (
                    <HasCard
                      key={player.id}
                      player={player}
                      score={score}
                      tone={hasBand(score)}
                      onOpen={onOpenPlayer}
                    />
                  ))}
                </div>
              </div>
              <div>
                <h3>Bottom 10</h3>
                <div className="dash-has-list">
                  {has.bottom.map(({ player, score }) => (
                    <HasCard
                      key={player.id}
                      player={player}
                      score={score}
                      tone={hasBand(score)}
                      onOpen={onOpenPlayer}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="evidence-caption">No readable personality pack on squad players yet.</p>
          )}

          {ready && has.ranked.length > 0 && has.ranked.length < squad.length ? (
            <p className="evidence-caption">
              HAS shown for {has.ranked.length} of {squad.length} — others missing personality data.
            </p>
          ) : null}
        </div>
      </section>
    </main>
  );
}
