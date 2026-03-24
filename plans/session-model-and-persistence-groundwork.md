# Feature: Session Model And Persistence Groundwork

## Slug
session-model-and-persistence-groundwork

## Source
plans/PHASE 4 BACKLOG.md — P4-01 Session Model And Persistence Groundwork

## Scope
Establish explicit session/run groundwork in persistence and service vocabulary without changing the current chat-first HTMX behavior. This increment will keep existing `/chats/{chat_id}` restore and `/send-message-htmx` send behavior stable while introducing additive storage and repository/service seams for:

- explicit session-oriented metadata that is no longer transcript-only by convention
- explicit run identity tied to each send lifecycle record
- backward-compatible migration for existing local SQLite databases

## Non-goals
- No user-facing fork/replay/resume workflow yet.
- No broad UI redesign or route-path rename from `chat` to `session`.
- No artifact/file record model in this increment.
- No background job orchestration or control-plane behavior.
- No provider/runtime wiring changes beyond carrying session/run identity metadata.

## Acceptance Criteria
- [ ] Existing user-visible flow is preserved: `/`, `/chat-start`, `/chats/{chat_id}`, and `/send-message-htmx` continue to behave as today, including hidden `chat_session_id` form wiring.
- [x] Database bootstrap adds the minimum new Phase 4 persistence structures for explicit run identity and keeps old databases readable through additive backfill/migration logic.
- [x] Each started turn request persists a stable run identity record and links lifecycle updates (`processing/completed/failed/conflicted`) to that run without breaking duplicate replay semantics.
- [x] Repository/service layers expose explicit session/run-aware data needed for later Phase 4 slices while retaining compatibility for current callers.
- [ ] Regression tests cover schema migration/backfill, run-link persistence, duplicate replay behavior, and no-regression route send/restore paths.

## Risks / Assumptions
Assumptions:
- Keep `chat_sessions` and current route parameters as the externally visible compatibility anchor in this slice.
- Treat one send lifecycle as one run record for now; richer run intent/mode taxonomy comes in later Phase 4 items.
- Prefer additive schema updates over destructive renames to protect local developer data.

Risks:
- Incomplete backfill could leave legacy rows without run linkage if migration paths are not carefully tested.
- Naming overlap (`chat_*` vs session/run terms) may create temporary dual vocabulary; code comments/docs must make intent explicit.
- Duplicate replay/idempotency is sensitive; incorrect run-link writes could create extra rows or drift lifecycle state.

## Implementation Steps
- [x] Step 1: Add additive persistence schema for explicit run identity (new table/columns/indexes) plus bootstrap backfill guards for pre-Phase-4 databases. — files: `persistence/db.py`, `tests/test_chat_repository.py`
- [x] Step 2: Extend repository domain models and row mappers with session/run-groundwork types and link turn-request lifecycle writes to persisted run identity. — files: `persistence/repository.py`, `persistence/__init__.py`
- [x] Step 3: Update service-layer request lifecycle seams to carry the new run/session-groundwork fields while preserving current route contracts and harness execution flow. — files: `services/chat_turns.py`, `tests/test_chat_turn_service.py`
- [ ] Step 4: Confirm no-regression route behavior for send/replay/restore with the new persistence model in place. — files: `tests/test_main_routes.py`
- [ ] Step 5: Align contributor docs with the additive Phase 4 session/run groundwork and compatibility posture (no UI workflow change yet). — files: `README.md`, `AGENTS.md`

## Tests to Add
- [x] `test_bootstrap_database_backfills_phase4_run_identity_for_legacy_rows` -> covers AC: Database bootstrap adds new structures and keeps old DBs readable.
- [x] `test_chat_repository_start_turn_persists_run_identity_link` -> covers AC: started turn request persists stable run identity link.
- [x] `test_chat_repository_duplicate_turn_replay_does_not_create_extra_runs` -> covers AC: duplicate replay semantics remain intact with run linkage.
- [x] `test_chat_turn_service_preserves_send_contract_with_run_groundwork` -> covers AC: repository/service remain compatible for current callers.
- [ ] `test_send_message_routes_preserve_existing_htmx_chat_session_behavior_after_phase4_schema` -> covers AC: no visible route/HTMX regression.

## Definition of Done
- [ ] All acceptance criteria checked off
- [ ] All new or updated tests pass
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy .` passes
- [ ] `uv run python -m pytest` passes
- [ ] `README.md` updated if user-visible behavior changed
- [ ] E2E or visual checks run when UI behavior changes materially
- [ ] `CHANGELOG.md` updated when the feature ships
- [ ] Matching phase backlog and `plans/done/PHASE X DONE.md` updated when the feature ships
- [ ] `AGENTS.md` updated if architecture or contributor guidance changes
