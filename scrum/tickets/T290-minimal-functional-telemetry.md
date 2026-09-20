---
id: T290
title: Minimal functional telemetry — install → launch → load → outcome
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T215]
---

# T290 — Minimal functional telemetry

## Why

Owner has no reliable signal on whether the tool actually works for people who download it — currently dependent on unreliable, low-volume forum follow-up (two load-failure reports, zero diagnostics screenshots provided despite being asked). Explicitly not interested in vanity metrics (page views, download counts, comment counts) — those are already visible and don't answer the real question: does the app run, does a load succeed or fail and why, and do people come back. This is the direct instrumentation pillar of the funded token spend behind FMT 1.28.

## Scope

- In: Anonymous, disclosed (visible in Settings / User Preferences) event reporting for: installer run, app launch, load-save attempt, load outcome (success / failure + failure reason if determinable), and repeat-run signal (has this anon id run successfully before)
- In: Failure reason should reuse whatever T215 Diagnostics already determines locally — do not invent a second failure-classification system
- In: Clear, honest user-facing disclosure of what is sent — no silent collection
- Out: Any personally identifying data, save contents, player/club data, IP-based analytics dashboards beyond what's needed to answer the questions above
- Out: A/B testing framework, funnels beyond install → launch → load → outcome, marketing analytics

## Acceptance criteria

- [ ] Owner can see: installs, launches, load attempts, load outcomes with failure reasons, and return-usage rate, without depending on user forum replies
- [ ] Disclosure is visible in-app before or alongside first send
- [ ] One commit `T290: …`

## Notes / pointers

- Depends on T215 landing first — telemetry should report the same accurate signals Diagnostics now surfaces locally, not a second guess at what happened
- Needs a decision on where events land (self-hosted endpoint vs. a lightweight third-party) — flag to HQ before implementation if that needs a new external dependency or cost

## Progress

_(worker fills)_
