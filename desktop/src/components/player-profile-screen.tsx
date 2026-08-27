"use client";

import type { CSSProperties } from "react";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  GitCompareArrows,
  MapPinned,
  ShieldAlert,
  Star,
  UserRound,
} from "lucide-react";
import type { LiveFootballSnapshot, LivePlayer } from "@/domain/adapters";
import { SET_PIECE_ATTRIBUTES } from "@/domain/attribute-desk";
import { abilityToneFromScore, attributeTone } from "@/domain/attribute-tone";
import { formatHasScore, hasBand, liveHasScore } from "@/domain/has-score";
import { formatPlayerPositions } from "@/domain/live-data";
import { livePersonalityLabels } from "@/domain/personality-labels";
import { AttributeDesk } from "@/components/attribute-desk";
import { AttributeHistoryPanel } from "@/components/attribute-history-panel";
import { MentoringPanel } from "@/components/mentoring-panel";
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

function metricLabel(value: string) {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\bXg\b/i, "xG")
    .replace(/\bXa\b/i, "xA")
    .replace(/^./, (letter) => letter.toUpperCase());
}

function metricValue(label: string, value: unknown) {
  if (typeof value !== "number") return "Unknown";
  return value.toFixed(label.toLowerCase().includes("per 90") ? 2 : 0);
}

function PlayerPolygram({ player }: { player: LivePlayer }) {
  const axes = [
    ["Technique", ["Technique", "First Touch", "Dribbling"]],
    ["Creation", ["Passing", "Vision", "Flair"]],
    ["Defending", ["Marking", "Tackling", "Positioning"]],
    ["Movement", ["Acceleration", "Pace", "Agility"]],
    ["Physical", ["Strength", "Stamina", "Jumping Reach"]],
    ["Set pieces", SET_PIECE_ATTRIBUTES],
  ] as const;
  const centre = 110;
  const radius = 76;
  const points = axes.map(([, names], index) => {
    const values = names.flatMap((name) => typeof player.attributes?.[name] === "number" ? [player.attributes[name] as number] : []);
    const value = values.length ? values.reduce((sum, item) => sum + item, 0) / values.length : 0;
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / axes.length;
    const distance = radius * (value / 20);
    return `${centre + Math.cos(angle) * distance},${centre + Math.sin(angle) * distance}`;
  }).join(" ");
  return (
    <section className="dossier-panel polygram-panel">
      <header><BarChart3 /><h2>Ability polygram</h2></header>
      <svg viewBox="0 0 220 220" role="img" aria-label="Visible attribute polygram">
        {[.25, .5, .75, 1].map((scale) => <polygon key={scale} points={axes.map((_, index) => { const angle = -Math.PI / 2 + (index * Math.PI * 2) / axes.length; return `${centre + Math.cos(angle) * radius * scale},${centre + Math.sin(angle) * radius * scale}`; }).join(" ")} className="polygram-grid" />)}
        {axes.map(([label], index) => { const angle = -Math.PI / 2 + (index * Math.PI * 2) / axes.length; const x = centre + Math.cos(angle) * 98; const y = centre + Math.sin(angle) * 98; return <text key={label} x={x} y={y} textAnchor="middle">{label}</text>; })}
        <polygon points={points} className="polygram-shape" />
      </svg>
      <p>Built only from visible attributes; missing axes remain at zero.</p>
    </section>
  );
}

function RoleFitCards({ player, limit = 6 }: { player: LivePlayer; limit?: number }) {
  const roles = player.playableRoles?.slice(0, limit) ?? [];
  if (!roles.length) {
    return <p className="role-fit-empty">No playable FM26 role score has been validated from the current mapped attributes.</p>;
  }
  return (
    <div className="role-fit-cards">
      {roles.map((role) => (
        <article key={role.roleKey} style={{ "--role-score": `${role.score}%` } as CSSProperties}>
          <span><strong>{role.shortRole}</strong><small>{role.score}</small></span>
          <div>
            <b>{role.role}</b>
            <small>{role.positions.join(" / ")} · position {role.positionFit}% · attributes {role.attributeFit ?? "—"}%</small>
          </div>
        </article>
      ))}
    </div>
  );
}

const PROFILE_TABS = [
  "attributes",
  "mentoring",
  "development",
  "overview",
  "tactical",
  "performance",
  "career",
] as const;

function profileTabLabel(value: (typeof PROFILE_TABS)[number]) {
  if (value === "tactical") return "Tactical fit";
  if (value === "development") return "Development";
  if (value === "mentoring") return "Mentoring";
  return value[0]!.toUpperCase() + value.slice(1);
}

export function PlayerProfileScreen({
  player,
  snapshot,
  favorite,
  checking,
  onRefresh,
  onToggleFavorite,
  onBack,
  onOpenClub,
  onOpenPlayer,
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
        <Button variant="outline" onClick={onBack}><ArrowLeft data-icon="inline-start" />Back</Button>
        <section className="favorites-empty"><h1>Player unavailable</h1><p>This player is not present in the latest live or indexed FM26 data.</p></section>
      </main>
    );
  }

  const parentClub = player.clubId ? snapshot.clubs.find((item) => item.id === player.clubId) : null;
  const parentClubName = parentClub?.name ?? player.clubName;
  const loanedOut = player.loanedOut === true;
  const loanClubName = player.loanClubName?.trim() || null;
  const loanClubId = player.loanClubId?.trim() || null;
  const primaryClubId = loanedOut && loanClubId ? loanClubId : player.clubId;
  const primaryClubName = loanedOut && loanClubName
    ? loanClubName
    : parentClubName;
  const club = primaryClubId
    ? snapshot.clubs.find((item) => item.id === primaryClubId) ?? parentClub
    : parentClub;
  const clubName = primaryClubName ?? club?.name;
  const clubSub =
    loanedOut && loanClubName
      ? `Parent: ${parentClubName ?? "—"}`
      : null;
  const mappedAttributeCount = Object.values(player.attributes ?? {}).filter((value) => typeof value === "number").length;
  const knownEvidence = player.scoutConfidence ?? Math.min(100, Math.round((mappedAttributeCount / 47) * 100));
  const unknownEvidence = 100 - knownEvidence;

  const ageLabel = player.age != null ? `${player.age} years old` : "—";
  const dobLabel = player.dateOfBirth?.trim() || null;
  const position = formatPlayerPositions(player);
  const height = formatHeight(player.heightCm ?? null);
  const leftFoot = player.leftFoot != null ? String(player.leftFoot) : "—";
  const rightFoot = player.rightFoot != null ? String(player.rightFoot) : "—";
  const ca = abilityLabel(player.currentAbility);
  const pa = abilityLabel(player.potentialAbility);
  const hasScore = liveHasScore(player);
  const hasLabel = formatHasScore(hasScore);
  const hasTone = hasScore == null ? "attr-tone-mid" : `attr-tone-${hasBand(hasScore)}`;
  const inferredLabels = livePersonalityLabels(player);
  const personalityLabel = formatGeneralText(player.personality ?? inferredLabels?.personality ?? null);
  const mediaLabel = formatGeneralText(player.mediaHandling ?? inferredLabels?.mediaHandling ?? null);
  const nationLabel = player.nationality?.trim() || "—";

  return (
    <main className="player-dossier">
      <header className="dossier-header">
        <div className="dossier-heading">
          <Button variant="ghost" size="icon" aria-label="Back to squad" onClick={onBack}><ArrowLeft /></Button>
          <PlayerFace playerId={player.id} name={player.name} size="lg" />
          <div>
            <h1>{player.name}</h1>
          </div>
        </div>
        <div className="dossier-actions">
          <Button variant="outline" className={favorite ? "shortlist-active" : ""} onClick={onToggleFavorite}><Star data-icon="inline-start" fill={favorite ? "currentColor" : "none"} />{favorite ? "Saved" : "Save"}</Button>
        </div>
      </header>

      <section className="player-facts" aria-label="Key info">
        <div className="player-facts-row">
          <span className="player-nation-fact">
            <b>Nationality</b>
            <span className="player-fact-identity">
              {player.nationalityId ? (
                <NationFlag nationId={player.nationalityId} name={player.nationality ?? "Nation"} size="md" />
              ) : (
                <span className="nation-flag nation-flag-md nation-flag-empty" aria-hidden="true" />
              )}
              <strong title={nationLabel === "—" ? undefined : nationLabel}>{nationLabel}</strong>
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
            <span className="player-fact-identity">
              {club ? (
                <ClubLogo clubId={club.id} name={club.name} size="md" />
              ) : (
                <span className="club-logo club-logo-md club-logo-empty" aria-hidden="true" />
              )}
              <span className="player-fact-value">
                <strong title={clubName ?? undefined}>{clubName ?? "—"}</strong>
                {clubSub ? <small className="player-fact-sub">{clubSub}</small> : null}
              </span>
            </span>
          </button>
          <span>
            <b>Position</b>
            <span className="player-fact-value">
              <strong title={position === "—" ? undefined : position}>{position}</strong>
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

        <TabsContent value="overview">
          <div className="dossier-layout">
            <div className="dossier-main-column">
              <section className="dossier-panel scout-summary-panel">
                <header><UserRound /><h2>Scout summary</h2></header>
                <p>
                  FMT identifies <strong>{player.name}</strong> ({player.nationality ?? "nationality unknown"}, age {player.age ?? "unknown"}) at {clubName ?? "an unmapped club"}.
                </p>
                <div className="summary-columns">
                  <div><h3><CheckCircle2 />Strengths</h3><span>{player.strengths.length ? player.strengths.join(" · ") : "No visible evidence"}</span></div>
                  <div><h3><AlertCircle />Weaknesses</h3><span>{player.weaknesses.length ? player.weaknesses.join(" · ") : "No visible evidence"}</span></div>
                  <div><h3><ClipboardList />Recommended next action</h3><span>{snapshot.tactic ? "Review live formation-specific fit." : "Keep scouting while the live tactic layout is validated."}</span></div>
                </div>
              </section>

              <section className="dossier-panel role-fit-panel">
                <header><MapPinned /><h2>{snapshot.tactic ? "Role & tactical fit" : "Role evidence"}</h2></header>
                <div className="role-fit-layout">
                  <div className="role-fit-metrics">
                    <span><small>Best role</small><strong>{player.bestRole ?? "Unknown"}</strong></span>
                    <span><small>{snapshot.tactic ? "Tactical fit" : "Role evidence"}</small><strong>{player.roleFit == null ? "Unknown" : `${player.roleFit}%`}</strong></span>
                    <span><small>Knowledge</small><strong>{player.scoutConfidence == null ? "Unknown" : `${player.scoutConfidence}%`}</strong></span>
                  </div>
                  <div className="mini-role-map">
                    <span className="mini-box left" /><span className="mini-box right" /><span className="mini-half" /><span className="mini-centre" />
                    <i>Role map unavailable</i>
                  </div>
                  <div className="fit-legend">
                    <span><i data-tone="strong" />Strong fit</span>
                    <span><i data-tone="good" />Good fit</span>
                    <span><i data-tone="suitable" />Suitable</span>
                    <span><i data-tone="low" />Low fit</span>
                  </div>
                </div>
                <RoleFitCards player={player} limit={5} />
              </section>

              <section className="dossier-panel attribute-evidence-panel">
                <header><BarChart3 /><h2>Attribute evidence</h2><span>Visible + hidden when mapped</span></header>
                <AttributeDesk player={player} />
              </section>
            </div>

            <aside className="dossier-side-column">
              <PlayerPolygram player={player} />
              <section className="dossier-panel knowledge-panel">
                <header><CircleHelp /><h2>Knowledge profile</h2></header>
                <div className="knowledge-overview">
                  <span className="knowledge-donut" style={{ "--known": `${knownEvidence}%` } as CSSProperties} />
                  <div>
                    <span><i data-tone="known" />Known mapped evidence <strong>{knownEvidence}%</strong></span>
                    <span><i data-tone="estimated" />Estimated <strong>0%</strong></span>
                    <span><i data-tone="unknown" />Unknown <strong>{unknownEvidence}%</strong></span>
                  </div>
                </div>
                <dl>
                  <div><dt>Last scouted</dt><dd>{player.lastScoutedDate ?? "Unknown"}</dd></div>
                  <div><dt>Observations</dt><dd>Unknown</dd></div>
                  <div><dt>Report reliability</dt><dd>{player.reportReliability ?? "Unknown"}</dd></div>
                </dl>
              </section>

              <section className="dossier-panel compact-dossier-panel">
                <header><ShieldAlert /><h2>Risk profile</h2></header>
                {["Adaptation", "Wage", "Tactical mismatch", "Injury history", "Registration"].map((risk) => (
                  <button key={risk}><span><i />{risk}</span><strong>Unknown</strong><ChevronRight /></button>
                ))}
              </section>

              <section className="dossier-panel career-panel">
                <header><BarChart3 /><h2>Career & form</h2></header>
                <div className="form-bars">{Array.from({ length: 10 }, (_, index) => <i key={index} />)}</div>
                <span><small>Current form</small><strong>{player.averageRating?.toFixed(2) ?? "Unknown"}</strong></span>
                <div className="career-stats">
                  <span><small>Minutes</small><strong>{player.minutesPlayed ?? "Unknown"}</strong></span>
                  <span><small>Goals</small><strong>{player.goals ?? "Unknown"}</strong></span>
                  <span><small>Assists</small><strong>{player.assists ?? "Unknown"}</strong></span>
                </div>
                <p>From visible data only</p>
              </section>

              <section className="dossier-panel decision-panel">
                <header><ClipboardList /><h2>Decision history</h2></header>
                <div><span>No scouting decisions recorded</span></div>
              </section>
            </aside>
          </div>
        </TabsContent>

        <TabsContent value="tactical">
          <section className="dossier-panel tab-evidence-panel">
            <header><MapPinned /><h2>In possession / out of possession evidence</h2></header>
            <div className="role-phase-grid">
              <article><small>Best mapped FM26 role</small><strong>{player.bestRole ?? "Role unknown"}</strong><p>{player.roleFit == null ? "Not enough mapped evidence." : `${player.roleFit}/100 from position familiarity and mapped attributes.`}</p></article>
              <article><small>In possession</small><strong>{player.inPossessionFit == null ? "Unknown" : `${player.inPossessionFit}/100`}</strong><p>Mapped from the local FM Dossier role-phase index when available.</p></article>
              <article><small>Out of possession</small><strong>{player.outOfPossessionFit == null ? "Unknown" : `${player.outOfPossessionFit}/100`}</strong><p>Mapped separately from the out-of-possession role-phase index when available.</p></article>
              <article><small>Combined recommendation</small><strong>{player.recommendation?.minimum == null ? "Not enough evidence" : player.recommendation.minimum === player.recommendation.maximum ? player.recommendation.minimum : `${player.recommendation.minimum}–${player.recommendation.maximum}`}</strong><p>{(player.recommendation?.completeness ?? 0) >= 95 ? "Exact score from complete visible evidence." : "Partial observations produce an interval, never a false exact score."}</p></article>
            </div>
            <RoleFitCards player={player} />
          </section>
        </TabsContent>
        <TabsContent value="attributes">
          <section className="dossier-panel tab-evidence-panel attribute-desk-panel">
            <AttributeDesk
              player={player}
              deltaMode="recent"
              historySyncKey={snapshot.status.lastSync}
            />
          </section>
        </TabsContent>
        <TabsContent value="mentoring">
          <MentoringPanel
            key={player.id}
            player={player}
            snapshot={snapshot}
            checking={checking}
            onRefresh={onRefresh}
            onOpenPlayer={onOpenPlayer}
          />
        </TabsContent>
        <TabsContent value="development">
          <AttributeHistoryPanel
            key={player.id}
            player={player}
            historySyncKey={snapshot.status.lastSync}
          />
        </TabsContent>
        <TabsContent value="performance">
          <section className="dossier-panel tab-evidence-panel">
            <header><BarChart3 /><h2>Performance and per 90</h2></header>
            <div className="performance-grid">
              {Object.entries({ "Average rating": player.averageRating, Minutes: player.minutesPlayed, Goals: player.goals, Assists: player.assists, ...player.per90 }).map(([label, value]) => (
                <article key={label}><small>{metricLabel(label)}</small><strong>{metricValue(metricLabel(label), value)}</strong></article>
              ))}
            </div>
            <p className="evidence-caption">Only competition and per-90 values read from club-visible FM26 structures appear here.</p>
          </section>
        </TabsContent>
        <TabsContent value="career">
          <section className="dossier-panel tab-evidence-panel">
            <header><BarChart3 /><h2>Career history</h2><span>Mapped totals</span></header>
            <div className="performance-grid">
              {Object.entries(player.careerTotals ?? {}).map(([label, value]) => (
                <article key={label}><small>{metricLabel(label)}</small><strong>{metricValue(metricLabel(label), value)}</strong></article>
              ))}
              <article><small>Signed</small><strong>{player.signDate ?? "Unknown"}</strong></article>
              <article><small>Contract start</small><strong>{player.contractStartDate ?? "Unknown"}</strong></article>
              <article><small>Remaining</small><strong>{player.contractRemaining ?? "Unknown"}</strong></article>
            </div>
            <p className="evidence-caption">Season-by-season timeline is shown only when that structure is mapped; these totals come from the local FM26 save index.</p>
          </section>
        </TabsContent>
      </Tabs>
    </main>
  );
}
