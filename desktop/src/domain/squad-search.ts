/** Fold diacritics for forgiving squad header search (Loop A lookup). */

export function foldSearchText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase();
}

/** True when folded name contains folded query (substring). Empty query = no match. */
export function playerMatchesSquadSearch(name: string, query: string): boolean {
  const q = foldSearchText(query).trim();
  if (!q) return false;
  return foldSearchText(name).includes(q);
}
