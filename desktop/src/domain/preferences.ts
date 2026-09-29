import { useSyncExternalStore } from "react";

/**
 * User-facing app preferences (Settings > User Preferences), distinct from
 * diagnostics/status. New preferences (UI density, theme, non-club attribute
 * masking, ...) get a new key here — parsePreferences merges onto defaults so
 * older persisted payloads missing a newer key still work.
 */
export type FmtPreferences = {
  hidePA: boolean;
  autoLoadOnStartup: boolean;
  /**
   * UI density (T293). false = today's compact size; true = the whole UI is
   * scaled up via root `zoom` (see `html[data-density="large"]` in globals.css).
   */
  largeUi: boolean;
  /**
   * Anonymous, per-install telemetry id (T290). Not user-facing/toggleable —
   * lives here only because this is the existing persisted store, not because
   * it's a preference. Generated once on first load if missing (see
   * loadPreferences) rather than given a static default, since it must be
   * unique per install.
   */
  telemetryId: string;
};

const STORAGE_KEY = "fmt-preferences-v1";

const DEFAULT_PREFERENCES: FmtPreferences = {
  hidePA: true,
  autoLoadOnStartup: true,
  largeUi: false,
  telemetryId: "",
};

function parsePreferences(raw: string | null): FmtPreferences {
  if (!raw) return { ...DEFAULT_PREFERENCES };
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return { ...DEFAULT_PREFERENCES };
    return { ...DEFAULT_PREFERENCES, ...(parsed as Partial<FmtPreferences>) };
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

function loadPreferences(): FmtPreferences {
  if (typeof window === "undefined") return { ...DEFAULT_PREFERENCES };
  try {
    const prefs = parsePreferences(window.localStorage.getItem(STORAGE_KEY));
    if (!prefs.telemetryId) {
      prefs.telemetryId = crypto.randomUUID();
      savePreferences(prefs);
    }
    return prefs;
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

function savePreferences(prefs: FmtPreferences): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // storage unavailable (private mode, quota) — preference just won't persist
  }
}

let current: FmtPreferences = loadPreferences();
const listeners = new Set<() => void>();

function getSnapshot(): FmtPreferences {
  return current;
}

function getServerSnapshot(): FmtPreferences {
  return DEFAULT_PREFERENCES;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setPreference<K extends keyof FmtPreferences>(
  key: K,
  value: FmtPreferences[K],
): void {
  current = { ...current, [key]: value };
  savePreferences(current);
  for (const listener of listeners) listener();
}

export function usePreferences(): FmtPreferences {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/** Non-React read for callers outside a component (e.g. the telemetry client). */
export function getPreferences(): FmtPreferences {
  return current;
}
