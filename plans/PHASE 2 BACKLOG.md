# Phase 2 Backlog

## Goal

Phase 2 should take the app from a stateless single-turn demo to a usable local-first chat workbench with:

- multi-turn conversation continuity within a chat
- multiple chats per user context
- durable chat history across reloads and restarts
- a simple, explicit chat lifecycle that does not require authentication

## Recommended Scope Decisions

- Use local SQLite as the default persistence layer.
  - It matches the Python-first, local-first posture and does not require a separate service.
- Scope chats to an anonymous browser/client identity instead of making all chats globally visible.
  - This preserves the no-auth baseline while avoiding a shared-history-by-default UX.
- Keep the lifecycle simple in Phase 2.
  - Recommended baseline: `active` and `archived`.
- Keep the server-rendered HTMX model.
  - Add transcript and chat-list partials rather than moving state ownership into client-side JavaScript.

## Research Notes From The Current Codebase

- [`main.py`](/Users/jamie/Development/basic_chat_app/main.py) only supports `/send-message-htmx` with a single `message` field and no `chat_id`.
- [`agents/openai_agent.py`](/Users/jamie/Development/basic_chat_app/agents/openai_agent.py) always sends one system message plus one user message, so conversation history is not yet representable.
- [`static/js/chat.js`](/Users/jamie/Development/basic_chat_app/static/js/chat.js) optimistically appends messages in the browser, which works for single-turn UX but is not enough for restoring or switching transcripts.
- [`pyproject.toml`](/Users/jamie/Development/basic_chat_app/pyproject.toml) has no persistence dependency or schema tool today, so storage needs to be introduced intentionally.

## Proposed Backlog Items

### P2-01 Conversation Persistence Foundation

Priority: P0

Why this exists:
Phase 2 cannot deliver continuity without a durable chat/message store.

Deliver:

- introduce a storage model for `chat_sessions` and `chat_messages`
- define ordered transcript reads and simple repository helpers
- add storage bootstrap at startup
- add runtime configuration for the database path

Acceptance criteria:

- chats and messages can be created, listed, and loaded in deterministic tests
- stored chats survive app restarts
- storage failures produce explicit startup or request-level errors

Notes:

- Recommended config: `CHAT_DB_PATH`
- Recommended metadata: `id`, `client_id`, `title`, `created_at`, `updated_at`, `archived_at`

### P2-02 Anonymous Client Identity And Chat Ownership

Priority: P0

Why this exists:
Multiple chats without authentication still need stable ownership and isolation.

Deliver:

- issue an anonymous client ID cookie on first visit
- associate every chat with that client ID
- ensure chat reads and writes are scoped to the current client

Acceptance criteria:

- the same browser can reload and still see its prior chats
- a fresh browser/client receives an empty state
- attempts to access another client scope return a not-found style response

### P2-03 Multi-Turn Turn-Processing Path

Priority: P0

Why this exists:
Phase 2 is not only about multiple chat records. Existing chats must actually retain conversational context.

Deliver:

- extend the agent input path so prior messages can be included when sending a new turn
- load the stored transcript before calling the model
- persist the assistant reply back into the same chat
- define deterministic behavior for failed model calls

Acceptance criteria:

- tests verify later turns include prior context in the OpenAI request
- a failed model call does not create a fake assistant reply
- the route contract remains understandable and localized

Notes:

- Keep this minimal.
- Do not introduce a broad provider/runtime abstraction yet; that belongs to Phase 3.

### P2-04 Transcript Rendering And Chat Routes

Priority: P0

Why this exists:
Once chats are persisted, the server needs a real way to load and render them again.

Deliver:

- add routes for creating a chat, opening a chat, and rendering a transcript partial
- create reusable server-rendered transcript/message partials
- support restoring the currently selected chat on page reload

Acceptance criteria:

- opening an existing chat renders the full stored transcript
- page reload does not drop the current chat context
- empty states are explicit when no chats exist yet

### P2-05 Multi-Chat Shell And Navigation UX

Priority: P1

Why this exists:
Continuity only becomes useful when users can move between chats without friction.

Deliver:

- add a chat list sidebar or mobile drawer
- add a clear "new chat" action
- show the selected chat state in the shell
- keep the current responsive, no-build-step approach

Acceptance criteria:

- a user can create a new chat, switch to an older chat, and continue it
- the selected chat is visually obvious on desktop and mobile
- the UI still works cleanly with HTMX-driven partial updates

Notes:

- Default chat titles can come from a truncated first user message until rename exists.

### P2-06 Chat Metadata And Lifecycle Actions

Priority: P1

Why this exists:
"Manage chat history" needs at least lightweight organization, not just a growing flat list.

Deliver:

- add stable chat titles
- support manual rename or a clearly defined auto-title policy
- add archive/unarchive actions
- add an archived view or filter

Acceptance criteria:

- users can keep the active chat list clean without losing history
- archived chats remain restorable
- lifecycle state is visible and predictable in the UI

Notes:

- Permanent delete can be deferred if archive already makes the lifecycle coherent.

### P2-07 Concurrency, Integrity, And Failure-Mode Hardening

Priority: P1

Why this exists:
Persistence introduces failure cases that do not exist in the current MVP.

Deliver:

- make the user-message and assistant-message write flow transactional where appropriate
- prevent duplicate turn submission per chat
- define behavior for archived, missing, or stale chat targets during a request
- include chat IDs/client IDs in logs where useful

Acceptance criteria:

- duplicate submits do not create duplicated assistant turns
- partial failures leave storage in a deterministic state
- edge cases around missing or archived chats are covered by tests

### P2-08 Test And Documentation Expansion

Priority: P1

Why this exists:
Phase 2 changes the core product behavior and needs durable regression coverage before later phases build on it.

Deliver:

- add repository and storage tests
- expand route tests for create, switch, reload, and archive flows
- add agent tests for history-aware request construction
- add e2e coverage for resuming an existing chat after refresh
- update contributor docs and setup docs for the new behavior/config

Acceptance criteria:

- Phase 2 behavior is documented end-to-end
- regression tests cover the main lifecycle paths
- local setup remains straightforward for contributors

## Suggested Implementation Order

1. P2-01 Conversation Persistence Foundation
2. P2-02 Anonymous Client Identity And Chat Ownership
3. P2-03 Multi-Turn Turn-Processing Path
4. P2-04 Transcript Rendering And Chat Routes
5. P2-05 Multi-Chat Shell And Navigation UX
6. P2-06 Chat Metadata And Lifecycle Actions
7. P2-07 Concurrency, Integrity, And Failure-Mode Hardening
8. P2-08 Test And Documentation Expansion

## Explicitly Out Of Scope For Phase 2

- authentication and user accounts
- streaming responses
- generalized chat runtime/provider abstraction
- tool calling or MCP integration
- fork-from-message or branch management
- file uploads or project/workspace context
- public deployment hardening

## Early Decisions To Resolve

### Storage Approach

Question:
Should Phase 2 use standard-library `sqlite3` or add an ORM/migration tool?

Recommendation:
Start with `sqlite3` to preserve the Phase 1 simplicity unless the schema grows enough to justify extra tooling immediately.

### Ownership Model

Question:
Should chats be browser-cookie scoped or globally visible on a single app instance?

Recommendation:
Browser-cookie scoped is the better default for a no-auth workbench.

### Lifecycle Depth

Question:
Is archive enough for Phase 2, or do we also want delete?

Recommendation:
Make archive/unarchive the baseline lifecycle. Add delete only if Phase 2 still feels incomplete after archive exists.
