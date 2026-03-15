# Phase 2 Backlog

See [`plans/PHASE 2 DESIGN.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%202%20DESIGN.md) for the Phase 2 product, UI, routing, and scope decisions that shape these items.

See [`plans/PARKING LOT.md`](/Users/jamie/Development/basic_chat_app/plans/PARKING%20LOT.md) for known ideas that are intentionally out of scope for this phase.

## Backlog Items

### P2-08 Test And Documentation Expansion

Priority: P1

Deliver:

- add the remaining Phase 2 repository and route regression coverage around P2-07 failure and concurrency behavior
- add e2e coverage for restoring an existing chat after a true browser refresh or direct URL revisit
- document the visual regression workflow and any remaining Phase 2 contributor expectations
- align the planning/docs set so completed Phase 2 work is not still described as backlog

Acceptance criteria:

- Phase 2 behavior is documented end-to-end without obvious planning drift between design, backlog, done, and README
- regression tests cover the main shipped lifecycle paths plus the remaining P2-07 hardening paths
- browser-level refresh/resume behavior is covered by e2e tests
- local setup remains straightforward for contributors

What the user will see:
No change.
