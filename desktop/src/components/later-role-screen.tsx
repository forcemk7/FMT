"use client";

/** Muted roadmap stub for role tabs that are not Loop A/B yet. */
export function LaterRoleScreen({ role }: { role: string }) {
  return (
    <main className="screen later-role-screen">
      <p className="section-kicker">Roadmap · later</p>
      <h1>{role}</h1>
      <p>
        Visual placeholder for the in-game club role you are targeting. No desk here until
        this role has its own usage loop (load → decide → return). Step 1 remains Squad +
        player desk + history.
      </p>
    </main>
  );
}
