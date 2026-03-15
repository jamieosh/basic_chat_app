# Phase 2 Backlog

See [`plans/PHASE 2 DESIGN.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%202%20DESIGN.md) for the Phase 2 product, UI, routing, and scope decisions that shape these items.

See [`plans/PARKING LOT.md`](/Users/jamie/Development/basic_chat_app/plans/PARKING%20LOT.md) for known ideas that are intentionally out of scope for this phase.

## Backlog Items

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
