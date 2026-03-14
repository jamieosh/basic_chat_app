# Phase 1 Backlog

This backlog captures the work needed to complete the "Reliable Single-Chat Baseline" phase.  
Items are intentionally unnumbered so they can be reordered as priorities change.

-- 

## Finish Portability And Configuration Baseline

Phase 1 should be portable and predictable for local use before it grows broader capabilities. That means startup should not depend on incidental working-directory assumptions, local setup should be obvious, and baseline runtime configuration should not contradict the project's current no-auth, experimentation-first posture. Some of this work is already in place, but the backlog should still track the remaining cleanup needed to make the baseline coherent.

- Keep path resolution, startup expectations, and local environment setup portable and explicit.
- Make CORS behavior environment-driven and aligned with the current no-auth baseline.
- Remove contradictory default configuration that would confuse local users or small internal forks.
- Keep packaging/runtime metadata and developer setup documentation aligned with actual project requirements.

-- 

## Expand Regression Coverage For Baseline Reliability

A small project still needs strong confidence in its core behavior. This item adds focused, deterministic tests around known fragile paths so refactors and experiments do not regress the baseline chat flow. The emphasis is on high-signal test coverage, not test volume, with particular attention to the startup and configuration behavior that now defines Phase 1 quality.

- Add tests for key error and fallback paths in message processing.
- Add tests for startup/readiness and configuration-related behavior that affects local reliability.
- Add tests for rendering/formatting edge cases that affect chat output.
- Keep tests offline and deterministic with mocked external dependencies.

-- 

## Strengthen Baseline Request And Failure UX

Reliable single-chat behavior depends on the browser experience as well as the backend path. Phase 1 should make the request cycle predictable under normal use and common failure conditions, so the app feels stable even before broader chat features or streaming exist.

- Prevent duplicate submissions while a request is already in flight.
- Make loading, error, and service-unavailable states explicit in the chat UI.
- Ensure the single-chat flow behaves predictably when the backend is not ready or returns an error.
- Add focused coverage for the most important frontend request/failure behaviors.

-- 

## Reduce External Runtime Fragility

Phase 1 can intentionally keep CDN-hosted frontend dependencies if that choice remains explicit and documented. The important part is to avoid accidental fragility by making the external runtime assumptions visible to contributors and fork maintainers.

- Keep CDN-hosted frontend assets as an intentional default, not an incidental implementation detail.
- Document which external assets are required for the default UI to function.
- Pin or review external asset versions so the baseline remains predictable over time.
- Clarify the tradeoff between minimal setup and external dependency risk for forks.

-- 

## Tighten Documentation For Contributors And Forks

Phase 1 completion should be obvious to new contributors and fork maintainers. This item ensures docs consistently describe what exists today, what is intentionally deferred, and what "reliable single-chat baseline" actually means in practice. Clear docs reduce onboarding time and keep implementation choices aligned with vision.

- Keep README, VISION, and PHASES language aligned around current scope.
- Add a concise "Phase 1 complete means..." definition for maintainers.
- Clarify local setup, runtime assumptions, and current security posture for forks.
- Make it explicit that authentication, multi-chat continuity, and broader runtime abstraction are later-phase concerns.
- Clarify where to change prompts, model wiring, and chat UI behavior safely.
