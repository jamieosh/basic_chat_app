# Phase 4 Done

Completed Phase 4 backlog items move here once they are shipped.

## Completed Items

### P4-01 Session Model And Persistence Groundwork

Priority: P1

Delivered:

- added explicit run-identity persistence by extending `persistence/db.py` with `chat_session_runs`, `chat_turn_requests.run_id`, additive indexes, and bootstrap backfill logic for legacy local databases
- extended `persistence/repository.py` and `persistence/__init__.py` so turn-request lifecycle state now carries linked run identity and keeps run status synchronized through started, completed, failed, and conflicted outcomes
- updated `services/chat_turns.py` observability shaping so run identity metadata is available while preserving the existing route-level send contract
- added regression coverage in `tests/test_chat_repository.py`, `tests/test_chat_turn_service.py`, and `tests/test_main_routes.py` for run-link persistence, duplicate replay behavior, and no-regression HTMX send/restore behavior
- updated `README.md` and `AGENTS.md` so contributor-facing docs describe the additive Phase 4 session/run groundwork and current compatibility posture

Acceptance criteria met:

- existing `/`, `/chat-start`, `/chats/{chat_id}`, and `/send-message-htmx` behavior remained stable, including hidden `chat_session_id` wiring
- database bootstrap now provisions run-identity structures and backfills legacy rows without destructive migration
- each accepted turn request now persists and reuses a stable run identity record across lifecycle transitions
- repository and service layers now expose session/run-aware state needed for later Phase 4 slices while retaining existing callers
- regression coverage now includes migration/backfill, run-link persistence, duplicate replay stability, and route no-regression behavior

What the user sees:
Little or no visible UI change yet. The shipped value is a stronger session/run persistence foundation for later Phase 4 workflow slices.
