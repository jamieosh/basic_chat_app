# Phase 4 Design

This document captures the intended Phase 4 product and architecture shape so contributors can evolve the current chat workbench into a richer session-oriented workbench without losing the simple default send flow.

This document should be read alongside [`plans/TERMINOLOGY.md`](/Users/jamie/Development/basic_chat_app/plans/TERMINOLOGY.md), which defines terms such as `session`, `run`, `transcript`, `agent`, `runtime`, and `harness`.

See [`plans/PHASE 4 BACKLOG.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%204%20BACKLOG.md) for the proposed delivery slices.

See [`plans/PARKING LOT.md`](/Users/jamie/Development/basic_chat_app/plans/PARKING%20LOT.md) for known ideas that are intentionally deferred.

## Goal

Phase 4 moves the project from a multi-chat app with a real harness boundary into a workbench whose durable objects are a `session` and its `runs`, rather than only a transcript thread.

The current app already has several important ingredients:

- stable per-chat harness binding
- a small control/service seam
- normalized execution requests, events, failures, and observability
- persisted chat, message, and turn-request lifecycle records

What it still lacks is a richer session model above that groundwork.

Phase 4 should make all of the following easier without destabilizing the existing HTMX-first chat experience:

- treating a session as more than a list of user and assistant messages
- treating a run as more than the hidden mechanics of the latest send
- exposing inspectable session and runtime metadata in the product
- exposing enough run metadata that replay, compare, and resume behaviors become deliberate rather than improvised
- supporting compare, fork, replay, and resume-style workflows cleanly
- separating transcript history from other session-adjacent records such as run metadata or artifacts
- giving sessions a lightweight profile or context-policy shape beyond just a title
- giving future workbench surfaces a clearer durable object than the current chat thread

## What This Phase Means For Users

Phase 4 should be the first phase where the product starts to feel more like a workbench and less like only a saved-chat UI.

For users, the intended promise is:

- existing chat flows should stay simple and predictable
- sessions should be easier to inspect, branch, compare, and revisit
- runs should become a more understandable concept when users retry, replay, compare, or resume work
- runtime identity and session state should become more visible instead of staying mostly backend-only
- session scope or profile should become more visible where it materially helps the user understand what the session is for
- work that belongs to a session but is not plain transcript text should have a cleaner home over time

Users still do not need a large orchestration UI in this phase. The default experience should remain calm and local-first.

## What This Phase Means For Developers And Forks

Phase 4 is where the repository should stop treating `chat_sessions` plus transcript history as the full durable system model.

For developers and fork maintainers, the intended outcome is:

- a session-oriented domain model becomes explicit in planning, persistence, service code, and UI language where appropriate
- a run-oriented execution model becomes more explicit instead of staying mostly hidden inside turn-request lifecycle details
- the current chat thread remains a valuable record, but no longer has to carry every future workbench concern
- contributors can add inspectability, lineage, replay, and artifact behavior without rebuilding the harness boundary again
- the route layer continues to act as a client of a small control/service seam rather than becoming the owner of session orchestration
- the app stays open to more than one runtime shape without forcing external-runtime integration into this phase
- future personal-agent and small-team phases inherit a clearer session foundation instead of extending transcript-only assumptions

## Design Principles

- Preserve the current server-rendered, HTMX-first default UX.
- Keep the normal send flow easy to trace from route to service to harness to persistence.
- Treat session identity as richer than transcript history, but introduce that richness additively.
- Treat run identity as richer than "one send action," but introduce that richness additively.
- Preserve stable harness binding as a session property rather than reintroducing route-owned runtime selection.
- Keep `session`, `run`, and `transcript` distinct in planning and implementation, even when the UI still looks like a simple chat.
- Separate transcript messages from run metadata, lineage metadata, and future artifacts.
- Prefer additive persistence changes and backward-compatible migrations over destructive restructuring.
- Keep inspectability explicit: session state, lineage, and runtime metadata should be visible rather than implied.
- Keep the default app usable without background workers, extra services, or a large control plane.
- Let future compare, replay, and resume flows build on normalized harness execution rather than bypassing it.
- Leave room for external or federated runtime shapes later without making them a Phase 4 dependency.

## Current State And Gaps

The current shipped app already has the minimum technical foundation for a session-oriented phase:

- `chat_sessions` persist stable harness binding and basic lifecycle timestamps
- `chat_messages` remain the canonical raw transcript
- `chat_turn_requests` provide request-level lifecycle state for the current send flow
- `ChatTurnService` owns normalized request execution, replay coordination, and failure shaping
- the harness contract can already emit normalized events and observability metadata

The main gap is that these pieces still present as a chat-thread application more than a session workbench.

Visible and architectural gaps include:

- no explicit session concept beyond the current chat record
- no explicit run concept beyond the current turn-request mechanics
- no session lineage such as forked-from or replay-derived relationships
- no inspectable run history beyond the current turn-request implementation details
- no session-facing place for runtime metadata, scope metadata, profile metadata, or future approvals
- no artifact or output model separate from the transcript
- no user-facing compare, fork, replay, or resume workflow
- no lightweight session profile or work-scope concept beyond the chat title
- no explicit room in the model for future non-native runtime shapes beyond the current harness binding details

Phase 4 should address those gaps without pretending the app already needs a full control plane.

## Scope Decisions

### Session Model First, Not A Whole New Platform

- Phase 4 should make the session concept explicit.
- Phase 4 should also make the run concept explicit enough to support inspectability and deliberate revisit workflows.
- That does not require a separate service, a large orchestration layer, or a fully detached runtime process.
- The current `chat_sessions` record may remain the persistence anchor at first, as long as the product and code stop treating transcript history as the whole story.

### Transcript Remains Canonical, But Not Exclusive

- User and assistant messages should remain the canonical transcript record.
- The transcript should remain the visible conversation history, not the only meaningful record in a session.
- Session metadata, lineage, run summaries, and artifacts should not be forced back into transcript messages just because chat is the current UI.
- Phase 4 should separate those concerns in persistence and service design where it provides real leverage.

### Inspectability Before Heavy Automation

- Users should be able to inspect session and runtime state before the project takes on a large background-run or approval workflow.
- Phase 4 should favor visible metadata, lineage, and run records over hidden smart behavior.
- Resume and replay can begin as deliberate user actions rather than autonomous orchestration.

### Compare, Fork, Replay, And Resume Are Session Behaviors

- Forking should create a distinct session with visible lineage.
- Replay should be able to create or extend work without mutating past transcript history invisibly.
- Resume should mean continuing a known session or run state, not guessing based only on transcript text.
- Compare workflows may begin with simple branch lineage, run metadata, and runtime metadata before a large side-by-side UI.
- Deliberate runtime comparison is in scope when it fits branch, replay, or compare workflows; ad hoc per-message runtime switching is not.

### Session Profile And Scope Context Should Stay Lightweight

- Phase 4 may introduce lightweight session profile, scope, notes, or project linkage if it helps the workbench model.
- That profile may later become a natural home for context-policy ideas such as shared standards or reusable session guidance, but Phase 4 should keep it small and inspectable.
- It should not become a full file-manager or container system in this phase.
- Rich attachments, broad artifact families, or full project workspaces can remain future work unless a narrow slice clearly earns its place here.

### Open To More Than One Runtime Shape

- Phase 4 should preserve the assumption that a session binds to a runtime, but not assume that every future runtime is native to this repository.
- This phase does not need to implement external or federated runtime integration.
- It should avoid persistence or service assumptions that would make such runtimes awkward later.

## Expected Architecture / Product Shape

The intended Phase 4 shape is:

- the web UI still presents a chat-first experience
- but the persisted and service-facing model is explicitly session-and-run oriented
- transcript messages remain one record within a session
- run metadata becomes more inspectable and more intentionally modeled
- session lineage and non-transcript records can exist without leaking provider logic into routes
- session profile and runtime metadata become visible enough to explain what a session is and how it runs

The likely responsibility split becomes:

- Interface layer:
  - route-backed session views, transcript rendering, and session actions such as fork, replay, or compare entry points
- Small control/service layer:
  - session lifecycle, lineage, replay or resume coordination, run-facing metadata, session-profile handling, and UI-facing failure presentation
- Harness layer:
  - execution behavior, context assembly, event production, observability, and future tool orchestration
- Persistence layer:
  - session identity, transcript history, run metadata, lineage records, session profile metadata, and small artifact or output records

Phase 4 should leave the repository in a state where later phases can add approvals, interrupts, background execution, and multiple concurrent agents on top of a real session model rather than on top of transcript-only assumptions.

## Delivery Guardrails

- Do not break the current `/send-message-htmx` append contract while introducing session concepts.
- Do not reintroduce provider-specific logic into routes, templates, or persistence helpers.
- Keep the default OpenAI/Anthropic binding model intact unless a phase slice explicitly extends session binding behavior.
- Do not force external-runtime support into Phase 4 just to prove future flexibility.
- Preserve direct-route revisit behavior and existing chat URL usability unless a migration path is explicit and tested.
- Favor additive schema changes with readable backfills for existing local databases.
- Keep non-streaming HTMX rendering supported even if richer run metadata is introduced.
- Add focused tests around session lifecycle, run lifecycle, lineage, replay behavior, compare behavior, and route restore paths as they evolve.
- Keep UI changes intentional and lightweight rather than turning Phase 4 into a broad redesign.

## Out Of Scope

- a full multi-agent control plane
- team collaboration or shared supervision workflows
- background workers as a baseline requirement
- broad file attachment or container management
- general search, archive browsing, or deleted-chat recovery unless a slice is explicitly promoted from the parking lot
- arbitrary per-message runtime switching as a normal workflow
- deep integration with external runtime systems
- a full streaming UI rollout
- replacing the HTMX-first server-rendered posture

## Open Questions To Keep Visible

- whether the internal persistence model should keep `chat_sessions` as the primary table name in Phase 4 while the app and docs adopt more session-oriented language
- how much of turn or run metadata should graduate from `chat_turn_requests` into a more explicit session-run record
- what the smallest useful run-intent or run-mode vocabulary is for conversational, replay, compare, or task-style runs
- what the minimal useful lineage model is for fork and replay workflows
- whether replay should always create a new session branch or may sometimes continue the same session deliberately
- how much runtime-compare behavior belongs in Phase 4 versus a later control-plane phase
- what the smallest artifact or output model is that creates real user value without becoming a generic file system
- how much session profile or context-policy metadata belongs in Phase 4 versus later workbench phases
