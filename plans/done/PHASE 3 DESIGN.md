# Phase 3 Design

This document captures the intended Phase 3 product and architecture shape so contributors can make the harness boundary clearer without losing the lightweight workbench posture of the project.

See [`plans/PHASE 3 BACKLOG.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%203%20BACKLOG.md) for the proposed delivery slices.

See [`plans/PARKING LOT.md`](/Users/jamie/Development/basic_chat_app/plans/PARKING%20LOT.md) for ideas that are known but intentionally deferred.

## Goal

Phase 3 moves the project from a chat-first app that is still coupled fairly directly to one provider implementation into a lightweight workbench with a clear application-facing harness boundary and a small control-layer seam.

That boundary should make all of the following easier without route-level rewrites:

- swapping model providers such as OpenAI, Claude, or OpenRouter-backed variants
- adding or experimenting with chat agent harnesses, including framework-backed implementations
- introducing streaming-capable execution
- letting the harness own context assembly and memory behavior
- adding tool-use hooks later without redesigning the app surface
- keeping open the option of a future split between the web app and a separate harness service
- proving the abstraction with at least one real non-default harness that is configured only in the backend
- making inspectable runs, events, and stable bindings easier to support without treating the transcript as the whole system

## Design Principles

- Keep the default app usable out of the box with one simple harness configuration.
- Keep the frontend server-rendered and HTMX-first.
- Treat the chat agent harness boundary as transport-neutral so the web UI is only one possible client.
- Design the Phase 3 harness in-process first, but with request and response objects that are clean enough to become RPC-safe later.
- Keep the common harness contract small and explicit.
- Use optional capability flags rather than leaking provider-specific behavior into the app layer.
- Keep a small control/service layer between routes and harnesses so the web layer is not the de facto runtime owner.
- Let the current chat-centric persistence and routing continue to work, but avoid treating transcript history as the only durable concept forever.
- Let the harness layer own context assembly and prompt-template concerns.
- Treat frameworks such as LangChain as implementation details behind the same harness contract, not as app-level concepts.
- Keep one chat bound to one harness configuration for its lifetime unless a later phase explicitly introduces harness switching.
- Improve inspectability through normalized events and observability rather than hidden provider behavior.

## What Phase 3 Means For Users

Phase 3 is mostly an architecture and product-foundation phase rather than a dramatic UI-feature phase.

For users, the promise is:

- the app should still feel simple and predictable
- future capabilities such as streaming, better memory behavior, or tool use can be added cleanly rather than as one-off rewrites
- changing or upgrading the underlying model implementation should not destabilize the main chat experience

Users may not see a large visible difference immediately, but they should benefit from a more coherent path to richer chat behavior in later phases.

## What Phase 3 Means For Developers And Forks

Phase 3 is the point where model and harness experimentation should stop spilling across routes, startup wiring, and provider-specific error handling, and where the first small control-layer seam should become visible.

For developers and fork maintainers, the intended outcome is:

- the web chat layer talks to a single harness contract
- provider-specific code lives in one dedicated harness/provider area
- contributors can follow one registry-backed path to add a new harness without editing unrelated route code
- adding a Claude or OpenRouter implementation should be localized
- trying a framework-backed harness should not require reshaping the chat UI or route flow
- future non-web interfaces should be able to reuse the same harness contract
- the Phase 3 seam is validated by at least one real non-default harness rather than only a renamed OpenAI path
- the route layer starts to look like a client of a small control/service layer rather than the owner of execution behavior
- the shipped OpenAI adapter remains the default baseline, not the mandatory template for every future harness

## Resolved Scope Decisions

### Deployment Shape

- Phase 3 keeps the chat agent harness in-process with the FastAPI app.
- The harness contract should be designed so it could later be exposed across an API or worker boundary.
- Phase 3 does not introduce a separate harness service or separate deployment unit.
- Phase 3 may introduce a small control/service layer inside the same app, but not a large orchestration system.

### Layer Responsibilities

- Interface/transport layer:
  - web routes, HTMX responses, and any later Telegram or WhatsApp adapters
- Minimal control layer:
  - current chat identity, future session-friendly binding concepts, run lifecycle coordination, normalized observability, and UI-facing failure presentation
- Chat agent harness layer:
  - normalized chat execution contract, context assembly, prompt-template use, provider selection, capability exposure, observability hooks, and execution hooks
- Provider or harness layer:
  - concrete OpenAI, Claude, OpenRouter, or framework-backed implementations

The recommended contributor path is:

- add a new harness module under `agents/`
- keep prompt assembly, context shaping, and provider failure mapping inside that harness
- register it in `agents/harness_registry.py` with a stable key and optional version
- switch the default through settings or registry wiring rather than route branching
- prove the change in contract, registry, service, and route tests

Phase 3 does not need a rich session model yet, but it should stop assuming that a plain chat transcript is the full durable object of the system.

### Chat Agent Harness Ownership Of Memory Assembly

- The harness layer should own memory and context assembly.
- The chat application should continue to persist the canonical raw chat transcript.
- Pluggable context builders should transform raw transcript and harness inputs into the model-facing context.
- Phase 3 should not attempt to ship long-term retrieval, project memory, or a full knowledge system.

This is the recommended split because memory policy is part of harness behavior, not transport behavior. If routes or templates decide how memory is assembled, provider swaps and harness experiments will keep leaking back into app code. The key guardrail is that the app still owns the canonical stored transcript and request lifecycle, while the harness owns how that data is prepared for execution.

### Streaming And Tools

- Streaming support should be part of the harness type and event design from the start.
- Phase 3 does not need a large streaming UI rollout to justify that design.
- Tool use should exist at the contract level through hooks and event types.
- Phase 3 does not need a full tool loop or broad built-in tool catalog.

### Provider Capability Model

- The harness contract should expose a small common core that all harnesses satisfy.
- Optional features should be represented as capability flags or optional event types.
- Provider-specific request or response details should not leak into route handlers.
- Phase 3 should validate this model by wiring at least one real non-default harness behind backend configuration only, with no required user-facing harness picker.

### Harness Selection And Binding

- Each chat should be bound to one harness configuration for its lifetime.
- In this phase, that means a persisted harness key plus optional harness version, not a full provider-configuration snapshot and not a dedicated long-lived Python object per chat.
- Provider or agent configuration should be managed independently from the chat record and resolved through the bound harness key and version.
- Phase 3 may keep harness selection implicit through a single default harness at first, but the data model and harness contract should not assume only one provider forever.
- Current chat records can remain the persisted binding anchor in Phase 3, but the control-layer contract should leave room for a richer session model in later phases.

## Chat Agent Harness Contract Shape

The app-facing chat agent harness boundary should be able to express at least these concepts:

- harness identity and human-readable display metadata
- capability flags such as streaming support or tool-hook support
- a normalized execution request
- a normalized event stream or event-capable result
- normalized failure categories
- extension hooks for context builders and later tool orchestration
- normalized observability metadata for logging and diagnostics
- enough identity and binding metadata for a later control layer to reason about runs without route-level provider knowledge

For code-facing naming, Phase 3 should prefer `ChatHarness` as the primary abstraction name. `Chat Agent Harness` can remain the broader planning term in contributor-facing docs, but implementation code should stay shorter and more direct.

The request object should be serialization-friendly and should avoid passing framework-specific clients, database handles, or provider SDK objects across the boundary.

The response model should support both:

- collecting a final assistant message for the current non-streaming web flow
- emitting intermediate events later without redesigning the contract

### Current P3-01 Contract Vocabulary

The current implementation contract lives in `agents/chat_harness.py` and centers the app on these types:

- `ChatHarness`: the primary app-facing interface for chat execution
- `ChatHarnessIdentity`: stable harness key plus display metadata
- `ChatHarnessCapabilities`: optional capability flags such as streaming/tool support
- `ChatHarnessRequest`: serialization-friendly execution input
- `ChatHarnessResult`: normalized final response for the current non-streaming flow
- `ChatHarnessEvent`: normalized event payload for streaming-capable execution
- `ChatHarnessFailure`: normalized failure category and retryability metadata
- `ChatHarnessObservability`: normalized model/provider/request metadata for logs and diagnostics

`BaseAgent` should now be treated as a compatibility shim for older `process_message()` implementations, not as the preferred extension point for new harnesses.

The intended boundary is:

- app layer code depends on `ChatHarness`, `ChatHarnessRequest`, normalized failure codes, and display metadata from `ChatHarnessIdentity`
- harness implementations own prompt assembly, provider SDK calls, and mapping provider-specific exceptions into `ChatHarnessFailure`
- provider-specific request and exception types stay inside the harness/provider implementation instead of leaking back into routes

P3-01 should now be treated as completed groundwork for the rest of Phase 3 rather than an open design question.

## Information Flow

The intended Phase 3 flow is:

1. The web route validates the request and resolves the target chat.
2. A small control/service layer starts the turn lifecycle and loads the persisted transcript.
3. The control/service layer resolves the chat agent harness bound to that chat.
4. The control/service layer sends a normalized harness request plus raw prior turns into the harness layer.
5. The harness assembles model-facing context through its configured context builders.
6. The harness executes the selected provider or harness implementation and emits normalized events or a final result.
7. The control/service layer maps the normalized result back into persisted assistant turns or normalized failure outcomes.
8. The web layer renders the HTMX response without knowing provider-specific details.

## Persistence And Configuration Implications

- The current persistence model should remain authoritative for chats, messages, and turn requests.
- Phase 3 likely needs a persisted harness key and optional harness version on each chat session, even if all new chats initially use the same default harness.
- Harness definitions and provider configuration should be centralized in harness-focused settings and factory wiring rather than scattered through route startup code.
- Prompt templates should move behind the harness/context assembly layer rather than living as a route concern or a provider-only concern.
- The initial control/service layer should own normalized run lifecycle coordination without pretending to be a full control plane yet.

## Interface Neutrality And Future Multi-Client Use

Phase 3 should not build Telegram, WhatsApp, or a standalone harness service. It should, however, avoid painting the app into a web-only corner.

That means:

- route handlers should become clients of the harness boundary rather than owners of provider logic
- harness request and result types should not assume HTML or HTMX
- harness behavior should be reusable by later interface adapters
- a later web-app to harness-service split should feel like an extraction of the same contract, not a replacement architecture
- the initial control/service layer should be thin enough that it can later grow into a richer session/run control layer without being rewritten from scratch

## Alternative Harness Proof Requirement

Phase 3 should include one real alternative harness implementation in addition to the default OpenAI path.

The purpose is not to ship a large provider matrix or a user-facing model selector. The purpose is to force the architecture to prove that the harness seam is real under a non-OpenAI message model, failure model, and capability profile.

The shipped OpenAI adapter should be treated as the default baseline for this repository, not as the only acceptable implementation shape.

This proof implementation should:

- be enabled only through backend configuration
- avoid adding a user-facing harness-switching UI
- remain small enough that it validates the seam without becoming a separate product track
- preferably use a provider with meaningfully different message and event shapes so the contract is genuinely exercised

## Out Of Scope For Phase 3

- introducing a separate harness process or deployable service
- user-facing harness switching UI
- broad multi-provider feature parity across several alternative harnesses
- a full tool-execution loop
- file attachments, project containers, or chat forking workflows
- authentication or public-deployment hardening
- a rich multi-agent control plane or collaboration model
- forcing third-party frameworks into the baseline architecture
- replacing the server-rendered HTMX-first UI model

## Implementation Guardrails

- Do not let OpenAI, Claude, or other provider exception types leak into route handlers.
- Do not make the harness contract depend on FastAPI, HTMX, or HTML rendering concerns.
- Do not let provider-specific prompt assembly remain spread between routes and provider adapters.
- Keep the default harness path simple enough that a contributor can still follow the normal send flow quickly.
- Prefer a small number of obvious harness extension seams over a highly generic plugin system.
- Preserve deterministic behavior and testability for the default non-streaming request path.
- Normalize harness-level observability so logs and diagnostics stay comparable across provider implementations.
- Prove the boundary with at least one fake or minimal non-OpenAI harness in tests before calling the design complete.
- Prove the boundary with one real non-default harness implementation before calling Phase 3 complete.
- Keep the first control/service layer small enough that contributors can still follow the default send flow without learning a full orchestration system.

## Anti-Goals

- Do not turn Phase 3 into a full agent framework.
- Do not require a separate process boundary to justify the harness design.
- Do not make chats carry full provider credentials or full provider tuning payloads in persistence.
- Do not let a provider-backed implementation redefine chat lifecycle, persistence, or UI behavior.
- Do not make framework-backed harnesses the default mental model for contributors.

## Open Design Points To Keep Visible

These do not block the Phase 3 design direction, but they should stay explicit while implementation is broken into slices:

- whether the initial Phase 3 harness should expose a synchronous `run()` plus a streaming-capable `run_events()` path, or standardize immediately on an event-stream-first surface with a collector for non-streaming callers
- how much provider configuration should remain live behind a named harness key and optional version versus being selectively snapshotted for stronger reproducibility
- whether tool-call and tool-result events should be stored in persistence during Phase 3, or only normalized in-memory while the canonical transcript remains user and assistant messages only
- how far the initial control/service layer should go in representing runs and event history before Phase 4 takes on the richer session model explicitly
