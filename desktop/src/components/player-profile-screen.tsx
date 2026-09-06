"use client";

import { ArrowLeft, Star } from "lucide-react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import { abilityToneFromScore, attributeTone } from "@/domain/attribute-tone";
import { formatHasScore, hasBand, liveHasScore } from "@/domain/has-score";
import { playerPositionParts, playerTeamDisplayName } from "@/domain/live-data";
import { livePersonalityLabels } from "@/domain/personality-labels";
import { AttributeDesk } from "@/components/attribute-desk";
import { AttributeHistoryPanel } from "@/components/attribute-history-panel";
import { Button } from "@/components/ui/button";
import { PlayerFace } from "@/components/player-face";
import { ClubLogo } from "@/components/club-logo";
import { NationFlag } from "@/components/nation-flag";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function abilityLabel(value: number | null | undefined) {
  return typeof value === "number" ? String(value) : "—";
}

/** CA/PA are 1–200; tone uses the same 1–20 bands as attributes (value / 10). */
function abilityToneClass(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "attr-tone-mid";
  return `attr-tone-${abilityToneFromScore(value)}`;
}

function footToneClass(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "attr-tone-mid";
  return `attr-tone-${attributeTone("Left Foot", value)}`;
}

function formatHeight(heightCm: number | null | undefined) {
  if (typeof heightCm !== "number" || !Number.isFinite(heightCm)) return "—";
  return `${(heightCm / 100).toFixed(2)} m`;
}

function formatGeneralText(value: string | null | undefined) {
  if (!value?.trim()) return "—";
  const trimmed = value.trim();
  if (trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed) as unknown;
      if (Array.isArray(parsed)) {
        const parts = parsed.map((item) => String(item ?? "").trim()).filter(Boolean);
        return parts.length ? parts.join(", ") : "—";
      }
    } catch {
      /* show raw */
    }
  }
  return trimmed;
}

const PROFILE_TABS = ["attributes", "development"] as const;

function profileTabLabel(value: (typeof PROFILE_TABS)[number]) {
  if (value === "development") return "Development";
  return "Attributes";
}

export function PlayerProfileScreen({
  player,
  snapshot,
  favorite,
  onToggleFavorite,
  onBack,
  onOpenClub,
}: {
  player: LivePlayer | null;
  snapshot: LiveFootballSnapshot;
  favorite: boolean;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  onToggleFavorite: () => void;
  onBack: () => void;
  onOpenClub?: (clubId: string) => void;
  onOpenPlayer: (playerId: string) => void;
}) {
  if (!player) {
    return (
      <main className="screen">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft data-icon="inline-start" />
          Back
        </Button>
        <section className="favorites-empty">
          <h1>Player unavailable</h1>
          <p>This player is not present in the latest live or indexed FM26 data.</p>
        </section>
      </main>
    );
  }

  const parentClub = player.clubId ? snapshot.clubs.find((item) => item.id === player.clubId) : null;
  const parentClubName = parentClub?.name ?? player.clubName;
  const loanedOut = player.loanedOut === true;
  const loanClubName = player.loanClubName?.trim() || null;
  const loanClubId = player.loanClubId?.trim() || null;
  const activeClubId = loanedOut && loanClubId ? loanClubId : player.clubId ?? null;
  const teamDisplayName = playerTeamDisplayName(
    player,
    snapshot.clubTeams ?? [],
    snapshot.clubs,
  );
  const activeClubName =
    loanedOut && loanClubName
      ? loanClubName
      : teamDisplayName ?? parentClubName ?? null;
  const club = activeClubId
    ? snapshot.clubs.find((item) => item.id === activeClubId) ?? null
    : null;
  const clubName = activeClubName ?? club?.name ?? null;
  const clubSub =
    loanedOut && loanClubName ? `Parent: ${parentClubName ?? "—"}` : null;

  const ageLabel = player.age != null ? `${player.age} years old` : "—";
  const dobLabel = player.dateOfBirth?.trim() || null;
  const { primary: positionPrimary, secondary: positionSecondary } =
    playerPositionParts(player);
  const height = formatHeight(player.heightCm ?? null);
  const leftFoot = player.leftFoot != null ? String(player.leftFoot) : "—";
  const rightFoot = player.rightFoot != null ? String(player.rightFoot) : "—";
  const ca = abilityLabel(player.currentAbility);
  const pa = abilityLabel(player.potentialAbility);
  const hasScore = liveHasScore(player);
  const hasLabel = formatHasScore(hasScore);
  const hasTone = hasScore == null ? "attr-tone-mid" : `attr-tone-${hasBand(hasScore)}`;
  const inferredLabels = livePersonalityLabels(player);
  const personalityLabel = formatGeneralText(
    player.personality ?? inferredLabels?.personality ?? null,
  );
  const mediaLabel = formatGeneralText(
    player.mediaHandling ?? inferredLabels?.mediaHandling ?? null,
  );
  const nationLabel = player.nationality?.trim() || "—";

  return (
    <main className="player-dossier">
      <header className="dossier-header">
        <div className="dossier-heading">
          <Button variant="ghost" size="icon" aria-label="Back to squad" onClick={onBack}>
            <ArrowLeft />
          </Button>
          <PlayerFace playerId={player.id} name={player.name} size="lg" />
          <div>
            <h1>{player.name}</h1>
          </div>
        </div>
        <div className="dossier-actions">
          <Button
            variant="outline"
            className={favorite ? "shortlist-active" : ""}
            onClick={onToggleFavorite}
          >
            <Star data-icon="inline-start" fill={favorite ? "currentColor" : "none"} />
            {favorite ? "Saved" : "Save"}
          </Button>
        </div>
      </header>

      <section className="player-facts" aria-label="Key info">
        <div className="player-facts-row">
          <span className="player-nation-fact">
            <b>Nationality</b>
            <span className="player-fact-value">
              <span className="player-fact-identity">
                {player.nationalityId ? (
                  <NationFlag
                    nationId={player.nationalityId}
                    name={player.nationality ?? "Nation"}
                  size="sm"
                />
              ) : (
                <span className="nation-flag nation-flag-sm nation-flag-empty" aria-hidden="true" />
              )}
                <strong title={nationLabel === "—" ? undefined : nationLabel}>{nationLabel}</strong>
              </span>
            </span>
          </span>
          <span className="player-age-fact">
            <b>Age</b>
            <span className="player-fact-value">
              <strong title={ageLabel === "—" ? undefined : ageLabel}>{ageLabel}</strong>
              {dobLabel ? <small className="player-fact-sub">{dobLabel}</small> : null}
            </span>
          </span>
          <span>
            <b>Height</b>
            <span className="player-fact-value">
              <strong title={height === "—" ? undefined : height}>{height}</strong>
            </span>
          </span>
          <span title={personalityLabel === "—" ? undefined : personalityLabel}>
            <b>Personality</b>
            <span className="player-fact-value">
              <strong>{personalityLabel}</strong>
            </span>
          </span>
          <span>
            <b>Ability</b>
            <span className="player-fact-value">
              <strong className={abilityToneClass(player.currentAbility)}>{ca}</strong>
            </span>
          </span>
          <span>
            <b>Left foot</b>
            <span className="player-fact-value">
              <strong className={footToneClass(player.leftFoot)}>{leftFoot}</strong>
            </span>
          </span>
        </div>
        <div className="player-facts-row">
          <button
            type="button"
            className="player-club-fact"
            disabled={!club}
            onClick={() => club && onOpenClub?.(club.id)}
          >
            <b>{loanedOut && loanClubName ? "Loan club" : "Club"}</b>
            <span className="player-fact-value">
              <span className="player-fact-identity">
                {activeClubId ? (
                  <ClubLogo
                    clubId={activeClubId}
                    name={clubName ?? club?.name ?? "Club"}
                    size="sm"
                  />
                ) : (
                  <span className="club-logo club-logo-sm club-logo-empty" aria-hidden="true" />
                )}
                <strong title={clubName ?? undefined}>{clubName ?? "—"}</strong>
              </span>
              {clubSub ? <small className="player-fact-sub">{clubSub}</small> : null}
            </span>
          </button>
          <span>
            <b>Position</b>
            <span className="player-fact-value">
              <strong title={positionPrimary === "—" ? undefined : positionPrimary}>
                {positionPrimary}
              </strong>
              {positionSecondary ? (
                <small className="player-fact-sub">({positionSecondary})</small>
              ) : null}
            </span>
          </span>
          <span>
            <b>HAS</b>
            <span className="player-fact-value">
              <strong className={hasTone}>{hasLabel}</strong>
            </span>
          </span>
          <span title={mediaLabel === "—" ? undefined : mediaLabel}>
            <b>Media Handling</b>
            <span className="player-fact-value">
              <strong>{mediaLabel}</strong>
            </span>
          </span>
          <span>
            <b>Potential</b>
            <span className="player-fact-value">
              <strong className={abilityToneClass(player.potentialAbility)}>{pa}</strong>
            </span>
          </span>
          <span>
            <b>Right foot</b>
            <span className="player-fact-value">
              <strong className={footToneClass(player.rightFoot)}>{rightFoot}</strong>
            </span>
          </span>
        </div>
      </section>

      <Tabs defaultValue="attributes" className="dossier-tabs">
        <TabsList variant="line">
          {PROFILE_TABS.map((value) => (
            <TabsTrigger key={value} value={value}>
              {profileTabLabel(value)}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="attributes">
          <section className="dossier-panel tab-evidence-panel attribute-desk-panel">
            <AttributeDesk
              player={player}
              deltaMode="recent"
              historySyncKey={snapshot.status.lastSync}
            />
          </section>
        </TabsContent>
        <TabsContent value="development">
          <AttributeHistoryPanel
            key={player.id}
            player={player}
            historySyncKey={snapshot.status.lastSync}
          />
        </TabsContent>
      </Tabs>
    </main>
  );
}
