# Phase 2 Design

This document captures the Phase 2 product shape that was implemented so contributors can keep shipped behavior consistent during later work.

See [`plans/PHASE 2 BACKLOG.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%202%20BACKLOG.md) for the delivery slices.

See [`plans/PARKING LOT.md`](/Users/jamie/Development/basic_chat_app/plans/PARKING%20LOT.md) for ideas that are known but intentionally deferred.

## Goal

Phase 2 moves the app from a single-turn demo into a usable local-first chat workbench with:

- multiple chats per browser/client
- multi-turn continuity inside each chat
- durable chat history across reloads and restarts
- a familiar, lightweight multi-chat UI

## Design Principles

- Follow familiar chat-app patterns rather than inventing novel UI.
- Keep the frontend server-rendered and HTMX-first.
- Avoid SPA-style client state ownership and JavaScript-framework interaction models.
- Use a modern, clean default UI that is easy for forks to restyle.
- Keep the implementation simple enough that contributors can follow it quickly.
- Preserve the no-auth, local-first posture from Phase 1.

## Resolved Scope Decisions

### Storage

- Use local SQLite.
- Use standard-library `sqlite3`.
- Keep SQL explicit and small rather than introducing an ORM or migration tool in Phase 2.

### Ownership Model

- Chats are browser-cookie scoped.
- Each browser/client sees only its own chats.
- No authentication is added in Phase 2.

### Lifecycle Model

- Chats can be active, deleted, or internally archived.
- Phase 2 includes user-facing delete.
- Phase 2 does not include user-facing archive UI.
- Archived chats may exist in backend state or future hooks, but they are not surfaced in the user interface for this phase.

## Information Architecture

### Main States

- Chat Start Screen
- Active chat view
- Loading/switching state
- Chat not found state
- Service unavailable state

### Chat Start Screen

- This is the empty composer state shown when the user has no visible chats or clicks `New chat`.
- A chat record is not created until the user sends the first message.
- Once the first message is sent, the app creates the chat, persists the first turn, and moves into the normal chat transcript view.

### Active Chat View

- Desktop uses a standard left sidebar plus transcript layout.
- Mobile uses a standard left drawer for the chat list.
- The main content area shows the selected transcript and composer.

## Routing And URL Behavior

- `/`
  - If the current browser/client has no visible chats, render the Chat Start Screen.
  - If the current browser/client has visible chats, redirect to the most recently updated visible chat.
- `/chats/{chat_id}`
  - Render the shell with that chat selected.
- HTMX partial endpoints
  - Used for chat list refreshes, transcript swaps, and related incremental UI updates.

## Chat Creation And Navigation Behavior

### New Chat

- `New chat` returns the user to the Chat Start Screen.
- It does not create a blank chat record by itself.

### First Message

- Sending the first message from the Chat Start Screen creates the chat.
- The resulting view becomes a normal transcript page for that chat.
- The URL should reflect the created chat.

### Switching Chats

- Users can switch chats from the sidebar or mobile drawer.
- Switching chats should show a simple spinner/loading treatment.
- The selected chat should be visually obvious in the list.

### Reload Behavior

- Reloading a chat URL should restore that chat.
- Reloading `/` should either show the Chat Start Screen or redirect into the current client's most recently updated visible chat.

## Chat List Design

- Show title plus a subtle timestamp.
- Use simple server-generated titles in Phase 2, for example `Chat 1`, `Chat 2`.
- Numbering is per browser/client, not global across the app.
- Title generation should be isolated behind a method so future naming behavior can change without route churn.

## Message And Loading Behavior

- Use the existing typing-indicator pattern for message send.
- Use a spinner or similarly lightweight loading treatment for chat switching.
- Keep transitions simple and predictable.
- Do not introduce heavy client-managed state or SPA-style optimistic navigation.

## Delete Behavior

- Delete is user-facing in Phase 2.
- Delete requires confirmation.
- If the active chat is deleted, the app should open the next available visible chat.
- If no visible chats remain, the app should return to the Chat Start Screen.

## Archive Behavior

- Archive is not a user-facing action in Phase 2.
- Archived chats are hidden from the Phase 2 UI.
- The backend can support an archived flag or hook so the behavior can evolve later without reshaping storage.

## Error And Empty States

### No Chats Yet

- Show the Chat Start Screen.
- The UI should make it clear that the user can begin by asking a question.

### Chat Not Found

- Show a clear not-found style message for stale or invalid chat URLs.
- Normal in-app delete flow should not land on this state.
- After in-app delete, route the user to the next available visible chat, or to the Chat Start Screen if none remain.

### Backend Unavailable

- Preserve the current inline degraded-service style from Phase 1 where possible.

## Out Of Scope For Phase 2

- authentication and user accounts
- user-facing archive browsing or archive restore UI
- editable chat titles
- AI-generated default titles
- project or folder containers
- streaming responses
- generalized provider/runtime abstraction
- file uploads or project context

## Implementation Guardrails

- Prefer HTMX partial swaps over full client-managed app state.
- Keep route and template boundaries obvious.
- Keep browser JavaScript focused on UI glue rather than application state ownership.
- Avoid backend changes that assume future project/container features already exist.
- Forward-looking note for Phase 3:
  - if streaming-capable harness execution is introduced later, prefer an event-first execution surface so the existing non-streaming web flow can be a collector over the same core path rather than a separate provider-specific code path.
