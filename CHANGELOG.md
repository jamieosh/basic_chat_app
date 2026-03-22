# Changelog

## 2026-03-22

### Ship Phase 3 Anthropic Harness Proof Implementation

- Added a shipped Anthropic-backed harness in `agents/anthropic_agent.py` and expanded `agents/harness_registry.py`, `utils/settings.py`, and `utils/diagnostics.py` so new chats can be backend-configured to bind to either `openai` or `anthropic` through `DEFAULT_CHAT_HARNESS_KEY`.
- Added `templates/prompts/anthropic/` plus focused regression coverage in `tests/test_anthropic_agent.py`, `tests/test_harness_registry.py`, `tests/test_settings.py`, `tests/test_diagnostics.py`, `tests/test_chat_turn_service.py`, and `tests/test_main_routes.py` to lock Anthropic request construction, startup validation, readiness metadata, and persisted binding behavior without route-level provider branching.
- Updated `.env.example`, `README.md`, and `AGENTS.md` so the shipped provider-selection path is explicit and contributors can see where to configure OpenAI vs Anthropic for new chats.
- Final verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`278 passed`).

### Ship Phase 3 Test, Docs, And Forking Guidance Alignment

- Added explicit harness-boundary regression coverage in `tests/test_chat_harness_contract.py`, `tests/test_harness_registry.py`, `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, `tests/test_diagnostics.py`, and `tests/test_openai_agent.py` to lock registry resolution, fake-harness startup wiring, non-default readiness metadata, and OpenAI `run()`/`run_events()` parity while keeping alternate harnesses possible.
- Introduced a fake event-harness fixture in `tests/conftest.py` so the app can be booted and exercised through a non-OpenAI default harness without route-level provider coupling.
- Updated `README.md`, `AGENTS.md`, `plans/PHASE 3 BACKLOG.md`, and `plans/PHASE 3 DESIGN.md` so contributor-facing docs and Phase 3 planning docs now describe one registry-backed harness extension path and the same UI-layer, harness-layer, and small control/service-layer split.
- Final verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`238 passed`).

### Ship Phase 3 Control-Layer Refactor, Error Handling, And Harness Observability

- Refactored `services/chat_turns.py` and `main.py` so the small control/service layer now owns normalized started-turn execution, harness-resolution fallback, failure finalization, and per-turn observability while the route stays focused on validation and HTMX rendering.
- Extended `utils/diagnostics.py` and `agents/openai_agent.py` so readiness and runtime logging now expose normalized harness identity details and the default OpenAI adapter emits provider identity consistently in observability tags.
- Expanded regression coverage in `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, `tests/test_diagnostics.py`, and `tests/test_openai_agent.py` to lock success, failure, duplicate replay, harness-unavailable fallback, conflict handling, and readiness metadata behavior through the refactored control-layer path.
- Updated `README.md`, `AGENTS.md`, `plans/PHASE 3 BACKLOG.md`, and `plans/done/PHASE 3 DONE.md` so contributor-facing docs and Phase 3 planning records describe the shipped control-layer and observability responsibilities consistently.
- Verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`223 passed`).

### Ship Phase 3 Tool Hook And Capability Foundation

- Extended `agents/chat_harness.py`, `agents/base_agent.py`, and `agents/__init__.py` so the Phase 3 harness contract now includes normalized tool capability metadata, tool-call/tool-result payload types, and an optional `execute_tool_call()` seam without changing the current non-streaming app flow.
- Kept `agents/openai_agent.py` explicitly non-tool-aware by default while preserving the shipped two-event text/completion behavior for the OpenAI-backed harness adapter.
- Added regression coverage in `tests/test_chat_harness_contract.py`, `tests/test_openai_agent.py`, `tests/test_chat_turn_service.py`, and `tests/test_main_routes.py` to prove tool events remain serialization-friendly, collector-safe, and invisible to the current persisted transcript and HTMX response flow.
- Updated `README.md`, `AGENTS.md`, `plans/PHASE 3 BACKLOG.md`, and `plans/done/PHASE 3 DONE.md` so contributor guidance and Phase 3 planning docs describe the shipped tool-hook seam consistently.
- Verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`214 passed`).

### Ship Phase 3 Streaming-Capable Harness Execution Surface

- Refactored `agents/chat_harness.py`, `agents/openai_agent.py`, and `services/chat_turns.py` so `run_events()` is now the canonical harness execution surface, while `run()` stays as the shared non-streaming collector over normalized event streams.
- Updated `main.py`, `tests/test_chat_harness_contract.py`, `tests/test_openai_agent.py`, `tests/test_chat_turn_service.py`, and `tests/test_main_routes.py` so the current HTMX send flow deterministically collects multi-event output into one persisted assistant reply and rejects partial assistant persistence when a stream fails.
- Refreshed `README.md` and `AGENTS.md` so contributor guidance now describes the Phase 3 harness contract as event-first, with provider-backed implementations expected to expose `run_events()` directly.
- Updated `plans/PHASE 3 BACKLOG.md` and `plans/done/PHASE 3 DONE.md` to record `P3-05` as shipped and remove it from the active backlog.
- Verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`208 passed`).

### Ship Phase 3 Context Builders And Harness-Owned Memory Assembly

- Added harness-owned context assembly types and pluggable builders in `agents/chat_harness.py` and `agents/context_builders.py`, so model-facing context can evolve behind the harness boundary while persisted chat messages remain the canonical raw transcript.
- Refactored `agents/openai_agent.py`, `utils/prompt_manager.py`, `services/chat_turns.py`, `persistence/repository.py`, and `main.py` so the shipped OpenAI path now builds prompt and transcript context through a default builder and the route no longer shapes provider-facing history itself.
- Expanded regression coverage in `tests/test_context_builders.py`, `tests/test_openai_agent.py`, `tests/test_chat_harness_contract.py`, `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, and `tests/test_prompt_manager.py` to lock default prompt parity and prove alternate memory policies can fit behind the same request contract.
- Updated `README.md`, `AGENTS.md`, `plans/PHASE 3 BACKLOG.md`, and `plans/done/PHASE 3 DONE.md` to reflect the shipped context-builder seam and harness-owned memory assembly model.
- Verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`200 passed`).

### Ship Phase 3 OpenAI Harness Adapter Migration

- Refactored `agents/openai_agent.py` so the shipped OpenAI runtime behaves as a true harness adapter behind `ChatHarness.run()`, while `agents/chat_harness.py` keeps `BaseAgent` and `process_message()` clearly in compatibility-shim territory.
- Tightened `services/chat_turns.py` and the Phase 3 route coverage in `tests/test_main_routes.py` so app-layer failure presentation and send-flow tests now depend on normalized harness failures instead of provider-shaped exceptions or legacy monkeypatch paths.
- Expanded regression coverage in `tests/test_openai_agent.py` and `tests/test_chat_turn_service.py` to lock default OpenAI parity, normalized error translation, and compatibility-only failure alias handling.
- Updated `README.md` and `AGENTS.md` so contributor guidance describes the shipped OpenAI path as a registry-resolved harness adapter with provider-specific execution and failure translation kept behind the harness boundary.
- Verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`189 passed`).

### Ship Phase 3 Harness Registry, Control Wiring, And Stable Binding

- Added a startup-wired `HarnessRegistry` in `agents/harness_registry.py` and updated `main.py` plus `utils/settings.py` so the shipped app resolves its default harness through registry-backed configuration instead of route-owned provider wiring.
- Extended `persistence/db.py` and `persistence/repository.py` so `chat_sessions` now persist `harness_key` plus optional `harness_version`, with additive SQLite backfill for older local databases that predate the binding columns.
- Refactored `services/chat_turns.py` and the `/send-message-htmx` flow in `main.py` so new chats stamp a stable harness binding and later sends resolve execution from the persisted chat binding instead of assuming one global harness instance.
- Added regression coverage in `tests/test_chat_repository.py`, `tests/test_chat_turn_service.py`, and `tests/test_main_routes.py` for binding round-trips, legacy-database backfill, persisted follow-up resolution, and unknown-binding failure handling.
- Updated `README.md`, `AGENTS.md`, `plans/PHASE 3 BACKLOG.md`, and `plans/done/PHASE 3 DONE.md` to reflect the shipped Phase 3 harness-registry seam and stable chat binding model.
- Verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`187 passed`).

## 2026-03-15

### Ship Phase 3 Chat Harness Vocabulary And Contracts

- Added a normalized `ChatHarness` contract with serialization-friendly request, result, event, failure, identity, capability, and observability types in `agents/chat_harness.py`, while keeping `BaseAgent` only as a compatibility shim.
- Refactored the FastAPI startup, readiness, and send-message flow in `main.py`, `utils/diagnostics.py`, and `services/chat_turns.py` so the app layer now talks to harness-level contracts and normalized failures instead of catching OpenAI SDK exceptions directly.
- Adapted the shipped OpenAI path in `agents/openai_agent.py` to expose explicit harness identity, normalized `run()` behavior, and harness-owned observability metadata without changing the current non-streaming chat behavior.
- Updated contributor-facing guidance in `README.md` and `plans/PHASE 3 DESIGN.md`, moved `P3-01` out of `plans/PHASE 3 BACKLOG.md`, and recorded the shipped slice in `plans/done/PHASE 3 DONE.md`.
- Verification passed with `uv run ruff check .`, `uv run mypy .`, and `uv run python -m pytest` (`178 passed`).

### Ship Phase 2 Test And Documentation Expansion

- Added repository, service, and route regression coverage for replayed `failed` and `conflicted` requests, duplicate `processing` requests, archived target rejection, and archived mid-flight conflict handling.
- Expanded the Playwright test harness with a test-only live-server fixture that exposes the temporary SQLite database path for deterministic persisted-chat seeding.
- Added live-app browser coverage for restoring an existing chat after a full refresh or direct `/chats/{chat_id}` revisit, and verified follow-up sends stay attached to the restored chat.
- Updated contributor-facing docs to reflect the shipped Phase 2 multi-chat baseline and documented the visual snapshot workflow more explicitly.
- Moved `P2-08 Test And Documentation Expansion` out of the active Phase 2 backlog and into the Phase 2 done record.

### Ship Phase 2 Concurrency, Integrity, And Failure-Mode Hardening

- Reworked the `/send-message-htmx` lifecycle around transactional repository helpers and a dedicated chat-turn service so the route no longer coordinates raw multi-step write sequencing.
- Added persisted request-ID idempotency per browser/client so duplicate submits replay the stored outcome instead of creating duplicate user or assistant turns.
- Defined and documented the send reliability contract: invalid targets now fail as `404` at request start, while chats deleted or archived during in-flight finalization return `409` and keep only the accepted user turn.
- Expanded route, repository/service, and Playwright coverage for duplicate replay, lifecycle conflicts, request-ID rotation, and deterministic partial-failure behavior.
- Removed the unused `hello.py` scaffold file.

### Ship Phase 2 Chat Titles And Delete Lifecycle

- Added deterministic per-client default chat titles and kept title generation isolated behind the repository layer for later evolution.
- Added confirmed chat deletion from the active transcript header and routed delete flows into the next visible chat or back to the Chat Start Screen when no visible chats remain.
- Kept archived chats hidden from the visible Phase 2 shell while adding explicit repository coverage for archived-state behavior.
- Tightened the active-chat header for mobile with compact icon-only drawer, new-chat, and delete controls so chat metadata fits without wasting height.
- Added route, repository, Playwright behavior, and visual-regression coverage for delete lifecycle behavior plus high-risk desktop/mobile shell layouts.

### Ship Phase 2 Multi-Chat Shell And Navigation UX

- Added a dedicated Chat Start Screen route and HTMX partial so `New chat` returns to a real start state without breaking `/` redirect behavior for existing chats.
- Expanded the server-rendered shell into a more standard multi-chat workbench with a persistent desktop sidebar, mobile chat-list drawer, and OOB updates that keep header, list, and active chat state synchronized.
- Added lightweight chat-switch loading feedback, stronger active-chat state treatment, and cleaner start-screen presentation while preserving the existing HTMX-first interaction model.
- Refined chat-list timestamp rendering so chats updated today show time-only while older chats show a compact date.
- Expanded route and Playwright coverage for the new start-screen route, `New chat` navigation, mobile drawer interaction, and chat-switch UX.

### Ship Phase 2 Routes, URLs, And Transcript Rendering

- Added route-backed chat restoration with `/chats/{chat_id}` and redirected `/` into the latest visible chat when the current client already has saved conversations.
- Added a Phase 2 Chat Start Screen for clients with no visible chats and kept generic not-found behavior for missing or foreign chat URLs.
- Split the chat shell into reusable server-rendered partials for the chat list, transcript header, and transcript body, with HTMX endpoints for incremental transcript and chat-list refreshes.
- Updated the send-message flow to push the active chat URL after first-message creation and keep shell state synchronized after success and failure responses.
- Tightened the Phase 2 shell presentation with compact chat-list rows, lighter header copy, and static-asset cache busting so refreshed UI changes render reliably.
- Expanded route and Playwright coverage for redirect behavior, transcript reloads, partial rendering, and start-screen flows.

### Ship Phase 2 Anonymous Client Ownership

- Added anonymous browser-scoped client ID issuance with a stable `HttpOnly` cookie and reused it across requests.
- Removed app-level dependence on the old placeholder client identity and aligned tests with explicit client ownership.
- Documented the ownership contract in the Phase 2 planning docs so later chat-scoped routes keep enforcing generic not-found behavior.
- Added regression coverage for cookie issuance, cookie reuse, and client-scoped chat isolation.

### Ship Phase 2 Multi-Turn Turn Processing

- Extended the send-message flow to create a persisted chat on first send and append later turns to the same chat through a hidden `chat_session_id`.
- Added history-aware agent input so stored prior `user` and `assistant` turns are sent back to OpenAI in order before the latest user message.
- Persisted the user turn before the model call, persisted the assistant turn only on success, and kept the active chat session ID available even after model failures.
- Added per-client default chat title generation and HTTP-level not-found handling for missing or foreign chat targets on the write path.
- Expanded route, agent, repository, and Playwright coverage for multi-turn continuity, failure behavior, and same-page chat reuse.

### Ship Phase 2 Persistence Foundation

- Added a SQLite-backed persistence package with explicit schema bootstrap for `chat_sessions` and `chat_messages`.
- Introduced repository helpers for deterministic chat creation, transcript reads, visible-chat listing, and soft delete behavior.
- Added runtime configuration for `CHAT_DATABASE_PATH`, defaulting to `data/chat.db`, and ignored local database files under `data/`.
- Wired storage initialization into FastAPI startup and readiness handling so bootstrap failures surface explicitly.
- Added regression coverage for repository behavior, storage-aware startup/readiness states, and database-path settings validation.
- Updated setup docs and planning docs to reflect that `P2-01 Conversation Persistence Foundation` is complete.

## 2026-03-14

### Complete Phase 1 Documentation Alignment

- Added a clear `Phase 1 Complete Means` definition and explicit default security posture to the README.
- Documented the primary safe customization points for prompts, runtime wiring, and chat UI behavior.
- Updated the Phase 1 description in `plans/PHASES.md` to mark it complete and describe the shipped baseline accurately.
- Tightened `plans/VISION.md` language so authentication, streaming, persisted multi-chat continuity, runtime abstraction, and deployment hardening remain clearly deferred beyond Phase 1.
- Reduced `plans/PHASE 1 BACKLOG.md` to an explicit no-remaining-items marker.

### Reduce External Runtime Fragility

- Kept CDN-hosted HTMX and Tailwind as the intentional Phase 1 default instead of introducing a frontend build step.
- Added explicit template comments that identify the external browser assets and document the HTMX pin plus the reviewed Tailwind CDN exception.
- Documented the default external frontend runtime assumptions, tradeoffs, and fork guidance in the README.
- Added regression coverage that locks the home page to the reviewed HTMX and Tailwind asset references.

### Strengthen Baseline Request And Failure UX

- Prevented duplicate chat submissions while an HTMX request is already in flight.
- Simplified the normal loading state to the existing typing dots while keeping footer status messaging for validation and failure conditions.
- Made unavailable-agent and startup-incomplete chat requests render consistent inline HTML error states instead of falling back to raw framework errors.
- Added focused route and Playwright coverage for duplicate-submit prevention, server-side failure rendering, degraded home-page state, and transport-error fallback behavior.

### Expand Regression Coverage For Baseline Reliability

- Added focused regression tests for route helper behavior, partial readiness states, and remaining OpenAI error branches.
- Added settings and diagnostics coverage for invalid values, fallback defaults, failure summaries, and prompt-specific startup paths.
- Added agent-level regression tests for context-prefix behavior, prompt lookup failures, and GPT-5 temperature-parameter compatibility.
- Added formatter edge-case coverage for empty input, empty fenced blocks, adjacent code fences, and invalid input types.

### Finish Portability And Configuration Baseline

- Added a central runtime settings layer for OpenAI and CORS configuration.
- Made `.env` loading explicitly project-root-based so startup does not depend on the current working directory.
- Switched CORS behavior to environment-driven defaults aligned with the current no-auth baseline.
- Allowed model name, prompt name, timeout, and temperature to be configured without code changes.
- Adjusted GPT-5 request construction to omit unsupported `temperature` parameters while preserving custom temperature support for older model families.
- Updated setup documentation and example environment configuration to match the supported runtime surface.
- Added regression coverage for settings parsing, CORS wiring, configured prompt lookup, and env-driven agent startup.

### Improve Startup And Runtime Diagnostics

- Added explicit startup diagnostics for required configuration and app asset checks.
- Split liveness and readiness behavior with a dedicated readiness endpoint that reports failed checks.
- Refined startup, request, and OpenAI-path logging to be more actionable and lower-noise for local debugging.
- Added deterministic regression tests for startup failures, readiness states, and logging config parsing.

### Stabilize The Single-Chat Request/Response Path

- Hardened OpenAI response handling for missing, blank, and malformed model content.
- Refactored chat response formatting to safely render mixed plain text and fenced code blocks.
- Standardized HTMX bot/error message HTML for the single-chat request/response path.
- Returned deterministic 400 responses for missing or blank user messages.
- Stopped exposing raw unexpected exception text in user-facing error messages.
- Added regression tests for route errors, formatter edge cases, and model-response fallback paths.

### Keep Default Behavior Deterministic And Neutral

- Removed hardcoded domain-specific default context from the baseline OpenAI request path.
- Renamed the default assistant identity to the neutral, repo-branded `AI Chat`.
- Kept the user-context prompt seam in place while making it empty by default.
- Updated the default OpenAI temperature baseline to align with the current GPT-5 default-model behavior.
- Added regression tests that lock the default prompt payload to raw user input unless context is explicitly configured.

### Polish Baseline Chat Input Layout

- Synced the `Send` button height with the textarea's rendered single-line height so the chat composer stays visually aligned before the input expands.
