import { useSyncExternalStore } from "react";

/**
 * User-facing app preferences (Settings > User Preferences), distinct from
 * diagnostics/status. New preferences (UI density, theme, non-club attribute
 * masking, ...) get a new key here — parsePreferences merges onto defaults so
 * older persisted payloads missing a newer key still work.
 */
export type FmtPreferences = {
  hidePA: boolean;
};

const STORAGE_KEY = "fmt-preferences-v1";

const DEFAULT_PREFERENCES: FmtPreferences = {
  hidePA: false,
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
    return parsePreferences(window.localStorage.getItem(STORAGE_KEY));
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
