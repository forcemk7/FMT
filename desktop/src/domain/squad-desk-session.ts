/** In-memory Squad desk navigation — survives remount when opening a player. */

export type SquadDeskRosterFilter = "atClub" | "loanedIn" | "loanedOut";

let selectedTeamUid: string | null = null;
let scrollTop = 0;
/** While true, ignore scroll writes so a shared `.app-main` reset cannot clobber the stash. */
let scrollFrozen = false;
/** Per-team roster status filters for the current save session. */
const rosterFiltersByTeamUid = new Map<string, SquadDeskRosterFilter[]>();

export function getSquadDeskSelectedTeamUid(): string | null {
  return selectedTeamUid;
}

export function setSquadDeskSelectedTeamUid(teamUid: string | null): void {
  selectedTeamUid = teamUid;
}

export function getSquadDeskRosterFilters(
  teamUid: string,
): SquadDeskRosterFilter[] | null {
  const stored = rosterFiltersByTeamUid.get(teamUid);
  return stored ? [...stored] : null;
}

export function setSquadDeskRosterFilters(
  teamUid: string,
  statuses: Iterable<SquadDeskRosterFilter>,
): void {
  // Squad Filter is single-status (T209); keep only the first entry.
  const unique = [...new Set(statuses)].slice(0, 1);
  if (unique.length === 0) {
    rosterFiltersByTeamUid.delete(teamUid);
    return;
  }
  rosterFiltersByTeamUid.set(teamUid, unique);
}

export function clearSquadDeskRosterFilters(): void {
  rosterFiltersByTeamUid.clear();
}

export function getSquadDeskScrollTop(): number {
  return scrollTop;
}

export function setSquadDeskScrollTop(top: number): void {
  if (scrollFrozen) return;
  scrollTop = Number.isFinite(top) && top > 0 ? top : 0;
}

/** Capture squad scroll and freeze it. Do not touch the DOM — next screen zeros `.app-main`. */
export function stashSquadScroll(): void {
  if (typeof document !== "undefined") {
    const main = document.querySelector(".app-main");
    if (main instanceof HTMLElement) {
      const top = main.scrollTop;
      scrollTop = Number.isFinite(top) && top > 0 ? top : scrollTop;
    }
  }
  scrollFrozen = true;
}

export function unfreezeSquadScroll(): void {
  scrollFrozen = false;
}

export function readAppMainScrollTop(): number {
  if (typeof document === "undefined") return 0;
  const main = document.querySelector(".app-main");
  return main instanceof HTMLElement ? main.scrollTop : 0;
}

export function writeAppMainScrollTop(top: number): void {
  if (typeof document === "undefined") return;
  const main = document.querySelector(".app-main");
  if (main instanceof HTMLElement) {
    main.scrollTop = top;
  }
}

/**
 * One-shot restore after Squad remount.
 * No ResizeObserver loop — that fights fast user scrolling and feels animated/jumpy.
 * Any wheel/pointer from the user cancels pending re-apply immediately.
 */
export function restoreSquadScrollToMain(): () => void {
  const top = scrollTop;
  if (top <= 0) {
    scrollFrozen = false;
    return () => undefined;
  }

  scrollFrozen = true;
  let cancelled = false;
  const main =
    typeof document !== "undefined" ? document.querySelector(".app-main") : null;

  const release = () => {
    if (cancelled) return;
    cancelled = true;
    scrollFrozen = false;
    if (main instanceof HTMLElement) {
      main.removeEventListener("wheel", onUser, true);
      main.removeEventListener("pointerdown", onUser, true);
      main.removeEventListener("touchstart", onUser, true);
    }
  };

  const onUser = () => {
    release();
  };

  writeAppMainScrollTop(top);

  if (main instanceof HTMLElement) {
    main.addEventListener("wheel", onUser, { capture: true, passive: true });
    main.addEventListener("pointerdown", onUser, { capture: true });
    main.addEventListener("touchstart", onUser, { capture: true, passive: true });
  }

  const frame = window.requestAnimationFrame(() => {
    if (cancelled) return;
    writeAppMainScrollTop(top);
    release();
  });

  return () => {
    window.cancelAnimationFrame(frame);
    release();
  };
}
