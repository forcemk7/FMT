"use client";

import type { ReactNode } from "react";
import { useMemo } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { rankSquadMovers } from "@/domain/attribute-history";
import {
  DASH_PEEK_SIZE,
  dashViewBlurb,
  dashViewProfileTab,
  dashViewTitle,
  type DashViewId,
} from "@/domain/dashboard-views";
import { squadHasRankings } from "@/domain/has-score";
import { rankBestPlayers, rankBestTalent } from "@/domain/squad-ability-rank";
import {
  DashAbilityRow,
  DashHasRow,
  DashMatchExperienceRow,
  DashMoverRow,
} from "@/components/dashboard-widgets";
import { LiveDataState } from "@/components/live-data-state";
import { Button } from "@/components/ui/button";
import { isAtClubEmployee } from "@/domain/live-data";
import { rankMatchExperienceOpportunities } from "@/domain/match-experience-opportunities";
import type { PlayerProfileTab } from "@/components/player-profile-screen";

type OpenPlayer = (playerId: string, options?: { tab?: PlayerProfileTab }) => void;

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
  onOpenPlayer: OpenPlayer;
  onOpenView: (view: DashViewId) => void;
}) {
  const squad = useMemo(
    () =>
      snapshot.players.filter((player) =>
        isAtClubEmployee(player, snapshot.managedClubId),
      ),
    [snapshot.managedClubId, snapshot.players],
  );
  const has = useMemo(() => squadHasRankings(squad, DASH_PEEK_SIZE), [squad]);
  const movers = useMemo(
    () => rankSquadMovers(squad, undefined, DASH_PEEK_SIZE),
    [squad, snapshot.status.lastSync, snapshot.status.lastSuccessfulRead],
  );
  const bestPlayers = useMemo(
    () => rankBestPlayers(snapshot.players, snapshot.managedClubId, DASH_PEEK_SIZE),
    [snapshot.managedClubId, snapshot.players],
  );
  const bestTalent = useMemo(
    () => rankBestTalent(snapshot.players, snapshot.managedClubId, DASH_PEEK_SIZE),
    [snapshot.managedClubId, snapshot.players],
  );
  const matchExperience = useMemo(
    () => rankMatchExperienceOpportunities(snapshot, DASH_PEEK_SIZE),
    [snapshot],
  );
  const ready =
    snapshot.status.state === "connected" &&
    Boolean(snapshot.managedClubId) &&
    (squad.length > 0 || bestPlayers.length > 0 || bestTalent.length > 0);

  const openFromView = (viewId: DashViewId) => (playerId: string) =>
    onOpenPlayer(playerId, { tab: dashViewProfileTab(viewId) });

  return (
    <main className={`screen dash-screen${ready ? " is-dash-compact" : ""}`}>
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
            title={dashViewTitle("Movers")}
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
                    onOpen={openFromView("Movers")}
                    compact
                  />
                ))}
              </div>
            ) : null}
          </WidgetShell>

          <WidgetShell
            title={dashViewTitle("Best players")}
            viewId="Best players"
            onOpenView={onOpenView}
            empty={bestPlayers.length ? null : "No readable CA on owned club players yet."}
          >
            {bestPlayers.length ? (
              <div className="dash-peek-list">
                {bestPlayers.map((row) => (
                  <DashAbilityRow
                    key={row.player.id}
                    row={row}
                    mode="players"
                    onOpen={openFromView("Best players")}
                    compact
                    clubTeams={snapshot.clubTeams}
                    clubs={snapshot.clubs}
                  />
                ))}
              </div>
            ) : null}
          </WidgetShell>

          <WidgetShell
            title={dashViewTitle("Best talent")}
            viewId="Best talent"
            onOpenView={onOpenView}
            empty={
              bestTalent.length
                ? null
                : "No owned players age 20 or under with readable PA yet."
            }
          >
            {bestTalent.length ? (
              <div className="dash-peek-list">
                {bestTalent.map((row) => (
                  <DashAbilityRow
                    key={row.player.id}
                    row={row}
                    mode="talent"
                    onOpen={openFromView("Best talent")}
                    compact
                    clubTeams={snapshot.clubTeams}
                    clubs={snapshot.clubs}
                  />
                ))}
              </div>
            ) : null}
          </WidgetShell>

          <WidgetShell
            title={dashViewTitle("Match experience")}
            viewId="Match experience"
            onOpenView={onOpenView}
            empty={
              matchExperience.length
                ? null
                : "No Under N / Reserves players who would be #1–2 on a First Team."
            }
          >
            {matchExperience.length ? (
              <div className="dash-peek-list">
                {matchExperience.map((row) => (
                  <DashMatchExperienceRow
                    key={row.player.id}
                    row={row}
                    onOpen={openFromView("Match experience")}
                    compact
                  />
                ))}
              </div>
            ) : null}
          </WidgetShell>

          <WidgetShell
            title={dashViewTitle("HAS Top")}
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
                    onOpen={openFromView("HAS Top")}
                    compact
                    highlight="top"
                  />
                ))}
              </div>
            ) : null}
          </WidgetShell>

          <WidgetShell
            title={dashViewTitle("HAS Bottom")}
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
                    onOpen={openFromView("HAS Bottom")}
                    compact
                    highlight="bottom"
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
  onOpenPlayer: OpenPlayer;
  onBack: () => void;
}) {
  const squad = useMemo(
    () =>
      snapshot.players.filter((player) =>
        isAtClubEmployee(player, snapshot.managedClubId),
      ),
    [snapshot.managedClubId, snapshot.players],
  );
  const bestPlayers = useMemo(
    () => rankBestPlayers(snapshot.players, snapshot.managedClubId, 64),
    [snapshot.managedClubId, snapshot.players],
  );
  const bestTalent = useMemo(
    () => rankBestTalent(snapshot.players, snapshot.managedClubId, 64),
    [snapshot.managedClubId, snapshot.players],
  );
  const ready =
    snapshot.status.state === "connected" &&
    Boolean(snapshot.managedClubId) &&
    (squad.length > 0 || bestPlayers.length > 0 || bestTalent.length > 0);

  const movers = useMemo(
    () => rankSquadMovers(squad, undefined, 64),
    [squad, snapshot.status.lastSync, snapshot.status.lastSuccessfulRead],
  );
  const matchExperience = useMemo(
    () => rankMatchExperienceOpportunities(snapshot, 64),
    [snapshot],
  );
  const has = useMemo(() => squadHasRankings(squad, Math.max(squad.length, 1)), [squad]);
  const openPlayer = (playerId: string) =>
    onOpenPlayer(playerId, { tab: dashViewProfileTab(view) });

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
          <DashMoverRow key={player.id} player={player} changes={changes} onOpen={openPlayer} />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">No attribute moves since the last recorded change-point.</p>
    );
  } else if (view === "Best players") {
    body = bestPlayers.length ? (
      <div className="dash-has-list dash-view-list">
        {bestPlayers.map((row) => (
          <DashAbilityRow
            key={row.player.id}
            row={row}
            mode="players"
            onOpen={openPlayer}
            clubTeams={snapshot.clubTeams}
            clubs={snapshot.clubs}
          />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">No readable CA on owned club players yet.</p>
    );
  } else if (view === "Best talent") {
    body = bestTalent.length ? (
      <div className="dash-has-list dash-view-list">
        {bestTalent.map((row) => (
          <DashAbilityRow
            key={row.player.id}
            row={row}
            mode="talent"
            onOpen={openPlayer}
            clubTeams={snapshot.clubTeams}
            clubs={snapshot.clubs}
          />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">No owned players age 20 or under with readable PA yet.</p>
    );
  } else if (view === "Match experience") {
    body = matchExperience.length ? (
      <div className="dash-has-list dash-view-list">
        {matchExperience.map((row) => (
          <DashMatchExperienceRow key={row.player.id} row={row} onOpen={openPlayer} />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">
        No Under N / Reserves players who would be #1 or #2 same-pos on a First Team.
      </p>
    );
  } else if (view === "HAS Top") {
    body = has.top.length ? (
      <div className="dash-has-list dash-view-list">
        {has.top.map(({ player, score }) => (
          <DashHasRow
            key={player.id}
            player={player}
            score={score}
            onOpen={openPlayer}
            highlight="top"
          />
        ))}
      </div>
    ) : (
      <p className="evidence-caption">No readable personality pack on squad players yet.</p>
    );
  } else {
    body = has.bottom.length ? (
      <div className="dash-has-list dash-view-list">
        {has.bottom.map(({ player, score }) => (
          <DashHasRow
            key={player.id}
            player={player}
            score={score}
            onOpen={openPlayer}
            highlight="bottom"
          />
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
          <Button variant="ghost" size="icon" onClick={onBack} aria-label="Back">
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
