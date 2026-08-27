"use client";

import { useMemo, type ReactNode } from "react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import type { AttributeTone } from "@/domain/attribute-tone";
import {
  mentoringHaSnapshot,
  mentoringPairDeltas,
  rankMentorCandidates,
  sortMenteeCandidates,
  squadMenteeCandidates,
  type MentorRank,
  type MentoringDeltaTone,
} from "@/domain/mentoring-match";
import { formatHasScore, hasBand, liveHasScore } from "@/domain/has-score";
import { isAtClubSquadPlayer } from "@/domain/live-data";
import { HasBreakdownGrid } from "@/components/has-breakdown-grid";
import { LiveDataState } from "@/components/live-data-state";
import { PlayerFace } from "@/components/player-face";

function deltaLabel(delta: number) {
  if (delta === 0) return "0";
  return delta > 0 ? `+${delta}` : String(delta);
}

function deltaCellTone(tone: MentoringDeltaTone): AttributeTone {
  if (tone === "gain") return "high";
  if (tone === "cost") return "low";
  return "mid";
}

function MentoringDeltaGrid({
  subject,
  player,
  side,
}: {
  subject: LivePlayer;
  player: LivePlayer;
  side: "mentor" | "mentee";
}) {
  const rows = useMemo(
    () =>
      mentoringPairDeltas(subject, player, side).map((row) => ({
        abbr: row.abbr,
        label: row.key,
        value: deltaLabel(row.delta),
        tone: deltaCellTone(row.tone),
      })),
    [subject, player, side],
  );

  return <HasBreakdownGrid className="mentoring-player-card-grid" rows={rows} />;
}

function MentoringPlayerCard({
  subject,
  player,
  side,
  tier,
  onOpen,
}: {
  subject: LivePlayer;
  player: LivePlayer;
  side: "mentor" | "mentee";
  tier?: MentorRank["tier"];
  onOpen: (id: string) => void;
}) {
  const has = liveHasScore(player);
  const tone = has == null ? "mid" : hasBand(has);

  return (
    <button
      type="button"
      className="mentoring-player-card"
      data-tier={tier}
      onClick={() => onOpen(player.id)}
    >
      <span className="mentoring-player-card-top">
        <PlayerFace playerId={player.id} name={player.name} size="sm" />
        <strong className="mentoring-player-name">{player.name}</strong>
        <span className={`dash-has-score tone-${tone}`}>{formatHasScore(has)}</span>
      </span>
      <MentoringDeltaGrid subject={subject} player={player} side={side} />
    </button>
  );
}

function MentoringColumn({
  side,
  count,
  children,
}: {
  side: "mentor" | "mentee";
  count: number;
  children: ReactNode;
}) {
  return (
    <section className="mentoring-column" data-side={side}>
      <header className="mentoring-column-head">
        <h3>{side === "mentor" ? "Mentors" : "Mentees"}</h3>
        <span className="mentoring-count">{count}</span>
      </header>
      <div className="mentoring-player-list">{children}</div>
    </section>
  );
}

export function MentoringPanel({
  player,
  snapshot,
  checking,
  onRefresh,
  onOpenPlayer,
}: {
  player: LivePlayer;
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  onOpenPlayer: (id: string) => void;
}) {
  const atClub = isAtClubSquadPlayer(player, snapshot.managedClubId);
  const squad = useMemo(
    () =>
      snapshot.players.filter((row) => isAtClubSquadPlayer(row, snapshot.managedClubId)),
    [snapshot.managedClubId, snapshot.players],
  );
  const hasThresholds = Object.keys(mentoringHaSnapshot(player)).length > 0;

  const mentors = useMemo(() => rankMentorCandidates(player, squad), [player, squad]);
  const mentees = useMemo(
    () => sortMenteeCandidates(squadMenteeCandidates(player, squad), liveHasScore),
    [player, squad],
  );

  const ready =
    snapshot.status.state === "connected" && Boolean(snapshot.managedClubId) && squad.length > 0;

  if (!ready) {
    return (
      <section className="dossier-panel tab-evidence-panel mentoring-panel">
        <LiveDataState
          snapshot={snapshot}
          title="Mentoring"
          checking={checking}
          onRefresh={onRefresh}
          compact
        />
      </section>
    );
  }

  if (!atClub || !hasThresholds) {
    return <section className="dossier-panel tab-evidence-panel mentoring-panel mentoring-panel-empty" />;
  }

  return (
    <section className="dossier-panel tab-evidence-panel mentoring-panel">
      <div className="mentoring-columns">
        <MentoringColumn side="mentor" count={mentors.length}>
          {mentors.length ? (
            mentors.map(({ player: candidate, tier }) => (
              <MentoringPlayerCard
                key={candidate.id}
                subject={player}
                player={candidate}
                side="mentor"
                tier={tier}
                onOpen={onOpenPlayer}
              />
            ))
          ) : (
            <div className="mentoring-empty" aria-hidden />
          )}
        </MentoringColumn>
        <MentoringColumn side="mentee" count={mentees.length}>
          {mentees.length ? (
            mentees.map((candidate) => (
              <MentoringPlayerCard
                key={candidate.id}
                subject={player}
                player={candidate}
                side="mentee"
                onOpen={onOpenPlayer}
              />
            ))
          ) : (
            <div className="mentoring-empty" aria-hidden />
          )}
        </MentoringColumn>
      </div>
    </section>
  );
}
