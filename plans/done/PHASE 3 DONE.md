# Phase 3 Done

Completed Phase 3 backlog items move here once they are shipped.

## Completed Items

### P3-08 Test, Docs, And Forking Guidance Alignment

Priority: P1

Delivered:

- added explicit harness-boundary regression coverage in `tests/test_chat_harness_contract.py`, `tests/test_harness_registry.py`, `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, `tests/test_diagnostics.py`, and `tests/test_openai_agent.py` so registry resolution, fake-harness startup wiring, non-default readiness metadata, and OpenAI `run()`/`run_events()` parity are now locked behind the same normalized harness contract
- added a fake event-harness fixture in `tests/conftest.py` so startup wiring and the normal HTMX send flow can be exercised through a non-OpenAI default harness without route-level provider coupling
- updated `README.md` and `AGENTS.md` so contributors can follow one registry-backed path for adding a new harness implementation while treating `agents/openai_agent.py` as the shipped default adapter rather than the mandatory template for every future harness
- updated `plans/PHASE 3 BACKLOG.md`, `plans/PHASE 3 DESIGN.md`, and `plans/PHASES.md` so the active planning docs now describe the same UI-layer, harness-layer, and small control/service-layer split as the contributor-facing docs

Acceptance criteria met:

- contributors can follow one obvious path to add a new provider-backed harness
- Phase 3 terminology is consistent across code and docs
- `README.md` and `AGENTS.md` describe the same extension model as the Phase 3 planning docs
- the updated docs describe the UI layer, harness layer, and small control/service layer consistently
- tests lock the default harness behavior while leaving space for alternate implementations

What the user sees:
No direct product change, but the repository is now easier to understand, extend, and fork safely.

### P3-07 Control-Layer Refactor, Error-Handling, And Harness Observability

Priority: P1

Delivered:

- refactored `services/chat_turns.py` so the small control/service layer now owns normalized started-turn execution, harness-resolution fallback, failure finalization, response-harness selection, and per-turn observability shaping
- updated `main.py` so `/send-message-htmx` consumes normalized service outcomes instead of catching harness execution and resolution failures inline, while the route still owns validation and HTMX rendering
- extended `utils/diagnostics.py` and `agents/openai_agent.py` so readiness and runtime logs can surface harness key, optional version, provider identity, model identity, and normalized failure categories through shared observability fields
- expanded regression coverage in `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, `tests/test_diagnostics.py`, and `tests/test_openai_agent.py` to lock success, failure, duplicate replay, harness-unavailable fallback, conflict handling, and readiness metadata through the refactored control-layer path
- updated contributor-facing docs so `README.md` and `AGENTS.md` describe the shipped control/service layer and observability responsibilities consistently

Acceptance criteria met:

- route handlers do not branch on provider SDK exception classes or provider-specific error types
- the control/service layer owns normalized run lifecycle coordination without becoming a large orchestration system
- logs and diagnostics can identify the harness key, optional version, provider identity, and normalized failure category through shared observability data
- request lifecycle behavior remains covered for success, failure, duplicate replay, and conflict cases
- the app layer remains responsible for persistence outcomes and user-facing rendering

What the user sees:
Failure behavior remains predictable, while the runtime behind it is less coupled to one provider-specific execution path.

### P3-06 Tool Hook And Capability Foundation

Priority: P2

Delivered:

- extended `agents/chat_harness.py`, `agents/base_agent.py`, and `agents/__init__.py` so the normalized harness vocabulary now includes explicit tool capability metadata, `tool_call` and `tool_result` payload types, and backward-compatible `supports_tools` behavior
- added an optional `execute_tool_call()` seam in `agents/chat_harness.py` so future harness-owned orchestration can plug into the contract without introducing a built-in tool loop in this slice
- kept `agents/openai_agent.py` explicitly non-tool-aware by default while preserving the shipped two-event text/completion behavior and simple capability profile for harnesses that do not support tools
- expanded regression coverage in `tests/test_chat_harness_contract.py`, `tests/test_openai_agent.py`, `tests/test_chat_turn_service.py`, and `tests/test_main_routes.py` to prove tool events stay serialization-friendly, collector-safe, and invisible to the current persisted transcript and HTMX response flow
- updated contributor-facing docs so `README.md` and `AGENTS.md` describe the shipped tool-hook seam, normalized tool events, and current in-memory-only scope consistently

Acceptance criteria met:

- the harness contract can represent tool activity without app-layer redesign
- harnesses that do not support tools can remain simple
- the default shipped app does not need built-in tools to satisfy the Phase 3 design

What the user sees:
Usually no visible UI change yet, but the harness contract is now ready for future tool experiments without another app-layer redesign.

### P3-05 Streaming-Capable Harness Execution Surface

Priority: P1

Delivered:

- refactored `agents/chat_harness.py` so `run_events()` is the canonical execution surface, `run()` is a shared collector over normalized events, and event/result invariants enforce ordered output, terminal completion, and normalized failure handling
- updated `agents/openai_agent.py` so the shipped OpenAI adapter emits one event-driven execution path instead of keeping separate provider logic for `run()` and `run_events()`
- added a small collection seam in `services/chat_turns.py` and wired `main.py` through it so the current HTMX send flow still persists and renders one deterministic final assistant reply without introducing browser streaming yet
- expanded regression coverage in `tests/test_chat_harness_contract.py`, `tests/test_openai_agent.py`, `tests/test_chat_turn_service.py`, and `tests/test_main_routes.py` to lock multi-event collection, failure propagation after partial output, and default OpenAI parity through the canonical event surface
- updated contributor-facing docs so `README.md` and `AGENTS.md` describe the shipped harness contract as event-first and keep extension guidance aligned with the Phase 3 execution model

Acceptance criteria met:

- provider implementations do not maintain separate execution logic for `run()` and `run_events()`
- a harness can expose streaming-capable events without redesigning the app-facing contract
- the current HTMX send flow can still collect a final assistant message deterministically
- tests cover both collected-final-response behavior and event-surface normalization
- normalized events carry enough metadata to support later inspectability without exposing provider-specific payloads to routes

What the user sees:
No major visible UI change yet, but the app is no longer architecturally blocked on future streaming-capable harness behavior.

### P3-04 Context Builders And Harness-Owned Memory Assembly

Priority: P1

Delivered:

- added normalized model-facing context types plus pluggable context-builder hooks in `agents/chat_harness.py` and `agents/context_builders.py`, while keeping the persisted transcript as the canonical raw conversation record
- refactored `agents/openai_agent.py` so the shipped OpenAI path assembles system prompt, optional user-context prompt, and prior transcript history through a default harness-owned context builder instead of inline provider-message shaping
- extended `utils/prompt_manager.py` with an optional context-prompt lookup path so harnesses can treat context augmentation as part of execution without forcing every prompt set to ship a user-context template
- moved transcript-to-harness request shaping out of `main.py` and into `services/chat_turns.py` plus `persistence/repository.py`, so the route remains responsible for request lifecycle and rendering while the harness boundary owns memory assembly
- added regression coverage in `tests/test_context_builders.py`, `tests/test_openai_agent.py`, `tests/test_chat_harness_contract.py`, `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, and `tests/test_prompt_manager.py` to lock default parity and prove alternate memory policies can be introduced behind the harness seam
- updated contributor-facing docs so `README.md` and `AGENTS.md` describe context builders, harness-owned prompt assembly, and the current extension path consistently

Acceptance criteria met:

- the harness can assemble model-facing context without route changes
- the default path preserves current multi-turn continuity semantics
- future memory experiments can be added behind the harness boundary instead of in web handlers

What the user sees:
No major visible UI change, but the app now has a clean harness-owned place for future memory, summarization, and context experiments.

### P3-03 OpenAI Harness Adapter Migration

Priority: P0

Delivered:

- refactored the shipped OpenAI runtime in `agents/openai_agent.py` so `run()` is the canonical app-facing execution path and provider-specific request construction plus error normalization stay inside the harness adapter
- clarified `BaseAgent` in `agents/chat_harness.py` as a compatibility shim rather than the default provider-backed implementation path
- reduced provider-shaped failure aliases in `services/chat_turns.py` to explicit compatibility mapping while keeping normalized harness failure codes primary in app-layer presentation
- updated route and adapter regression coverage so `tests/test_main_routes.py`, `tests/test_openai_agent.py`, and `tests/test_chat_turn_service.py` exercise normalized `run()` behavior and normalized harness failures instead of legacy `process_message()` monkeypatching
- refreshed contributor-facing docs so `README.md` and `AGENTS.md` describe the shipped OpenAI path as a registry-resolved harness adapter behind the Phase 3 contract

Acceptance criteria met:

- the default shipped app still behaves like the current OpenAI-backed chat experience
- route handlers no longer catch OpenAI-specific exceptions directly
- OpenAI-specific wiring is localized to harness/provider code

What the user sees:
No major visible UI change, but the default OpenAI-backed path is now a real harness adapter seam rather than a route-adjacent implementation detail.

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
