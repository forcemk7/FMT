"use client";

import { useMemo, useState } from "react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import {
  buildMatchExperienceCards,
  MATCH_EXPERIENCE_PAGE_SIZE,
  matchExperiencePosition,
  matchExperiencePositionOptions,
  type MatchExperienceCard,
  type MatchExperienceRow,
} from "@/domain/match-experience";
import { PlayerFace } from "@/components/player-face";

function abilityLabel(value: number | null): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "—";
}

function MatchExperienceRowView({
  row,
  onOpenPlayer,
}: {
  row: MatchExperienceRow | null;
  onOpenPlayer: (playerId: string) => void;
}) {
  if (!row) {
    return (
      <li className="match-experience-row match-experience-row-pad" aria-hidden="true">
        <div className="match-experience-row-btn" />
      </li>
    );
  }

  const openOther = !row.isFocus;
  const className = [
    "match-experience-row",
    row.isFocus ? "match-experience-row-focus" : "",
    !row.isOnRoster && row.isFocus ? "match-experience-row-projected" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const body = (
    <>
      <span className="match-experience-rank">{row.rank}</span>
      <PlayerFace playerId={row.playerId} name={row.name} size="sm" />
      <span className="match-experience-name">
        <strong>{row.name}</strong>
        {row.isFocus && !row.isOnRoster ? <small>projected</small> : null}
        {row.isFocus && row.isOnRoster ? <small>current</small> : null}
      </span>
      <span className="match-experience-ca">{abilityLabel(row.currentAbility)}</span>
    </>
  );

  return (
    <li className={className}>
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
}

function MatchExperienceCardView({
  card,
  positionOptions,
  onPositionChange,
  onOpenPlayer,
}: {
  card: MatchExperienceCard;
  positionOptions: string[];
  onPositionChange: (teamUid: string, position: string) => void;
  onOpenPlayer: (playerId: string) => void;
}) {
  const rankLabel =
    card.focusRank != null ? `${card.focusRank}/${card.totalRows}` : "—";

  const slots: Array<MatchExperienceRow | null> = [...card.rows];
  while (slots.length < MATCH_EXPERIENCE_PAGE_SIZE) slots.push(null);

  const selectValue = positionOptions.includes(card.position)
    ? card.position
    : (positionOptions[0] ?? card.position);

  return (
    <article className="match-experience-card">
      <header className="match-experience-card-header">
        <div className="match-experience-card-title">
          <h3 title={card.teamLabel}>{card.teamLabel}</h3>
          <span className="match-experience-card-meta">
            <span>{card.position}</span>
            <span aria-hidden="true">·</span>
            <span>{rankLabel}</span>
          </span>
        </div>
        {positionOptions.length > 0 ? (
          <label className="match-experience-pos-select">
            <span className="sr-only">Position for {card.teamLabel}</span>
            <select
              value={selectValue}
              onChange={(event) => onPositionChange(card.teamUid, event.target.value)}
            >
              {positionOptions.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </header>
      <ol
        className="match-experience-list"
        style={{ ["--match-exp-rows" as string]: MATCH_EXPERIENCE_PAGE_SIZE }}
      >
        {slots.map((row, index) => (
          <MatchExperienceRowView
            key={row ? `${card.teamUid}-${row.playerId}` : `${card.teamUid}-pad-${index}`}
            row={row}
            onOpenPlayer={onOpenPlayer}
          />
        ))}
      </ol>
    </article>
  );
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
  const positionOptions = matchExperiencePositionOptions(player);
  const defaultPosition = matchExperiencePosition(player) ?? positionOptions[0] ?? null;
  const [positionByTeam, setPositionByTeam] = useState<Record<string, string>>({});

  const managedClubName =
    snapshot.clubs.find((club) => club.id === snapshot.managedClubId)?.name ?? null;

  const cards = useMemo(
    () =>
      buildMatchExperienceCards(
        player,
        snapshot.players,
        snapshot.clubTeams ?? [],
        managedClubName,
        positionByTeam,
        defaultPosition,
      ),
    [
      player,
      snapshot.players,
      snapshot.clubTeams,
      managedClubName,
      positionByTeam,
      defaultPosition,
    ],
  );

  const onPositionChange = (teamUid: string, position: string) => {
    setPositionByTeam((prev) => ({ ...prev, [teamUid]: position }));
  };

  if (!defaultPosition) {
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
        </header>
        <p className="match-experience-empty">No club teams loaded in this snapshot.</p>
      </section>
    );
  }

  if (!cards.length) {
    return (
      <section className="match-experience-panel" aria-label="Match experience">
        <p className="match-experience-empty">
          No loaded club teams with resolved players.
        </p>
      </section>
    );
  }

  return (
    <section className="match-experience-panel" aria-label="Match experience">
      <div className="match-experience-cards">
        {cards.map((card) => (
          <MatchExperienceCardView
            key={card.teamUid}
            card={card}
            positionOptions={positionOptions}
            onPositionChange={onPositionChange}
            onOpenPlayer={onOpenPlayer}
          />
        ))}
      </div>
    </section>
  );
}
