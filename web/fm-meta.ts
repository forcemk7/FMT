/** Known FM26 game client versions (newest first). */
export const FM_GAME_VERSIONS = [
  "FM26 26.3.2",
  "FM26 26.3.0",
  "FM26 26.2.0",
  "FM26 26.1.3",
  "FM26 26.1.1",
  "FM26 26.1.0",
  "FM26 26.0.6",
  "FM26 26.0.5",
  "FM26 26.0.4",
  "FM26 26.0.3",
  "FM26 26.0.2",
  "FM26 26.0.1",
  "FM26 26.0.0",
] as const;

/**
 * In-game database version labels.
 * Note: game patch 26.3.x still reports database as 26.2.
 */
export const FM_DATABASE_VERSIONS = ["26.2.0", "26.1.0", "26.0.0"] as const;

export const CUSTOM_DATABASE_VALUE = "__custom__";
