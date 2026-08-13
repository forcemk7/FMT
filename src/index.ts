export {
  HAS_ATTRIBUTES,
  HIDDEN_ATTRIBUTES,
  PERSONALITY_ATTRIBUTES,
  UNMODELED_HAS_ATTRIBUTES,
  UNMODELED_HIDDEN_ATTRIBUTES,
  VISIBLE_ATTRIBUTES,
  TRACKED_ATTRIBUTES,
  CHECKER_TABLE_ATTRIBUTES,
  ATTRIBUTE_LABELS,
  PERSONALITY_ATTRIBUTE_LABELS,
  PERSONALITY_ATTRIBUTE_ABBR,
  HIDDEN_ATTRIBUTE_LABELS,
  ATTRIBUTE_DESCRIPTIONS,
  FULL_RANGE,
  attributeTone,
  isUnmodeledHiddenAttribute,
  hiddenQualityScore,
  hiddenQualityFloorScore,
  HA_QUALITY_WEIGHTS,
  HA_VISIBLE_QUALITY_WEIGHTS,
  HA_QUALITY_WEIGHT_SUM,
  HA_IMPORTANCE_WEIGHT,
  invertControversy,
  haQualityWeightSum,
  formatHaQualityWeightsTip,
  HIDDEN_QUALITY_GOOD_FLOOR,
  HIDDEN_QUALITY_BAD_CEILING,
  HIDDEN_QUALITY_INDEX_MAX,
  HIDDEN_QUALITY_ELITE_TOP_FRACTION,
  FM_ATTRIBUTE_ELITE_MIN,
  fmEliteHasFloor,
  uniqueHasTopFractionFloor,
  uniqueHasBottomFractionCeiling,
  resolveEliteHasFloor,
  resolvePoorHasCeiling,
  hiddenQualityTone,
  type HasAttribute,
  type HiddenAttribute,
  type PersonalityAttribute,
  type UnmodeledHasAttribute,
  type UnmodeledHiddenAttribute,
  type VisibleAttribute,
  type TrackedAttribute,
  type AttributeRange,
  type AttributeEstimate,
  type AttributeEstimates,
  type AttributeTone,
  type HaVisibleKnown,
} from "./domain/attributes.js";

export {
  parseRange,
  formatRange,
  intersect,
  intersectAll,
  rawIntersect,
  isEmptyRange,
  midpoint,
  toEstimate,
} from "./domain/range.js";

export {
  MEDIA_STYLE_TAGS,
  MEDIA_STYLE_ABBREVIATIONS,
  type MediaStyleTag,
  type PlayerSignals,
  type AppliedConstraint,
} from "./domain/observations.js";

export type {
  Catalog,
  PersonalityDefinition,
  MediaHandlingDefinition,
  MediaCase,
  PersonalityConditional,
} from "./catalog/types.js";

export {
  loadCatalog,
  findPersonality,
  findMediaHandling,
  parseMediaHandlingInput,
  formatMediaHandlingLabel,
} from "./catalog/lookup.js";

export {
  estimatePlayer,
  type EstimateOptions,
  type EstimateResult,
  type FieldViolation,
} from "./inference/estimate.js";

export {
  isPersonalityMediaCompatible,
  personalityMediaContradictions,
} from "./inference/bands.js";

export {
  rankPersonalityMediaCombos,
  rankPersonalityMediaCombosUnified,
  COMBO_RANK_SORT_HINT,
  type ComboPopulationLabel,
  type ComboRankBand,
  type ComboRankBands,
  type ComboRankEntry,
  type ComboRankMids,
  type ComboRanking,
  type RankCombosOptions,
  type RankCombosUnifiedOptions,
  type RankPopulationMode,
} from "./inference/rank-combos.js";

export {
  buildMentorLookForFromFloor,
  mentoringFocus,
  mentoringRole,
  menteePathUnderMentor,
  findMentoringGroupsForSubject,
  findInfluenceSafeMentoringGroups,
  isMentoringInfluenceSubject,
  mentoringAttributeValues,
  mentoringMenteeAttributeEvidence,
  defaultMentoringUnitRoles,
  evaluateMentoringUnit,
  mentoringInfluenceLevel,
  mentoringInfluenceScore,
  rankMentoringInfluence,
  scoreSafeInfluence,
  mentoringHierarchyBias,
  MENTORING_YOUNG_AGE,
  protectedTraits,
  MENTORING_TRAITS,
  MENTORING_DISPLAY_ORDER,
  mentoringTraitWeight,
  mentoringTraitIsKnown,
  type MentoringAttrReading,
  type MentoringCandidate,
  type MentoringDirectedEdge,
  type MentoringFloorBoard,
  type MentoringFloorOption,
  type MentoringHierarchyLabel,
  type MentoringInfluenceLevel,
  type MentoringInfluenceSafeGroup,
  type MentoringInfluenceSeat,
  type MentoringMenteeAttrReading,
  type MentoringPackageHint,
  type MentoringPairPath,
  type MentoringRole,
  type MentoringSearchProfile,
  type MentoringSquadPair,
  type MentoringGroupShape,
  type MentoringGroupSuggestion,
  type MentoringSafeGroupShape,
  type MentoringSubject,
  type MentoringTrait,
  type MentoringTraitBand,
  type MentoringUnitEvaluation,
  type MentoringUnitMember,
  type MentoringUnitShape,
  type MentorRosterFilter,
  type SafeInfluenceEdge,
} from "./inference/mentoring.js";

export {
  PENALTY_TAKER_ATTRS,
  PENALTY_TAKER_WEIGHTS,
  PENALTY_TAKER_WEIGHT_SUM,
  penaltyTakerScore,
  rankPenaltyTakers,
  type PenaltyTakerAttr,
  type PenaltyTakerCandidate,
  type PenaltyTakerRankEntry,
} from "./inference/penalty-taker.js";

export { type CaseMode } from "./inference/cases.js";

export {
  comboFeasibleForAttrs,
  type MatchableAttrs,
} from "./inference/match-combo.js";

export {
  CREDITS,
  type CreditLink,
  type CreditPerson,
  type CreditSection,
} from "./credits.js";
