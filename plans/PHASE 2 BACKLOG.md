# Phase 2 Backlog

See [`plans/PHASE 2 DESIGN.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%202%20DESIGN.md) for the Phase 2 product, UI, routing, and scope decisions that shape these items.

See [`plans/PARKING LOT.md`](/Users/jamie/Development/basic_chat_app/plans/PARKING%20LOT.md) for known ideas that are intentionally out of scope for this phase.

## Backlog Items

### P2-01 Conversation Persistence Foundation

Priority: P0

Deliver:

- introduce a storage model for `chat_sessions` and `chat_messages`
- bootstrap the SQLite schema at startup using standard-library `sqlite3`
- add runtime configuration for the database path
- add repository helpers for ordered transcript reads and chat list reads

Acceptance criteria:

- chats and messages can be created, listed, loaded, and deleted in deterministic tests
- stored chats survive app restarts
- storage failures produce explicit startup or request-level errors

What the user will see:
No visible change on its own, but it enables chats to persist instead of disappearing when the app restarts.

### P2-02 Anonymous Client Identity And Chat Ownership

Priority: P0

Deliver:

- issue an anonymous client ID cookie on first visit
- associate every chat with that client ID
- scope chat reads and writes to the current client

Acceptance criteria:

- the same browser can reload and still see its prior chats
- a fresh browser/client receives an empty state
- requests for another client scope return a not-found style response

What the user will see:
Their chats stay associated with their browser, so when they come back they see their own history rather than a shared global chat list.

### P2-03 Multi-Turn Turn-Processing Path

Priority: P0

Deliver:

- extend the agent input path so prior turns can be included when sending a new message
- load the stored transcript before calling the model
- persist the assistant reply back into the same chat
- define deterministic behavior for failed model calls

Acceptance criteria:

- tests verify later turns include prior context in the OpenAI request
- a failed model call does not create a fake assistant reply
- the route contract remains understandable and localized

What the user will see:
Follow-up questions will make sense in context because the assistant will remember earlier messages in the same chat.

### P2-04 Routes, URLs, And Transcript Rendering

Priority: P0

Deliver:

- add chat URLs based on `/chats/{chat_id}`
- add the Phase 2 Chat Start Screen behavior for users with no visible chats
- add HTMX partial endpoints for transcript and chat-list updates
- support restoring the selected chat from the URL

Acceptance criteria:

- opening an existing chat renders the full stored transcript
- page reload keeps the current chat context
- users with no visible chats land on the Chat Start Screen

What the user will see:
They can reopen an existing chat from its URL and see the full earlier transcript instead of starting from a blank screen after refresh.

### P2-05 Multi-Chat Shell And Navigation UX

Priority: P1

Deliver:

- add a standard sidebar layout on desktop
- add a standard left drawer for the chat list on mobile
- add a `New chat` action that returns the user to the Chat Start Screen
- show title plus subtle timestamp in the chat list
- show loading feedback when switching chats

Acceptance criteria:

- a user can create a new chat, switch to an older chat, and continue it
- the selected chat is visually obvious on desktop and mobile
- the UI stays aligned with the server-rendered HTMX architecture

What the user will see:
They will see a familiar multi-chat layout with a chat list, a new-chat action, and simple loading states when moving between conversations.

### P2-06 Chat Titles And Delete Lifecycle

Priority: P1

Deliver:

- generate default per-client chat titles such as `Chat 1`, `Chat 2`
- isolate title generation behind a method that can change later
- add delete behavior with confirmation
- after delete, open the next available visible chat or return to the Chat Start Screen
- support archived flags in backend state without exposing archive UI in Phase 2

Acceptance criteria:

- new chats receive deterministic default titles
- deleting a chat requires confirmation
- deleting the active chat routes the user to the next available visible chat, or to the Chat Start Screen if none remain
- archived chats do not appear in the Phase 2 UI

What the user will see:
Chats will have simple default names, and users will be able to delete chats cleanly without being left in a broken or empty state.

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
