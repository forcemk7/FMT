"use client";

import { useMemo, useState } from "react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import {
  buildMatchExperienceCards,
  matchExperiencePosition,
} from "@/domain/match-experience";
import { PlayerFace } from "@/components/player-face";

function abilityLabel(value: number | null): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "—";
}

export function MatchExperiencePanel({
  player,
  snapshot,
  onOpenPlayer,
}: {
  player: LivePlayer;
  snapshot: LiveFootballSnapshot;
  onOpenPlayer: (playerId: string) => void;
}) {
  const primaries = player.positions ?? [];
  const defaultPosition = matchExperiencePosition(player);
  const [position, setPosition] = useState(defaultPosition);

  const activePosition =
    position && primaries.some((code) => code === position)
      ? position
      : defaultPosition;

  const managedClubName =
    snapshot.clubs.find((club) => club.id === snapshot.managedClubId)?.name ??
    null;

  const cards = useMemo(
    () =>
      buildMatchExperienceCards(
        player,
        snapshot.players,
        snapshot.clubTeams ?? [],
        managedClubName,
        activePosition,
      ),
    [player, snapshot.players, snapshot.clubTeams, managedClubName, activePosition],
  );

  if (!activePosition) {
    return (
      <section className="dossier-panel tab-evidence-panel match-experience-panel">
        <header>
          <h2>Match experience</h2>
        </header>
        <p className="match-experience-empty">
          No primary position on this player — cannot rank against club teams.
        </p>
      </section>
    );
  }

  if (!(snapshot.clubTeams ?? []).length) {
    return (
      <section className="dossier-panel tab-evidence-panel match-experience-panel">
        <header>
          <h2>Match experience</h2>
          <span>{activePosition}</span>
        </header>
        <p className="match-experience-empty">No club teams loaded in this snapshot.</p>
      </section>
    );
  }

  return (
    <section className="match-experience-panel" aria-label="Match experience">
      {primaries.length > 1 ? (
        <div className="match-experience-positions" role="group" aria-label="Position">
          {primaries.map((code) => (
            <button
              key={code}
              type="button"
              className={
                code === activePosition
                  ? "match-experience-pos match-experience-pos-active"
                  : "match-experience-pos"
              }
              onClick={() => setPosition(code)}
            >
              {code}
            </button>
          ))}
        </div>
      ) : (
        <p className="match-experience-position-label">Position {activePosition}</p>
      )}

      <div className="match-experience-cards">
        {cards.map((card) => (
          <article key={card.teamUid} className="match-experience-card">
            <header>
              <h3>{card.teamLabel}</h3>
              <span>
                {card.focusRank != null
                  ? `${card.focusRank} / ${card.rows.length} · ${card.position}`
                  : card.position}
              </span>
            </header>
            {card.rows.length === 0 ? (
              <p className="match-experience-empty">No {card.position} on this roster.</p>
            ) : (
              <ol className="match-experience-list">
                {card.rows.map((row) => {
                  const openOther = !row.isFocus;
                  const className = [
                    "match-experience-row",
                    row.isFocus ? "match-experience-row-focus" : "",
                    !row.isOnRoster && row.isFocus
                      ? "match-experience-row-projected"
                      : "",
                  ]
                    .filter(Boolean)
                    .join(" ");
                  const body = (
                    <>
                      <span className="match-experience-rank">{row.rank}</span>
                      <PlayerFace
                        playerId={row.playerId}
                        name={row.name}
                        size="sm"
                      />
                      <span className="match-experience-name">
                        <strong>{row.name}</strong>
                        {row.isFocus && !row.isOnRoster ? (
                          <small>projected</small>
                        ) : null}
                        {row.isFocus && row.isOnRoster ? (
                          <small>current</small>
                        ) : null}
                      </span>
                      <span className="match-experience-ca">
                        {abilityLabel(row.currentAbility)}
                      </span>
                    </>
                  );
                  return (
                    <li key={`${card.teamUid}-${row.playerId}`} className={className}>
                      {openOther ? (
                        <button
                          type="button"
                          className="match-experience-row-btn"
                          onClick={() => onOpenPlayer(row.playerId)}
                        >
                          {body}
                        </button>
                      ) : (
                        <div className="match-experience-row-btn">{body}</div>
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
