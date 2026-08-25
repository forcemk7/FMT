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
import { attributeTone } from "@/domain/attribute-tone";
import { AttributeHistoryPanel } from "@/components/attribute-history-panel";
import { Button } from "@/components/ui/button";
import { ConfidenceRing } from "@/components/confidence-ring";
import { PlayerFace } from "@/components/player-face";
import { ClubLogo } from "@/components/club-logo";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const technicalAttributes = ["Crossing", "Dribbling", "Finishing", "First Touch", "Heading", "Long Shots", "Marking", "Passing", "Tackling", "Technique"];
const mentalAttributes = ["Aggression", "Anticipation", "Bravery", "Composure", "Concentration", "Decisions", "Determination", "Flair", "Leadership", "Off the Ball", "Positioning", "Teamwork", "Vision", "Work Rate"];
const physicalAttributes = ["Acceleration", "Agility", "Balance", "Jumping Reach", "Natural Fitness", "Pace", "Stamina", "Strength"];
const setPieceAttributes = ["Corners", "Free Kick Taking", "Penalty Taking", "Long Throws"];
const goalkeepingAttributes = ["Aerial Reach", "Command of Area", "Communication", "Eccentricity", "Handling", "Kicking", "One on Ones", "Punching", "Reflexes", "Rushing Out", "Throwing"];
const hiddenAttributes = ["Consistency", "Dirtiness", "Important Matches", "Injury Proneness", "Versatility"];
const personalityAttributes = ["Adaptability", "Ambition", "Loyalty", "Pressure", "Professionalism", "Sportsmanship", "Temperament", "Controversy"];

function evidenceValue(map: Record<string, number | null> | undefined, attribute: string) {
  const value = map?.[attribute];
  return typeof value === "number" ? String(value) : "—";
}

function abilityLabel(value: number | null | undefined) {
  return typeof value === "number" ? String(value) : "—";
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

function AttributeGroup({
  title,
  names,
  values,
}: {
  title: string;
  names: string[];
  values: Record<string, number | null> | undefined;
}) {
  return (
    <section className="attribute-column">
      <h3>{title}</h3>
      {names.map((name) => {
        const raw = values?.[name];
        const tone = typeof raw === "number" ? attributeTone(name, raw) : "neutral";
        return (
          <span key={name}>
            <small>{name}</small>
            <strong className={`attr-tone attr-tone-${tone}`}>{evidenceValue(values, name)}</strong>
          </span>
        );
      })}
    </section>
  );
}

function PlayerPolygram({ player }: { player: LivePlayer }) {
  const axes = [
    ["Technique", ["Technique", "First Touch", "Dribbling"]],
    ["Creation", ["Passing", "Vision", "Flair"]],
    ["Defending", ["Marking", "Tackling", "Positioning"]],
    ["Movement", ["Acceleration", "Pace", "Agility"]],
    ["Physical", ["Strength", "Stamina", "Jumping Reach"]],
    ["Set pieces", setPieceAttributes],
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
  onToggleFavorite: () => void;
  onBack: () => void;
  onOpenClub?: (clubId: string) => void;
}) {
  if (!player) {
    return (
      <main className="screen">
        <Button variant="outline" onClick={onBack}><ArrowLeft data-icon="inline-start" />Back</Button>
        <section className="favorites-empty"><h1>Player unavailable</h1><p>This player is not present in the latest live or indexed FM26 data.</p></section>
      </main>
    );
  }

  const club = player.clubId ? snapshot.clubs.find((item) => item.id === player.clubId) : null;
  const clubName = club?.name ?? player.clubName;
  const mappedAttributeCount = Object.values(player.attributes ?? {}).filter((value) => typeof value === "number").length;
  const knownEvidence = player.scoutConfidence ?? Math.min(100, Math.round((mappedAttributeCount / 47) * 100));
  const unknownEvidence = 100 - knownEvidence;

  return (
    <main className="player-dossier">
      <header className="dossier-header">
        <div className="dossier-heading">
          <Button variant="ghost" size="icon" aria-label="Back to squad" onClick={onBack}><ArrowLeft /></Button>
          <PlayerFace playerId={player.id} name={player.name} size="lg" />
          <div><h1>{player.name}</h1><p>{clubName ?? "Club unknown"} · CA {abilityLabel(player.currentAbility)} · PA {abilityLabel(player.potentialAbility)}</p></div>
        </div>
        <div className="dossier-actions">
          <Button variant="outline" className={favorite ? "shortlist-active" : ""} onClick={onToggleFavorite}><Star data-icon="inline-start" fill={favorite ? "currentColor" : "none"} />{favorite ? "Saved" : "Save"}</Button>
        </div>
      </header>

      <section className="player-facts">
        <span><b>Nationality</b><strong>{player.nationality ?? "Unknown"}</strong></span>
        <button className="player-club-fact" disabled={!club} onClick={() => club && onOpenClub?.(club.id)}>{club ? <ClubLogo clubId={club.id} name={club.name} size="sm" /> : null}<span><b>Club</b><strong>{clubName ?? "Unknown"}</strong></span></button>
        <span><b>Age / DOB</b><strong>{player.age ?? "Unknown"}{player.dateOfBirth ? ` · ${player.dateOfBirth}` : ""}</strong></span>
        <span><b>Position</b><strong>{player.positions.join(" / ") || "Unknown"}</strong></span>
        <span><b>Preferred foot</b><strong>{player.preferredFoot ?? "Unknown"}</strong></span>
        <span><b>CA</b><strong>{abilityLabel(player.currentAbility)}</strong></span>
        <span><b>PA</b><strong>{abilityLabel(player.potentialAbility)}</strong></span>
        <span><b>Value</b><strong>{player.value ?? "Unknown"}</strong></span>
        <span><b>Wage</b><strong>{player.wage ?? "Unknown"}</strong></span>
        <span><b>Contract</b><strong>{player.contractStatus ?? "Unknown"}</strong></span>
        <span className="fact-confidence"><b>Knowledge</b>{player.scoutConfidence == null ? <strong>Unknown</strong> : <ConfidenceRing value={player.scoutConfidence} size="sm" />}</span>
      </section>

      <Tabs defaultValue="attributes" className="dossier-tabs">
        <TabsList variant="line">
          {["attributes", "overview", "tactical", "performance", "career"].map((value) => (
            <TabsTrigger key={value} value={value}>
              {value === "tactical" ? "Tactical fit" : value === "attributes" ? "Attributes & history" : value[0].toUpperCase() + value.slice(1)}
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
                <div className="ability-strip">
                  <span><small>Current ability</small><strong>{abilityLabel(player.currentAbility)}</strong></span>
                  <span><small>Potential ability</small><strong>{abilityLabel(player.potentialAbility)}</strong></span>
                </div>
                <div className="attribute-grid attribute-grid-five">
                  <AttributeGroup title="Technical" names={technicalAttributes} values={player.attributes} />
                  <AttributeGroup title="Mental" names={mentalAttributes} values={player.attributes} />
                  <AttributeGroup title="Physical" names={physicalAttributes} values={player.attributes} />
                  <AttributeGroup title="Set pieces" names={setPieceAttributes} values={player.attributes} />
                  <AttributeGroup title="Goalkeeping" names={goalkeepingAttributes} values={player.attributes} />
                </div>
                <div className="attribute-grid attribute-grid-two">
                  <AttributeGroup title="Hidden" names={hiddenAttributes} values={player.hiddenAttributes} />
                  <AttributeGroup title="Personality" names={personalityAttributes} values={player.personalityAttributes} />
                </div>
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
          <section className="dossier-panel tab-evidence-panel">
            <header><BarChart3 /><h2>Attribute desk</h2><span>{mappedAttributeCount} visible · CA/PA/HA when mapped</span></header>
            <div className="ability-strip">
              <span><small>Current ability</small><strong>{abilityLabel(player.currentAbility)}</strong></span>
              <span><small>Potential ability</small><strong>{abilityLabel(player.potentialAbility)}</strong></span>
            </div>
            <div className="attribute-grid attribute-grid-five">
              <AttributeGroup title="Technical" names={technicalAttributes} values={player.attributes} />
              <AttributeGroup title="Mental" names={mentalAttributes} values={player.attributes} />
              <AttributeGroup title="Physical" names={physicalAttributes} values={player.attributes} />
              <AttributeGroup title="Set pieces" names={setPieceAttributes} values={player.attributes} />
              <AttributeGroup title="Goalkeeping" names={goalkeepingAttributes} values={player.attributes} />
            </div>
            <div className="attribute-grid attribute-grid-two">
              <AttributeGroup title="Hidden" names={hiddenAttributes} values={player.hiddenAttributes} />
              <AttributeGroup title="Personality" names={personalityAttributes} values={player.personalityAttributes} />
            </div>
            <p className="evidence-caption">CA, PA, hidden, and personality show only when the live map returns in-range values; otherwise —.</p>
          </section>
          <AttributeHistoryPanel key={player.id} playerId={player.id} />
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
