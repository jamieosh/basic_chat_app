# Phase 3 Done

Completed Phase 3 backlog items move here once they are shipped.

## Completed Items

### P3-02 Harness Registry, Control Wiring, And Stable Binding

Priority: P0

Delivered:

- added a startup-wired `HarnessRegistry` plus default-harness configuration so startup and readiness depend on registry-backed harness resolution instead of route-owned provider wiring
- persisted `harness_key` plus optional `harness_version` on `chat_sessions`, with additive SQLite backfill so older local databases remain readable without manual reset
- moved new-chat binding selection and persisted chat-harness resolution into the small `ChatTurnService` control layer
- kept one chat bound to one harness configuration for its lifetime, including duplicate replay and revisit flows
- added regression coverage for binding persistence, legacy-database backfill, service-level harness resolution, persisted follow-up execution, and unknown-binding failure handling
- updated contributor-facing docs so the registry, persisted binding model, and extension seam are described consistently

Acceptance criteria met:

- the app can resolve the harness for a chat without route-level provider branching
- the route layer no longer acts as the de facto owner of harness selection and execution wiring
- new chats are created with a stable harness binding
- the default configuration remains simple for contributors who only want the shipped baseline

What the user sees:
No major visible UI change, but a chat is now anchored to a specific harness configuration behind the scenes and future sends stay attached to that binding.

### P3-01 Chat Agent Harness Vocabulary And Contracts

Priority: P0

Delivered:

- added the app-facing `ChatHarness` contract plus normalized identity, capability, request, result, event, failure, and observability types
- switched the route and startup layer to depend on harness vocabulary and normalized failure codes instead of OpenAI SDK exception handling
- adapted the shipped OpenAI implementation to expose explicit harness identity, normalized `run()` execution, and harness-owned observability metadata
- added regression coverage for the new contract, normalized route failure handling, harness-oriented readiness reporting, and OpenAI harness behavior
- updated contributor-facing docs so new extensions target `ChatHarness` and can distinguish app-layer responsibilities from harness/provider responsibilities

Acceptance criteria met:

- the main app-facing execution contract does not reference OpenAI-specific request or exception types
- the contract is serialization-friendly enough to survive a later service boundary
- contributors can identify one clear interface to implement for a new harness

What the user sees:
No major visible UI change, but the app now has a real architectural seam between the chat application layer and the provider-backed harness implementation that later Phase 3 work can build on.
