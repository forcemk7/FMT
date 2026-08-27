"use client";

import type { ReactNode } from "react";
import { useMemo } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { rankSquadMovers } from "@/domain/attribute-history";
import {
  DASH_PEEK_SIZE,
  dashViewBlurb,
  dashViewTitle,
  type DashViewId,
} from "@/domain/dashboard-views";
import { squadHasRankings } from "@/domain/has-score";
import { rankSquadProspects } from "@/domain/squad-prospects";
import {
  DashHasRow,
  DashMoverRow,
  DashProspectRow,
} from "@/components/dashboard-widgets";
import { LiveDataState } from "@/components/live-data-state";
import { Button } from "@/components/ui/button";
import { isAtClubSquadPlayer } from "@/domain/live-data";

function WidgetShell({
  title,
  viewId,
  onOpenView,
  children,
  empty,
}: {
  title: string;
  viewId: DashViewId;
  onOpenView: (id: DashViewId) => void;
  children?: ReactNode;
  empty?: string | null;
}) {
  return (
    <section className="screen-panel dash-widget" aria-label={title}>
      <header className="dash-widget__head">
        <button type="button" className="dash-widget__title" onClick={() => onOpenView(viewId)}>
          <span className="dash-widget__label">{title}</span>
          <ArrowRight aria-hidden className="dash-widget__chevron" size={16} strokeWidth={2.25} />
        </button>
      </header>
      <div className="screen-panel__body dash-widget__body">
        {children}
        {empty ? <p className="evidence-caption">{empty}</p> : null}
      </div>
    </section>
  );
}

export function DashboardScreen({
  snapshot,
  checking,
  onRefresh,
  onOpenPlayer,
  onOpenView,
}: {
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  onOpenPlayer: (playerId: string) => void;
  onOpenView: (view: DashViewId) => void;
}) {
  const squad = useMemo(
    () =>
      snapshot.players.filter((player) =>
        isAtClubSquadPlayer(player, snapshot.managedClubId),
      ),
    [snapshot.managedClubId, snapshot.players],
  );
  const club = snapshot.clubs.find((item) => item.id === snapshot.managedClubId);
  const has = useMemo(() => squadHasRankings(squad, DASH_PEEK_SIZE), [squad]);
  const movers = useMemo(
    () => rankSquadMovers(squad, undefined, DASH_PEEK_SIZE),
    [squad, snapshot.status.lastSync, snapshot.status.lastSuccessfulRead],
  );
  const prospects = useMemo(() => rankSquadProspects(squad, DASH_PEEK_SIZE), [squad]);
  const ready =
    snapshot.status.state === "connected" && Boolean(snapshot.managedClubId) && squad.length > 0;

  return (
    <main className="screen dash-screen">
      <div className="planner-heading">
        <div>
          <h1>Dashboard</h1>
          <p>
            {ready
              ? `${club?.name ?? "Squad"} · filtered peeks — open a widget for the full view`
              : "Collective squad signals — load when FM26 has a save open"}
          </p>
        </div>
      </div>

      {!ready ? (
        <LiveDataState
          snapshot={snapshot}
          title="Dashboard"
          checking={checking}
          onRefresh={onRefresh}
        />
      ) : (
        <div className="dash-widget-grid">
          <WidgetShell
            title="Movers"
            viewId="Movers"
            onOpenView={onOpenView}
            empty={
              movers.length
                ? null
                : "No moves since last change-point. Load after training or matches."
            }
          >
            {movers.length ? (
              <div className="dash-peek-list">
                {movers.map(({ player, changes }) => (
                  <DashMoverRow
                    key={player.id}
                    player={player}
                    changes={changes}
                    onOpen={onOpenPlayer}
                    compact
                  />
                ))}
              </div>
            ) : null}
          </WidgetShell>

          <WidgetShell
            title="Prospects"
            viewId="Prospects"
            onOpenView={onOpenView}
            empty={
              prospects.length
                ? null
                : "No young high-PA players with a clear Pro mentor on squad."
            }
          >
            {prospects.length ? (
              <div className="dash-peek-list">
                {prospects.map((row) => (
                  <DashProspectRow key={row.player.id} row={row} onOpen={onOpenPlayer} compact />
                ))}
              </div>
            ) : null}
          </WidgetShell>

          <WidgetShell
            title="HAS Top"
            viewId="HAS Top"
            onOpenView={onOpenView}
            empty={has.top.length ? null : "No readable personality pack on squad players yet."}
          >
            {has.top.length ? (
              <div className="dash-peek-list">
                {has.top.map(({ player, score }) => (
                  <DashHasRow
                    key={player.id}
                    player={player}
                    score={score}
                    onOpen={onOpenPlayer}
                    compact
                  />
                ))}
              </div>
            ) : null}
          </WidgetShell>

          <WidgetShell
            title="HAS Bottom"
            viewId="HAS Bottom"
            onOpenView={onOpenView}
            empty={has.bottom.length ? null : "No readable personality pack on squad players yet."}
          >
            {has.bottom.length ? (
              <div className="dash-peek-list">
                {has.bottom.map(({ player, score }) => (
                  <DashHasRow
                    key={player.id}
                    player={player}
                    score={score}
                    onOpen={onOpenPlayer}
                    compact
                  />
                ))}
              </div>
            ) : null}
          </WidgetShell>
        </div>
      )}
    </main>
  );
}

export function DashboardViewScreen({
  view,
  snapshot,
  checking,
  onRefresh,
  onOpenPlayer,
  onBack,
}: {
  view: DashViewId;
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  onOpenPlayer: (playerId: string) => void;
  onBack: () => void;
}) {
  const squad = useMemo(
    () =>
      snapshot.players.filter((player) =>
        isAtClubSquadPlayer(player, snapshot.managedClubId),
      ),
    [snapshot.managedClubId, snapshot.players],
  );
  const ready =
    snapshot.status.state === "connected" && Boolean(snapshot.managedClubId) && squad.length > 0;

  const movers = useMemo(
    () => rankSquadMovers(squad, undefined, 64),
    [squad, snapshot.status.lastSync, snapshot.status.lastSuccessfulRead],
  );
  const prospects = useMemo(() => rankSquadProspects(squad, 64), [squad]);
  const has = useMemo(() => squadHasRankings(squad, Math.max(squad.length, 1)), [squad]);

  let body: ReactNode = null;
  if (!ready) {
    body = (
      <LiveDataState
        snapshot={snapshot}
        title={dashViewTitle(view)}
        checking={checking}
        onRefresh={onRefresh}
      />
    );
  } else if (view === "Movers") {
    body = movers.length ? (
      <div className="dash-has-list dash-view-list">
        {movers.map(({ player, changes }) => (
          <DashMoverRow key={player.id} player={player} changes={changes} onOpen={onOpenPlayer} />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">No attribute moves since the last recorded change-point.</p>
    );
  } else if (view === "Prospects") {
    body = prospects.length ? (
      <div className="dash-has-list dash-view-list">
        {prospects.map((row) => (
          <DashProspectRow key={row.player.id} row={row} onOpen={onOpenPlayer} />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">
        No young high-PA players with a clear Professionalism mentor on squad.
      </p>
    );
  } else if (view === "HAS Top") {
    body = has.top.length ? (
      <div className="dash-has-list dash-view-list">
        {has.top.map(({ player, score }) => (
          <DashHasRow key={player.id} player={player} score={score} onOpen={onOpenPlayer} />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">No readable personality pack on squad players yet.</p>
    );
  } else {
    body = has.bottom.length ? (
      <div className="dash-has-list dash-view-list">
        {has.bottom.map(({ player, score }) => (
          <DashHasRow key={player.id} player={player} score={score} onOpen={onOpenPlayer} />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">No readable personality pack on squad players yet.</p>
    );
  }

  return (
    <main className="screen dash-view-screen">
      <header className="planner-heading dash-view-heading">
        <div className="dash-view-heading-row">
          <Button variant="ghost" size="icon" onClick={onBack} aria-label="Back to Dashboard">
            <ArrowLeft />
          </Button>
          <div>
            <h1>{dashViewTitle(view)}</h1>
            <p>{dashViewBlurb(view)}</p>
          </div>
        </div>
      </header>
      <section className="screen-panel">
        <div className="screen-panel__body">{body}</div>
      </section>
    </main>
  );
}
