"use client";

import { useMemo } from "react";
import { ArrowRight } from "lucide-react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import { formatHasScore, hasBand, liveHasBreakdown, squadHasRankings, type HasTone } from "@/domain/has-score";
import { LiveDataState } from "@/components/live-data-state";
import { PlayerFace } from "@/components/player-face";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

function HasBreakdownTooltip({ player }: { player: LivePlayer }) {
  const rows = liveHasBreakdown(player);
  return (
    <div className="dash-has-tooltip-grid" aria-label="HAS inputs">
      {rows.map((row) => (
        <span key={row.abbr} className={`dash-has-tooltip-cell tone-${row.tone}`} title={row.label}>
          <small>{row.abbr}</small>
          <strong>{row.value}</strong>
        </span>
      ))}
    </div>
  );
}

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
              <small>{player.positions?.slice(0, 2).join(" / ") || "—"}</small>
            </span>
            <span className={`dash-has-score tone-${tone}`}>{formatHasScore(score)}</span>
          </button>
        }
      />
      <TooltipContent side="bottom" align="start" className="dash-has-tooltip">
        <HasBreakdownTooltip player={player} />
      </TooltipContent>
    </Tooltip>
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
