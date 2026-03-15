# Phase 2 Backlog

See [`plans/PHASE 2 DESIGN.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%202%20DESIGN.md) for the Phase 2 product, UI, routing, and scope decisions that shape these items.

See [`plans/PARKING LOT.md`](/Users/jamie/Development/basic_chat_app/plans/PARKING%20LOT.md) for known ideas that are intentionally out of scope for this phase.

## Backlog Items

### P2-07 Concurrency, Integrity, And Failure-Mode Hardening

Priority: P1

Deliver:

- move the per-chat turn write path behind repository-level transactional helpers where appropriate
- add server-side duplicate-submit protection or idempotency per chat instead of relying only on browser-side request locking
- define and enforce behavior when a chat becomes archived, deleted, missing, or stale while a request is in flight
- include chat IDs and client IDs in logs where useful for concurrency and lifecycle debugging

Acceptance criteria:

- duplicate submits against the same chat do not create duplicated user or assistant turns, even if the browser submits twice
- partial failures in the send path leave storage in a deterministic state with an explicit policy for what is persisted
- missing, deleted, archived, and stale-target edge cases are covered by tests
- the route layer no longer coordinates the full multi-step write lifecycle through loosely coupled repository calls

What the user will see:
No major new UI, but chat behavior will feel more reliable because duplicate messages, broken states, and inconsistent chat actions should happen less often.

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
