# Phase 2 Done

Completed Phase 2 backlog items move here once they are shipped.

## Completed Items

### P2-07 Concurrency, Integrity, And Failure-Mode Hardening

Priority: P1

Delivered:

- moved the send lifecycle behind repository-backed transactional helpers plus a small chat-turn service instead of coordinating the full write path directly in the route
- added persisted per-request idempotency keyed by client and request ID so duplicate submits replay their stored outcome instead of creating duplicate turns
- defined the lifecycle contract so invalid targets return `404` at request start, while chats deleted or archived during in-flight finalization return `409` and keep only the accepted user turn
- expanded send-path logging with chat IDs, client IDs, and request IDs for duplicate replay, success, failure, and lifecycle-conflict debugging
- removed the unused `hello.py` scaffold while updating docs and coverage to match the shipped Phase 2 reliability behavior

Acceptance criteria met:

- duplicate submits against the same chat no longer create duplicated user or assistant turns
- partial failures in the send path leave storage in a deterministic state with an explicit persistence policy
- missing, deleted, archived, and stale-target edge cases are covered by tests
- the route layer no longer coordinates the full multi-step write lifecycle through loosely coupled repository calls

What the user sees:
Chat sends feel more reliable because duplicate requests are replayed safely, failure states are deterministic, and stale or deleted chats now resolve with consistent `404` and `409` behavior.

### P2-06 Chat Titles And Delete Lifecycle

Priority: P1

Delivered:

- kept default chat naming deterministic per browser/client with simple titles such as `Chat 1`, `Chat 2`
- left title generation behind a repository method so future naming behavior can change without route churn
- added user-facing delete with confirmation from the active chat header
- routed delete back into the next visible chat, or to the Chat Start Screen when no visible chats remain
- kept archived chats hidden from the Phase 2 UI while adding explicit backend archive-state coverage

Acceptance criteria met:

- new chats receive deterministic default titles
- deleting a chat requires confirmation
- deleting the active chat routes the user to the next available visible chat, or to the Chat Start Screen if none remain
- archived chats do not appear in the Phase 2 UI

What the user sees:
Chats now have simple default names, and deleting a chat cleanly moves them to another visible chat or back to the start screen instead of leaving the shell in a broken state.

### P2-05 Multi-Chat Shell And Navigation UX

Priority: P1

Delivered:

- kept the desktop shell as a standard sidebar plus transcript layout and added a mobile left drawer for the chat list
- added a dedicated Chat Start Screen route plus a `New chat` action that returns users to it without creating a blank chat
- added subtle per-chat timestamps in the list, with today showing time-only and older chats showing the date
- added lightweight loading feedback while switching chats and kept the selected chat visually obvious across desktop and mobile

Acceptance criteria met:

- a user can create a new chat, switch to an older chat, and continue it
- the selected chat is visually obvious on desktop and mobile
- the UI stays aligned with the server-rendered HTMX architecture

What the user sees:
They get a familiar multi-chat shell with a chat list, a clean new-chat path, and lightweight loading feedback while moving between conversations.

### P2-04 Routes, URLs, And Transcript Rendering

Priority: P0

Delivered:

- added chat URLs based on `/chats/{chat_id}` and restored the selected chat from the URL on full page load
- made `/` render the Chat Start Screen for clients with no visible chats and redirect into the latest visible chat otherwise
- added HTMX partial endpoints for transcript and chat-list updates so server-rendered navigation stays in sync with the active chat
- rendered full stored transcripts for existing chats and kept generic not-found behavior for missing or foreign chat URLs

Acceptance criteria met:

- opening an existing chat renders the full stored transcript
- page reload keeps the current chat context
- users with no visible chats land on the Chat Start Screen

What the user sees:
They can reopen an existing chat from its URL, keep context after refresh, and land on a clear start screen when no chats exist yet.

### P2-02 Anonymous Client Identity And Chat Ownership

Priority: P0

Delivered:

- issued an anonymous browser-scoped client ID cookie on first visit and reused it across later requests
- associated persisted chats with the resolved client ID instead of a shared placeholder identity
- enforced client ownership on chat-targeted writes and returned a generic not-found style response for missing or foreign chat targets

Acceptance criteria met:

- the same browser/client keeps the same anonymous ID across requests
- a fresh browser/client starts with an empty chat state
- requests targeting another client scope receive a not-found style response

What the user sees:
Their chats stay associated with their browser instead of being implicitly shared across clients.

### P2-03 Multi-Turn Turn-Processing Path

Priority: P0

Delivered:

- extended the message send path so a first send creates a persisted chat and later sends append to the same chat
- loaded the stored transcript before calling the model and passed prior turns back to OpenAI in order
- persisted the assistant reply back into the same chat on success
- kept failed model calls from creating fake assistant replies while preserving the user turn and active chat session ID

Acceptance criteria met:

- tests verify later turns include prior context in the OpenAI request
- a failed model call does not create a fake assistant reply
- the route contract remains understandable and localized through the existing HTMX submit path

What the user sees:
Follow-up questions on the current page now continue the same chat instead of starting over each time.

### P2-01 Conversation Persistence Foundation

Priority: P0

Delivered:

- introduced a storage model for `chat_sessions` and `chat_messages`
- bootstrapped the SQLite schema at startup using standard-library `sqlite3`
- added runtime configuration for the database path
- added repository helpers for ordered transcript reads and chat list reads

Acceptance criteria met:

- chats and messages can be created, listed, loaded, and deleted in deterministic tests
- stored chats survive app restarts
- storage failures produce explicit startup or request-level errors

What the user sees:
No visible change on its own, but it enables chats to persist instead of disappearing when the app restarts.
