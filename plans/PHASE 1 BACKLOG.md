# Phase 1 Backlog

This backlog captures the remaining work needed to complete the "Reliable Single-Chat Baseline" phase.  
Items are intentionally unnumbered so they can be reordered as priorities change.

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

-- 

## Recently Completed

### Strengthen Baseline Request And Failure UX

Reliable single-chat behavior depends on the browser experience as well as the backend path. Phase 1 should make the request cycle predictable under normal use and common failure conditions, so the app feels stable even before broader chat features or streaming exist.

- Duplicate submissions are prevented while a request is already in flight.
- Loading, error, and service-unavailable states are explicit in the chat UI, with the default loading state kept intentionally minimal.
- The single-chat flow behaves predictably when the backend is not ready or returns an error.
- Focused frontend request/failure coverage exists for the most important baseline behaviors.
