"use client";

/**
 * Honest product map — what is live vs later vs not FMT.
 * Not a fake feature desk.
 */
export function RoadmapScreen() {
  return (
    <main className="screen roadmap-screen">
      <header className="roadmap-hero">
        <p className="section-kicker">Product map</p>
        <h1>What FMT is building</h1>
        <p>
          Modest roadmap. Live surfaces work. Everything else is labeled so we do not
          ship GlassScout-style empty chrome.
        </p>
      </header>

      <section className="roadmap-block roadmap-live" aria-labelledby="roadmap-live">
        <h2 id="roadmap-live">Step 1 — live now</h2>
        <ul>
          <li>
            <strong>Squad</strong>
            <span>Managed club from live FM26 memory.</span>
          </li>
          <li>
            <strong>Player desk</strong>
            <span>Attributes, CA / PA / HA, tones — open any squad player.</span>
          </li>
          <li>
            <strong>Attribute history</strong>
            <span>Append-only movement tracking to replace the spreadsheet.</span>
          </li>
        </ul>
      </section>

      <section className="roadmap-block roadmap-later" aria-labelledby="roadmap-later">
        <h2 id="roadmap-later">Step 2 — later</h2>
        <ul>
          <li>
            <strong>World index</strong>
            <span>Full-save reach at usable speed (replace FMLE). Needs a real player-list path — not funded until Step 1 is daily habit.</span>
          </li>
          <li>
            <strong>Mentoring / loans</strong>
            <span>Only if the club desk is already useful every session.</span>
          </li>
        </ul>
      </section>

      <section className="roadmap-block roadmap-not" aria-labelledby="roadmap-not">
        <h2 id="roadmap-not">Not FMT (for now)</h2>
        <ul>
          <li>
            <strong>Tactical Board / Scout Room / Dashboard pulse</strong>
            <span>GlassScout shell leftovers — stripped so they do not pretend to be product.</span>
          </li>
          <li>
            <strong>Blind memory spray as “world”</strong>
            <span>Works on some native saves; too slow and fragile for the bar we care about.</span>
          </li>
        </ul>
      </section>
    </main>
  );
}
