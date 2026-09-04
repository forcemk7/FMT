/** In-memory Squad desk navigation — survives remount when opening a player. */

let selectedTeamUid: string | null = null;
let scrollTop = 0;

export function getSquadDeskSelectedTeamUid(): string | null {
  return selectedTeamUid;
}

export function setSquadDeskSelectedTeamUid(teamUid: string | null): void {
  selectedTeamUid = teamUid;
}

export function getSquadDeskScrollTop(): number {
  return scrollTop;
}

export function setSquadDeskScrollTop(top: number): void {
  scrollTop = Number.isFinite(top) && top > 0 ? top : 0;
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
