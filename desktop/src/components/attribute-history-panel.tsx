"use client";

import { useMemo, useState, type MouseEvent } from "react";
import type { LivePlayer } from "@/domain/adapters";
import {
  colorForSeries,
  getPlayerAttrHistory,
  type AttrHistoryPoint,
} from "@/domain/attribute-history";
import { AttributeDesk } from "@/components/attribute-desk";

const DEFAULT_PLOT = ["CA", "PA"] as const;
const MAX_PLOT_SERIES = 6;
/** Fixed ability scale (CA/PA). */
const ABILITY_Y = { min: 1, max: 200 } as const;
/** Fixed attribute scale (1–20). */
const ATTR_Y = { min: 1, max: 20 } as const;

function linePath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) return `M ${pts[0]!.x} ${pts[0]!.y}`;
  return pts
    .map((pt, index) => `${index === 0 ? "M" : "L"} ${pt.x} ${pt.y}`)
    .join(" ");
}

function shortFieldLabel(field: string): string {
  if (field === "CA") return "Ability";
  if (field === "PA") return "Potential";
  return field;
}

function formatWallClockShort(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Observation";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function observationLabel(point: AttrHistoryPoint, index: number): string {
  const gameDate = point.gameDate?.trim();
  if (gameDate) return gameDate;
  if (point.at?.trim()) return formatWallClockShort(point.at);
  return `Observation ${index + 1}`;
}

function isAbilityField(field: string): boolean {
  return field === "CA" || field === "PA";
}

export function AttributeHistoryPanel({
  player,
  historySyncKey = null,
}: {
  player: LivePlayer;
  historySyncKey?: string | null;
}) {
  const points = getPlayerAttrHistory(player.id);
  const [selected, setSelected] = useState<string[]>(() => [...DEFAULT_PLOT]);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const toggleField = (field: string) => {
    setSelected((current) => {
      if (current.includes(field)) return current.filter((item) => item !== field);
      if (current.length >= MAX_PLOT_SERIES) return [...current.slice(1), field];
      return [...current, field];
    });
  };

  const plotFields = selected.filter((field) =>
    points.some((point) => typeof point.values[field] === "number"),
  );

  const chart = useMemo(() => {
    const width = 720;
    const height = 132;
    const pad = { left: 34, right: 10, top: 10, bottom: 22 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;

    const xAt = (index: number) => {
      if (points.length <= 1) return pad.left + innerW / 2;
      return pad.left + (index / (points.length - 1)) * innerW;
    };

    const abilityish = plotFields.some(isAbilityField);
    const attrish = plotFields.some((field) => !isAbilityField(field));
    const normalize = abilityish && attrish;

    const sharedScale = abilityish && !attrish ? ABILITY_Y : ATTR_Y;
    const yAtShared = (value: number) =>
      pad.top +
      ((sharedScale.max - value) / (sharedScale.max - sharedScale.min)) * innerH;
    const yAtNorm = (value: number, min: number, max: number) =>
      pad.top + ((max - value) / (max - min)) * innerH;

    const series = plotFields.flatMap((field, index) => {
      const scale = isAbilityField(field) ? ABILITY_Y : ATTR_Y;
      const orderIndex = selected.indexOf(field);
      const color = colorForSeries(orderIndex >= 0 ? orderIndex : index);
      const pts = points.flatMap((point, pointIndex) => {
        const value = point.values[field];
        if (typeof value !== "number") return [];
        const y = normalize
          ? yAtNorm(value, scale.min, scale.max)
          : yAtShared(value);
        return [{ x: xAt(pointIndex), y, value, pointIndex }];
      });
      if (!pts.length) return [];
      return [{ field, color, path: linePath(pts), pts }];
    });

    const xLabels =
      points.length === 0
        ? []
        : points.map((point, index) => ({
            x: xAt(index),
            label: observationLabel(point, index),
          }));

    return {
      width,
      height,
      pad,
      innerW,
      innerH,
      yLabelTop: normalize ? "↑" : String(sharedScale.max),
      yLabelBottom: normalize ? "↓" : String(sharedScale.min),
      series,
      xLabels,
      xAt,
      empty: points.length === 0,
      noSeries: plotFields.length === 0,
    };
  }, [player.id, points, plotFields.join("\0"), selected.join("\0")]);

  const hoverPoint =
    hoverIndex != null && points[hoverIndex] ? points[hoverIndex]! : null;

  const onPlotMove = (event: MouseEvent<SVGSVGElement>) => {
    if (points.length === 0) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * chart.width;
    let best = 0;
    let bestDist = Infinity;
    for (let index = 0; index < points.length; index++) {
      const dist = Math.abs(chart.xAt(index) - x);
      if (dist < bestDist) {
        bestDist = dist;
        best = index;
      }
    }
    setHoverIndex(best);
  };

  return (
    <section className="dossier-panel tab-evidence-panel development-desk-panel">
      <div className="development-desk-body">
        <div className="development-desk-plot-block">
          <div className="development-desk-chart">
            <svg
              viewBox={`0 0 ${chart.width} ${chart.height}`}
              role="img"
              aria-label="Attribute development plot"
              onMouseMove={onPlotMove}
              onMouseLeave={() => setHoverIndex(null)}
            >
              <line
                x1={chart.pad.left}
                x2={chart.width - chart.pad.right}
                y1={chart.pad.top}
                y2={chart.pad.top}
                className="development-plot-rail"
              />
              <line
                x1={chart.pad.left}
                x2={chart.width - chart.pad.right}
                y1={chart.height - chart.pad.bottom}
                y2={chart.height - chart.pad.bottom}
                className="development-plot-rail"
              />
              <text x={6} y={chart.pad.top + 4} className="attr-history-axis">
                {chart.yLabelTop}
              </text>
              <text x={6} y={chart.height - chart.pad.bottom} className="attr-history-axis">
                {chart.yLabelBottom}
              </text>
              {chart.series.map((series) => (
                <g key={series.field}>
                  <path
                    d={series.path}
                    fill="none"
                    stroke={series.color}
                    strokeWidth={1.75}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                  {series.pts.map((pt) => (
                    <circle
                      key={`${series.field}-${pt.pointIndex}`}
                      cx={pt.x}
                      cy={pt.y}
                      r={hoverIndex === pt.pointIndex ? 3.25 : 2.25}
                      fill={series.color}
                    />
                  ))}
                </g>
              ))}
              {hoverIndex != null && points.length > 0 ? (
                <line
                  x1={chart.xAt(hoverIndex)}
                  x2={chart.xAt(hoverIndex)}
                  y1={chart.pad.top}
                  y2={chart.height - chart.pad.bottom}
                  className="development-plot-guide"
                />
              ) : null}
              {chart.xLabels.map((item, index) => (
                <text
                  key={`${item.label}-${index}`}
                  x={item.x}
                  y={chart.height - 4}
                  textAnchor="middle"
                  className="attr-history-axis"
                >
                  {item.label.length > 12 ? `${item.label.slice(0, 10)}…` : item.label}
                </text>
              ))}
              {chart.empty ? (
                <text
                  x={chart.pad.left + chart.innerW / 2}
                  y={chart.pad.top + chart.innerH / 2}
                  textAnchor="middle"
                  className="attr-history-axis"
                >
                  No Load observations yet
                </text>
              ) : chart.noSeries ? (
                <text
                  x={chart.pad.left + chart.innerW / 2}
                  y={chart.pad.top + chart.innerH / 2}
                  textAnchor="middle"
                  className="attr-history-axis"
                >
                  Select attributes to plot
                </text>
              ) : null}
            </svg>
            {hoverPoint && hoverIndex != null && plotFields.length > 0 ? (
              <div className="development-plot-hover" role="status">
                <strong>{observationLabel(hoverPoint, hoverIndex)}</strong>
                <ul>
                  {plotFields.map((field) => {
                    const value = hoverPoint.values[field];
                    const color = colorForSeries(selected.indexOf(field));
                    return (
                      <li key={field}>
                        <i style={{ background: color }} />
                        <span>{shortFieldLabel(field)}</span>
                        <b>{typeof value === "number" ? value : "—"}</b>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}
          </div>
        </div>

        <div className="development-desk-attrs">
          <AttributeDesk
            player={player}
            deltaMode="allTime"
            compact
            historySyncKey={historySyncKey}
            selectedFields={selectedSet}
            selectedOrder={selected}
            onToggleField={toggleField}
          />
        </div>
      </div>
    </section>
  );
}
