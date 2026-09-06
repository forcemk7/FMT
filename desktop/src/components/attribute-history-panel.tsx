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
/** FM development plot always uses a fixed 0–20 axis. */
const PLOT_Y = { min: 0, max: 20 } as const;
const Y_TICKS = [0, 5, 10, 15, 20] as const;
const ENDPOINT_GOLD = "#f0c14a";

/**
 * FM-style path: horizontal tangents so plateaus stay flat and level changes
 * ease with a smooth S-curve between observations.
 */
function fmSmoothPath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) return `M ${pts[0]!.x} ${pts[0]!.y}`;
  if (pts.length === 2) {
    const a = pts[0]!;
    const b = pts[1]!;
    const dx = (b.x - a.x) / 3;
    return `M ${a.x} ${a.y} C ${a.x + dx} ${a.y} ${b.x - dx} ${b.y} ${b.x} ${b.y}`;
  }
  let d = `M ${pts[0]!.x} ${pts[0]!.y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i]!;
    const b = pts[i + 1]!;
    const dx = (b.x - a.x) / 3;
    d += ` C ${a.x + dx} ${a.y} ${b.x - dx} ${b.y} ${b.x} ${b.y}`;
  }
  return d;
}

function shortFieldLabel(field: string): string {
  if (field === "CA") return "Ability";
  if (field === "PA") return "Potential";
  return field;
}

function formatWallClockShort(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Observation";
  return formatFmDateParts(date.getUTCDate(), date.getUTCMonth(), date.getUTCFullYear() % 100, true);
}

const MONTH_SHORT = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

function formatFmDateParts(
  day: number,
  monthIndex: number,
  yearTwo: number,
  withYear: boolean,
): string {
  const month = MONTH_SHORT[monthIndex] ?? "Jan";
  if (!withYear) return `${day} ${month}`;
  return `${day} ${month} ${String(yearTwo).padStart(2, "0")}`;
}

/** Parse ISO / FM-ish game dates into plot tick labels (FM: "21 Jun 42", then "22 Aug"). */
function observationLabel(
  point: AttrHistoryPoint,
  index: number,
  prior: AttrHistoryPoint | null,
): string {
  const parsed = parseObservationDate(point);
  if (parsed) {
    const priorParsed = prior ? parseObservationDate(prior) : null;
    const withYear =
      index === 0 || !priorParsed || priorParsed.year !== parsed.year;
    return formatFmDateParts(parsed.day, parsed.monthIndex, parsed.year % 100, withYear);
  }
  const gameDate = point.gameDate?.trim();
  if (gameDate) return gameDate;
  if (point.at?.trim()) return formatWallClockShort(point.at);
  return `Obs ${index + 1}`;
}

function parseObservationDate(
  point: AttrHistoryPoint,
): { day: number; monthIndex: number; year: number } | null {
  const raw = point.gameDate?.trim() || point.at?.trim() || "";
  if (!raw) return null;
  // YYYY-MM-DD or ISO datetime
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) {
    return {
      year: Number(iso[1]),
      monthIndex: Number(iso[2]) - 1,
      day: Number(iso[3]),
    };
  }
  const wall = new Date(raw);
  if (!Number.isNaN(wall.getTime()) && raw.includes("T")) {
    return {
      year: wall.getUTCFullYear(),
      monthIndex: wall.getUTCMonth(),
      day: wall.getUTCDate(),
    };
  }
  return null;
}

function isAbilityField(field: string): boolean {
  return field === "CA" || field === "PA";
}

/** Map CA/PA (≈1–200) onto FM's 0–20 ability axis; attrs already 1–20. */
function plotValue(field: string, value: number): number {
  if (isAbilityField(field)) return value / 10;
  return value;
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
    const height = 168;
    const pad = { left: 40, right: 12, top: 12, bottom: 28 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;

    const xAt = (index: number) => {
      if (points.length <= 1) return pad.left + innerW / 2;
      return pad.left + (index / (points.length - 1)) * innerW;
    };

    const yAt = (value: number) => {
      const clamped = Math.min(PLOT_Y.max, Math.max(PLOT_Y.min, value));
      return pad.top + ((PLOT_Y.max - clamped) / (PLOT_Y.max - PLOT_Y.min)) * innerH;
    };

    const abilityOnly =
      plotFields.length > 0 && plotFields.every(isAbilityField);
    const axisTitle = abilityOnly ? "Ability" : "Attributes";

    const series = plotFields.flatMap((field, index) => {
      const orderIndex = selected.indexOf(field);
      const color = colorForSeries(orderIndex >= 0 ? orderIndex : index);
      const pts = points.flatMap((point, pointIndex) => {
        const value = point.values[field];
        if (typeof value !== "number") return [];
        return [
          {
            x: xAt(pointIndex),
            y: yAt(plotValue(field, value)),
            value,
            pointIndex,
          },
        ];
      });
      if (!pts.length) return [];
      return [{ field, color, path: fmSmoothPath(pts), pts }];
    });

    const xLabels =
      points.length === 0
        ? []
        : points.map((point, index) => ({
            x: xAt(index),
            label: observationLabel(point, index, points[index - 1] ?? null),
          }));

    const yTicks = Y_TICKS.map((tick) => ({
      tick,
      y: yAt(tick),
    }));

    return {
      width,
      height,
      pad,
      innerW,
      innerH,
      axisTitle,
      abilityOnly,
      series,
      xLabels,
      yTicks,
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

  const hoverLabel =
    hoverPoint && hoverIndex != null
      ? observationLabel(hoverPoint, hoverIndex, points[hoverIndex - 1] ?? null)
      : null;

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
              <text
                className="development-plot-axis-title"
                transform={`translate(11 ${chart.pad.top + chart.innerH / 2}) rotate(-90)`}
                textAnchor="middle"
              >
                {chart.axisTitle}
              </text>
              {chart.yTicks.map((item) => (
                <g key={item.tick}>
                  <line
                    x1={chart.pad.left}
                    x2={chart.width - chart.pad.right}
                    y1={item.y}
                    y2={item.y}
                    className={
                      item.tick === 0
                        ? "development-plot-baseline"
                        : "development-plot-grid"
                    }
                  />
                  <text
                    x={chart.pad.left - 6}
                    y={item.y + 3}
                    textAnchor="end"
                    className="attr-history-axis"
                  >
                    {item.tick}
                  </text>
                </g>
              ))}
              <line
                x1={chart.pad.left}
                x2={chart.pad.left}
                y1={chart.pad.top}
                y2={chart.height - chart.pad.bottom}
                className="development-plot-baseline"
              />
              {chart.series.map((series) => {
                const last = series.pts[series.pts.length - 1];
                const showEndpoint = chart.abilityOnly && last;
                return (
                  <g key={series.field}>
                    <path
                      d={series.path}
                      fill="none"
                      stroke={series.color}
                      strokeWidth={1.5}
                      strokeLinejoin="round"
                      strokeLinecap="round"
                      className="development-plot-line"
                    />
                    {showEndpoint ? (
                      <circle
                        cx={last.x}
                        cy={last.y}
                        r={3}
                        fill={ENDPOINT_GOLD}
                        className="development-plot-endpoint"
                      />
                    ) : null}
                    {hoverIndex != null
                      ? series.pts
                          .filter((pt) => pt.pointIndex === hoverIndex)
                          .map((pt) => (
                            <circle
                              key={`${series.field}-hover-${pt.pointIndex}`}
                              cx={pt.x}
                              cy={pt.y}
                              r={3}
                              fill={series.color}
                            />
                          ))
                      : null}
                  </g>
                );
              })}
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
                <g key={`${item.label}-${index}`}>
                  <line
                    x1={item.x}
                    x2={item.x}
                    y1={chart.height - chart.pad.bottom}
                    y2={chart.height - chart.pad.bottom + 4}
                    className="development-plot-xtick"
                  />
                  <text
                    x={item.x}
                    y={chart.height - 6}
                    textAnchor="middle"
                    className="attr-history-axis"
                  >
                    {item.label.length > 11 ? `${item.label.slice(0, 9)}…` : item.label}
                  </text>
                </g>
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
            {hoverPoint && hoverIndex != null && plotFields.length > 0 && hoverLabel ? (
              <div className="development-plot-hover" role="status">
                <strong>{hoverLabel}</strong>
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
