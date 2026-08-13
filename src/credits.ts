/**
 * Third-party / community credits for research and tools this project builds on.
 * Intended for a future About / Credits UI — no presentation yet.
 */

export type CreditPerson = {
  name: string;
  note?: string;
};

export type CreditLink = {
  label: string;
  url: string;
};

export type CreditSection = {
  id: string;
  title: string;
  summary: string;
  people: CreditPerson[];
  links: CreditLink[];
};

export const CREDITS: CreditSection[] = [
  {
    id: "has-personality-media-ranking",
    title: "Personality / media handling ranking (HAS)",
    summary:
      "Community ranking / guide for personality × media-handling quality (Hidden Attribute Score).",
    people: [
      { name: "Beni", note: "Steam Workshop" },
      { name: "Weasel", note: "Steam Workshop" },
    ],
    links: [
      {
        label: "Steam Workshop guide",
        url: "https://steamcommunity.com/sharedfiles/filedetails/?id=3141707601",
      },
    ],
  },
  {
    id: "ha-calculator",
    title: "Hidden attribute checker (calculator)",
    summary:
      "Spreadsheet / calculator lineage for estimating hidden attributes from personality and media handling.",
    people: [
      { name: "Noxuous", note: "Calculator" },
      { name: "JAwtunes", note: "Calculator" },
      { name: "BlueZero", note: "Updated to modern FM" },
      {
        name: "macaco3001",
        note: "Reupdated — bug fixes from own research; calculator compatible for non-newgens",
      },
    ],
    links: [
      {
        label: "SI forums — Ultimate Personality / Media Handling Guide",
        url: "http://community.sigames.com/showthread.php/307808-The-Ultimate-Personality-Media-Handling-Guide",
      },
    ],
  },
  {
    id: "personality-mhs-research",
    title: "Personality and media handling research",
    summary:
      "Personality and media-handling style (MHS) research underlying the calculator bands.",
    people: [{ name: "macaco3001" }],
    links: [],
  },
  {
    id: "ctrl-26-skin",
    title: "CTRL 26 skin",
    summary:
      "Football Manager 26 skin (CTRL 26) used as reference / inspiration for UI work.",
    people: [
      {
        name: "Matt (MW90)",
        note: "Creator — SortItOutSI uploader; GitHub matt-wadsworth/ctrl-fm",
      },
    ],
    links: [
      {
        label: "SortItOutSI — CTRL 26",
        url: "https://sortitoutsi.net/content/76287/ctrl-26-10",
      },
      {
        label: "GitHub — ctrl-fm",
        url: "https://github.com/matt-wadsworth/ctrl-fm",
      },
    ],
  },
];
