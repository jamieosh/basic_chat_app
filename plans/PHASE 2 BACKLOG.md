# Phase 2 Backlog

See [`plans/PHASE 2 DESIGN.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%202%20DESIGN.md) for the Phase 2 product, UI, routing, and scope decisions that shape these items.

See [`plans/PARKING LOT.md`](/Users/jamie/Development/basic_chat_app/plans/PARKING%20LOT.md) for known ideas that are intentionally out of scope for this phase.

## Backlog Items

### P2-07 Concurrency, Integrity, And Failure-Mode Hardening

Priority: P1

Deliver:

- make the user-message and assistant-message write flow transactional where appropriate
- prevent duplicate turn submission per chat
- define behavior for archived, missing, or stale chat targets during a request
- include chat IDs and client IDs in logs where useful

Acceptance criteria:

- duplicate submits do not create duplicated assistant turns
- partial failures leave storage in a deterministic state
- missing, deleted, and archived chat edge cases are covered by tests

What the user will see:
No major new UI, but chat behavior will feel more reliable because duplicate messages, broken states, and inconsistent chat actions should happen less often.

### P2-08 Test And Documentation Expansion

Priority: P1

Deliver:

- add repository and storage tests
- expand route tests for create, switch, reload, delete, and empty-state flows
- add agent tests for history-aware request construction
- add e2e coverage for resuming an existing chat after refresh
- update contributor docs and setup docs for the new behavior and config

Acceptance criteria:

- Phase 2 behavior is documented end-to-end
- regression tests cover the main lifecycle paths
- local setup remains straightforward for contributors

What the user will see:
No change.
