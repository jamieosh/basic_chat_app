# Changelog

## 2026-03-15

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
