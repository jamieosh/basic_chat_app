# Phase 4 Done

Completed Phase 4 backlog items move here once they are shipped.

## Completed Items

### P4-02 Session Metadata And Inspectability Surface

Priority: P1

Delivered:

- added session inspectability reads in `persistence/repository.py` and `persistence/__init__.py`, including deterministic latest-run lookup for an active session and typed repository return shapes for route rendering
- extended `main.py` context shaping so active chat rendering resolves persisted session binding metadata, latest run metadata, and runtime identity details through the harness registry with graceful fallback when a persisted binding cannot be resolved
- updated `templates/components/chat_view_header.html` and `static/css/chat.css` to ship a compact, responsive active-header metadata surface for session identity, runtime binding, model/provider details, and latest run status
- added route and repository regression coverage in `tests/test_main_routes.py` and `tests/test_chat_repository.py` for metadata rendering, HTMX OOB consistency, latest-run behavior, and no-regression start/not-found shell behavior
- updated `tests/e2e/test_chat_smoke.py` and refreshed `tests/e2e/snapshots/` so visual checks lock the intentional desktop/mobile header and shell updates
- updated `README.md` and `AGENTS.md` so contributor-facing docs describe the shipped inspectability surface and current capability posture

Acceptance criteria met:

- active chat now shows explicit session inspectability metadata, including stable session identity and lifecycle timestamps
- active chat now shows bound runtime identity and binding details derived from persisted session binding, not only default app banner metadata
- latest run metadata now renders when present and degrades cleanly to a no-run state when no run record exists yet
- metadata remains consistent between full-page loads and HTMX partial/OOB updates (`/chats/{chat_id}/transcript`, `/chat-start/transcript`, and send-response header updates)
- start and not-found shells keep existing behavior and accessibility semantics

What the user sees:
Active chats now expose an inspectability strip in the header with session ID/timestamps, runtime binding/model/provider identity, and latest run status so session state is visible without leaving the chat view.

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
