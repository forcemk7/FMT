"use client";

import { useMemo, useState } from "react";
import type { LivePlayer } from "@/domain/adapters";
import {
  HIDDEN_ATTRIBUTES,
  PERSONALITY_ATTRIBUTES,
} from "@/domain/attribute-desk";
import {
  colorForSeries,
  factualHistorySummary,
  getPlayerAttrHistory,
} from "@/domain/attribute-history";
import { AttributeDesk } from "@/components/attribute-desk";

const PLOT_PRESETS: Record<string, string[]> = {
  Ability: ["CA", "PA"],
  Hidden: [...HIDDEN_ATTRIBUTES],
  Personality: [...PERSONALITY_ATTRIBUTES],
  Development: ["CA", "Determination", "Professionalism", "Consistency", "Natural Fitness"],
};

const MAX_PLOT_SERIES = 6;

function smoothLinePath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) return `M ${pts[0]!.x} ${pts[0]!.y}`;
  if (pts.length === 2) return `M ${pts[0]!.x} ${pts[0]!.y} L ${pts[1]!.x} ${pts[1]!.y}`;
  let d = `M ${pts[0]!.x} ${pts[0]!.y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i]!;
    const p1 = pts[i]!;
    const p2 = pts[i + 1]!;
    const p3 = pts[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x} ${c1y} ${c2x} ${c2y} ${p2.x} ${p2.y}`;
  }
  return d;
}

function shortFieldLabel(field: string): string {
  if (field === "CA") return "Ability";
  if (field === "PA") return "Potential";
  if (field === "Important Matches") return "Imp. Matches";
  if (field === "Injury Proneness") return "Injury Pron.";
  if (field === "Natural Fitness") return "Nat. Fitness";
  if (field === "Professionalism") return "Professionalism";
  return field;
}

export function AttributeHistoryPanel({
  player,
  historySyncKey = null,
}: {
  player: LivePlayer;
  historySyncKey?: string | null;
}) {
  const points = getPlayerAttrHistory(player.id);
  const summary = factualHistorySummary(points);
  const available = useMemo(() => {
    const keys = new Set<string>();
    for (const point of points) {
      for (const key of Object.keys(point.values)) keys.add(key);
    }
    return keys;
  }, [player.id, points.length, historySyncKey]);

  const [preset, setPreset] = useState<keyof typeof PLOT_PRESETS | "Custom">("Ability");
  const [selected, setSelected] = useState<string[]>(() =>
    PLOT_PRESETS.Ability.filter((field) => true),
  );

  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const applyPreset = (name: keyof typeof PLOT_PRESETS) => {
    setPreset(name);
    setSelected(PLOT_PRESETS[name]!.filter((field) => available.size === 0 || available.has(field) || field === "CA" || field === "PA"));
  };

  const toggleField = (field: string) => {
    setPreset("Custom");
    setSelected((current) => {
      if (current.includes(field)) return current.filter((item) => item !== field);
      if (current.length >= MAX_PLOT_SERIES) return [...current.slice(1), field];
      return [...current, field];
    });
  };

  const plotFields = selected.filter((field) => available.has(field) || points.some((p) => field in p.values));

  const chart = useMemo(() => {
    if (points.length === 0 || plotFields.length === 0) return null;
    const width = 720;
    const height = 132;
    const pad = { left: 34, right: 10, top: 10, bottom: 22 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;

    const seriesRanges = plotFields.map((field) => {
      let min = Infinity;
      let max = -Infinity;
      for (const point of points) {
        const value = point.values[field];
        if (typeof value !== "number") continue;
        min = Math.min(min, value);
        max = Math.max(max, value);
      }
      if (!Number.isFinite(min) || !Number.isFinite(max)) return null;
      if (min === max) {
        min -= 1;
        max += 1;
      }
      return { field, min, max };
    });

    const validRanges = seriesRanges.filter(
      (row): row is { field: string; min: number; max: number } => row != null,
    );
    if (!validRanges.length) return null;

    const abilityish = validRanges.some((row) => row.field === "CA" || row.field === "PA");
    const attrish = validRanges.some((row) => row.field !== "CA" && row.field !== "PA");
    const normalize = abilityish && attrish;

    const sharedMin = Math.min(...validRanges.map((row) => row.min));
    const sharedMax = Math.max(...validRanges.map((row) => row.max));

    const xAt = (index: number) =>
      pad.left + (points.length <= 1 ? innerW / 2 : (index / (points.length - 1)) * innerW);
    const yAtShared = (value: number) =>
      pad.top + ((sharedMax - value) / (sharedMax - sharedMin)) * innerH;
    const yAtNorm = (value: number, min: number, max: number) =>
      pad.top + ((max - value) / (max - min)) * innerH;

    const series = validRanges.map((row, index) => {
      const pts = points.flatMap((point, pointIndex) => {
        const value = point.values[row.field];
        if (typeof value !== "number") return [];
        const y = normalize ? yAtNorm(value, row.min, row.max) : yAtShared(value);
        return [{ x: xAt(pointIndex), y }];
      });
      return { field: row.field, color: colorForSeries(index), path: smoothLinePath(pts), pts };
    });

    const xLabels = points.map((point, index) => ({
      x: xAt(index),
      label: point.gameDate?.trim() || String(index + 1),
    }));

    return {
      width,
      height,
      pad,
      yMin: normalize ? 0 : sharedMin,
      yMax: normalize ? 1 : sharedMax,
      yLabelTop: normalize ? "↑" : String(Math.round(sharedMax)),
      yLabelBottom: normalize ? "↓" : String(Math.round(sharedMin)),
      normalize,
      series,
      xLabels,
    };
  }, [player.id, points, plotFields.join("\0")]);

  if (points.length === 0) {
    return (
      <section className="dossier-panel tab-evidence-panel development-desk-panel">
        <header>
          <h2>Development</h2>
          <span>No observations yet</span>
        </header>
        <p className="evidence-caption development-desk-empty">
          Each Load appends a point when this player’s tracked values change. Play in FM, reload here —
          the desk shows all-time Δ and the plot tracks any attribute you select.
        </p>
      </section>
    );
  }

  return (
    <section className="dossier-panel tab-evidence-panel development-desk-panel">
      <header>
        <h2>Development</h2>
        <span>All-time Δ · click rows to plot</span>
      </header>

      {summary ? <p className="attr-history-summary development-desk-summary">{summary}</p> : null}

      <div className="development-desk-body">
        <div className="development-desk-attrs">
          <AttributeDesk
            player={player}
            deltaMode="allTime"
            compact
            historySyncKey={historySyncKey}
            selectedFields={selectedSet}
            onToggleField={toggleField}
          />
        </div>

        <div className="development-desk-plot-block">
          <div className="attr-history-presets development-plot-presets" role="group" aria-label="Plot presets">
            {(Object.keys(PLOT_PRESETS) as Array<keyof typeof PLOT_PRESETS>).map((name) => (
              <button
                key={name}
                type="button"
                className={preset === name ? "is-on" : undefined}
                onClick={() => applyPreset(name)}
              >
                {name}
              </button>
            ))}
          </div>

          <div className="development-plot-legend" aria-label="Plotted fields">
            {plotFields.length ? (
              plotFields.map((field, index) => (
                <button
                  key={field}
                  type="button"
                  className="development-plot-legend-item"
                  onClick={() => toggleField(field)}
                  title="Remove from plot"
                >
                  <i style={{ background: colorForSeries(index) }} />
                  {shortFieldLabel(field)}
                </button>
              ))
            ) : (
              <span>Select desk rows or a preset to plot.</span>
            )}
          </div>

          <div className="development-desk-chart">
            {chart ? (
              <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Attribute development plot">
                <text x={6} y={chart.pad.top + 4} className="attr-history-axis">
                  {chart.yLabelTop}
                </text>
                <text x={6} y={chart.height - chart.pad.bottom} className="attr-history-axis">
                  {chart.yLabelBottom}
                </text>
                {chart.normalize ? (
                  <text x={chart.width - 8} y={12} textAnchor="end" className="attr-history-axis">
                    shapes (mixed scale)
                  </text>
                ) : null}
                {chart.series.map((series) => (
                  <g key={series.field}>
                    <path d={series.path} fill="none" stroke={series.color} strokeWidth={2} />
                    {series.pts.map((pt, index) => (
                      <circle key={`${series.field}-${index}`} cx={pt.x} cy={pt.y} r={2.5} fill={series.color} />
                    ))}
                  </g>
                ))}
                {chart.xLabels.map((item, index) => (
                  <text
                    key={`${item.label}-${index}`}
                    x={item.x}
                    y={chart.height - 4}
                    textAnchor="middle"
                    className="attr-history-axis"
                  >
                    {item.label.length > 12 ? item.label.slice(0, 10) + "…" : item.label}
                  </text>
                ))}
              </svg>
            ) : (
              <p className="evidence-caption">Need values in history for the selected fields.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
