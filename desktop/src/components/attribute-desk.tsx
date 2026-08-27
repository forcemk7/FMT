"use client";

import type { CSSProperties, ReactNode } from "react";
import { useMemo } from "react";
import type { LivePlayer } from "@/domain/adapters";
import {
  GK_TECHNICAL_ATTRIBUTES,
  HIDDEN_ATTRIBUTES,
  MENTAL_ATTRIBUTES,
  PERSONALITY_ATTRIBUTES,
  PHYSICAL_ATTRIBUTES,
  SET_PIECE_ATTRIBUTES,
  TECHNICAL_ATTRIBUTES,
  gkGoalkeepingAttributeNames,
  gkTechnicalTooltipNames,
  isGoalkeeperPosition,
  resolveGoalkeeperRating,
  sortedAttributeEntries,
} from "@/domain/attribute-desk";
import { abilityToneFromScore, attributeTone } from "@/domain/attribute-tone";
import {
  allTimeDeltasForPlayer,
  colorForPlotField,
  recentDeltasForPlayer,
} from "@/domain/attribute-history";
import { AttrDeltaBadge } from "@/components/attr-delta-badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export type AttributeDeskDeltaMode = "none" | "recent" | "allTime";

function evidenceValue(map: Record<string, number | null> | undefined, attribute: string) {
  const value = map?.[attribute];
  return typeof value === "number" ? String(value) : "—";
}

function abilityLabel(value: number | null | undefined) {
  return typeof value === "number" ? String(value) : "—";
}

function abilityToneClass(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "attr-tone-mid";
  return `attr-tone-${abilityToneFromScore(value)}`;
}

function AttrRow({
  label,
  value,
  toneClass,
  title,
  delta,
  deltaAttribute,
  showDeltaColumn = false,
  fieldKey,
  selected = false,
  plotColor,
  onToggle,
}: {
  label: string;
  value: string;
  toneClass?: string;
  title?: string;
  delta?: number | null;
  deltaAttribute?: string;
  showDeltaColumn?: boolean;
  /** History / plot field key (defaults to label). */
  fieldKey?: string;
  selected?: boolean;
  plotColor?: string | null;
  onToggle?: (field: string) => void;
}) {
  const key = fieldKey ?? label;
  const interactive = typeof onToggle === "function";
  const className = [
    "attr-row",
    interactive ? "is-interactive" : "",
    selected ? "is-selected" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const style =
    selected && plotColor
      ? ({
          ["--plot-swatch" as string]: plotColor,
        } as CSSProperties)
      : undefined;

  const body = (
    <>
      <span className="attr-row-label">{label}</span>
      <span className={`attr-row-values${showDeltaColumn ? " has-delta-col" : ""}`}>
        {showDeltaColumn ? (
          <span className="attr-delta-slot" aria-hidden={delta == null || delta === 0}>
            <AttrDeltaBadge attribute={deltaAttribute ?? label} delta={delta} />
          </span>
        ) : null}
        <strong className={`attr-row-value ${toneClass ?? ""}`.trim()} title={title}>
          {value}
        </strong>
      </span>
    </>
  );

  if (interactive) {
    return (
      <button
        type="button"
        className={className}
        style={style}
        aria-pressed={selected}
        onClick={() => onToggle(key)}
      >
        {body}
      </button>
    );
  }

  return (
    <div className={className} style={style}>
      {body}
    </div>
  );
}


function AttributeRows({
  names,
  values,
  deltas,
  selectedFields,
  selectedOrder,
  onToggleField,
}: {
  names: readonly string[];
  values: Record<string, number | null> | undefined;
  deltas?: Record<string, number | null>;
  selectedFields?: ReadonlySet<string>;
  selectedOrder?: readonly string[];
  onToggleField?: (field: string) => void;
}) {
  const showDeltaColumn = deltas !== undefined;
  return (
    <div className="attr-row-list">
      {names.map((name) => {
        const raw = values?.[name];
        const tone = typeof raw === "number" ? attributeTone(name, raw) : "mid";
        const selected = selectedFields?.has(name) ?? false;
        return (
          <AttrRow
            key={name}
            label={name}
            value={evidenceValue(values, name)}
            toneClass={`attr-tone attr-tone-${tone}`}
            delta={deltas?.[name]}
            showDeltaColumn={showDeltaColumn}
            selected={selected}
            plotColor={selected && selectedOrder ? colorForPlotField(name, selectedOrder) : null}
            onToggle={onToggleField}
          />
        );
      })}
    </div>
  );
}

function AttributeTooltipList({
  names,
  values,
}: {
  names: readonly string[];
  values: Record<string, number | null> | undefined;
}) {
  return (
    <ul className="attribute-tooltip-list">
      {sortedAttributeEntries(names, values).map(({ name, value }) => {
        const tone = typeof value === "number" ? attributeTone(name, value) : "mid";
        return (
          <li key={name}>
            <span>{name}</span>
            <strong className={`attr-tone attr-tone-${tone}`}>
              {value == null ? "—" : String(value)}
            </strong>
          </li>
        );
      })}
    </ul>
  );
}

function AttributeHeading({
  title,
  tooltipNames,
  values,
}: {
  title: string;
  tooltipNames?: readonly string[];
  values?: Record<string, number | null> | undefined;
}) {
  if (tooltipNames?.length) {
    return (
      <Tooltip>
        <TooltipTrigger
          render={<h3 className="attribute-column-heading attribute-column-heading-tip">{title}</h3>}
        />
        <TooltipContent side="bottom" align="start" className="attribute-tooltip">
          <AttributeTooltipList names={tooltipNames} values={values} />
        </TooltipContent>
      </Tooltip>
    );
  }
  return <h3 className="attribute-column-heading">{title}</h3>;
}

function AttributeGroup({
  title,
  names,
  values,
  col,
  headerTooltipNames,
  footer,
  deltas,
  selectedFields,
  selectedOrder,
  onToggleField,
}: {
  title: string;
  names: readonly string[];
  values: Record<string, number | null> | undefined;
  col?: 1 | 2 | 3;
  headerTooltipNames?: readonly string[];
  footer?: ReactNode;
  deltas?: Record<string, number | null>;
  selectedFields?: ReadonlySet<string>;
  selectedOrder?: readonly string[];
  onToggleField?: (field: string) => void;
}) {
  return (
    <section className="attribute-column" data-col={col}>
      <AttributeHeading title={title} tooltipNames={headerTooltipNames} values={values} />
      <AttributeRows
        names={names}
        values={values}
        deltas={deltas}
        selectedFields={selectedFields}
        selectedOrder={selectedOrder}
        onToggleField={onToggleField}
      />
      {footer}
    </section>
  );
}

function GoalkeeperRatingBlock({ player }: { player: LivePlayer }) {
  const rating = resolveGoalkeeperRating(player.goalkeeperRating, player.attributes);
  return (
    <div className="attribute-extension attribute-gk-rating">
      <AttributeHeading
        title="Goalkeeping"
        tooltipNames={gkGoalkeepingAttributeNames()}
        values={player.attributes}
      />
      <div className="attr-row-list">
        <AttrRow
          label="Goalkeeper Rating"
          value={rating == null ? "—" : `${rating} / 10`}
          toneClass={
            rating == null
              ? "attr-tone attr-tone-mid"
              : `attr-tone attr-tone-${attributeTone("Ability", rating * 2)}`
          }
        />
      </div>
    </div>
  );
}

function GeneralColumn({
  player,
  col = 3,
  deltas,
  selectedFields,
  selectedOrder,
  onToggleField,
}: {
  player: LivePlayer;
  col?: 1 | 2 | 3;
  deltas?: Record<string, number | null>;
  selectedFields?: ReadonlySet<string>;
  selectedOrder?: readonly string[];
  onToggleField?: (field: string) => void;
}) {
  const rows = [
    {
      label: "Ability",
      field: "CA",
      value: abilityLabel(player.currentAbility),
      toneClass: abilityToneClass(player.currentAbility),
    },
    {
      label: "Potential",
      field: "PA",
      value: abilityLabel(player.potentialAbility),
      toneClass: abilityToneClass(player.potentialAbility),
    },
  ];

  const showDeltaColumn = deltas !== undefined;

  return (
    <section className="attribute-column attribute-general" data-col={col}>
      <AttributeHeading title="General" />
      <div className="attr-row-list">
        {rows.map((row) => {
          const selected = selectedFields?.has(row.field) ?? false;
          return (
            <AttrRow
              key={row.label}
              label={row.label}
              fieldKey={row.field}
              value={row.value}
              toneClass={row.toneClass}
              title={row.value === "—" ? undefined : row.value}
              delta={deltas?.[row.field]}
              deltaAttribute={row.field}
              showDeltaColumn={showDeltaColumn}
              selected={selected}
              plotColor={selected && selectedOrder ? colorForPlotField(row.field, selectedOrder) : null}
              onToggle={onToggleField}
            />
          );
        })}
      </div>
    </section>
  );
}

/** Fixed 3-column FM desk: stacked Set Pieces / GK Technical under play attrs (matches in-game). */
export function AttributeDesk({
  player,
  deltaMode = "none",
  compact = false,
  historySyncKey = null,
  selectedFields,
  selectedOrder,
  onToggleField,
}: {
  player: LivePlayer;
  deltaMode?: AttributeDeskDeltaMode;
  compact?: boolean;
  historySyncKey?: string | null;
  selectedFields?: ReadonlySet<string>;
  /** Selection order — drives plot swatch colors on rows. */
  selectedOrder?: readonly string[];
  onToggleField?: (field: string) => void;
}) {
  const gk = isGoalkeeperPosition(player.positions);
  const attrs = player.attributes;
  const deltas = useMemo(() => {
    if (deltaMode === "recent") return recentDeltasForPlayer(player.id);
    if (deltaMode === "allTime") return allTimeDeltasForPlayer(player.id);
    return undefined;
  }, [player.id, deltaMode, historySyncKey]);

  const select = { selectedFields, selectedOrder, onToggleField };

  return (
    <div
      className={[
        "attribute-desk",
        gk ? "attribute-desk-gk" : "attribute-desk-outfield",
        compact ? "attribute-desk-compact" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {gk ? (
        <div className="attribute-desk-row attribute-desk-primary">
          <AttributeGroup
            title="Goalkeeping"
            names={gkGoalkeepingAttributeNames()}
            values={attrs}
            col={1}
            deltas={deltas}
            {...select}
          />
          <AttributeGroup
            title="Mental"
            names={MENTAL_ATTRIBUTES}
            values={attrs}
            col={2}
            deltas={deltas}
            {...select}
          />
          <div className="attribute-column-stack" data-col={3}>
            <AttributeGroup
              title="Physical"
              names={PHYSICAL_ATTRIBUTES}
              values={attrs}
              deltas={deltas}
              {...select}
            />
            <AttributeGroup
              title="Technical"
              names={GK_TECHNICAL_ATTRIBUTES}
              values={attrs}
              headerTooltipNames={gkTechnicalTooltipNames()}
              deltas={deltas}
              {...select}
            />
          </div>
        </div>
      ) : (
        <div className="attribute-desk-row attribute-desk-primary">
          <div className="attribute-column-stack" data-col={1}>
            <AttributeGroup
              title="Technical"
              names={TECHNICAL_ATTRIBUTES}
              values={attrs}
              deltas={deltas}
              {...select}
            />
            <AttributeGroup
              title="Set Pieces"
              names={SET_PIECE_ATTRIBUTES}
              values={attrs}
              deltas={deltas}
              {...select}
            />
          </div>
          <AttributeGroup
            title="Mental"
            names={MENTAL_ATTRIBUTES}
            values={attrs}
            col={2}
            deltas={deltas}
            {...select}
          />
          <div className="attribute-column-stack attribute-column-stack-anchor" data-col={3}>
            <AttributeGroup
              title="Physical"
              names={PHYSICAL_ATTRIBUTES}
              values={attrs}
              deltas={deltas}
              {...select}
            />
            <GoalkeeperRatingBlock player={player} />
          </div>
        </div>
      )}
      <div className="attribute-desk-row attribute-desk-footer">
        <AttributeGroup
          title="Hidden"
          names={HIDDEN_ATTRIBUTES}
          values={player.hiddenAttributes}
          col={1}
          deltas={deltas}
          {...select}
        />
        <AttributeGroup
          title="Personality"
          names={PERSONALITY_ATTRIBUTES}
          values={player.personalityAttributes}
          col={2}
          deltas={deltas}
          {...select}
        />
        <GeneralColumn player={player} col={3} deltas={deltas} {...select} />
      </div>
    </div>
  );
}
