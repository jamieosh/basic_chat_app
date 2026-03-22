# Phase 3 Backlog

This document tracks the proposed Phase 3 delivery slices for the chat agent harness boundary.

Completed items should move to `plans/done/PHASE 3 DONE.md` once shipped.

The intent is to keep the work incremental: each slice should leave the app runnable while tightening the harness boundary a little further.

## Completed Groundwork

`P3-01 Chat Agent Harness Vocabulary And Contracts` has already shipped and now lives in [`plans/done/PHASE 3 DONE.md`](/Users/jamie/Development/basic_chat_app/plans/done/PHASE%203%20DONE.md).

The rest of this backlog assumes `ChatHarness`, normalized harness types, and the first contract vocabulary are already in place.

## Proposed Items

### P3-02 Harness Registry, Control Wiring, And Stable Binding

Priority: P0

Problem:
Startup still needs a clearer separation between the route layer, the small control/service layer, and harness resolution, and chats are not yet associated with a harness binding that can survive later provider expansion.

Deliver:

- add harness-focused startup wiring and a harness registry or factory
- centralize harness selection behind a small control/service layer rather than route-level wiring
- persist a harness key and optional harness version on chat creation
- keep one chat bound to one harness configuration for its lifetime
- keep provider or agent configuration independent from chat records and resolved through the harness binding
- preserve a simple single-default-harness setup for the out-of-box app

Acceptance criteria:

- the app can resolve the harness for a chat without route-level provider branching
- the route layer no longer acts as the de facto owner of harness selection and execution wiring
- new chats are created with a stable harness binding
- the default configuration remains simple for contributors who only want the shipped baseline

What the user sees:
No major visible UI change, but a chat is now anchored to a specific harness configuration behind the scenes.

### P3-03 OpenAI Harness Adapter Migration

Priority: P0

Problem:
The current OpenAI implementation is still effectively the app harness. Phase 3 needs that implementation moved behind the new harness contract before any provider-swapping story is credible.

Deliver:

- migrate the existing OpenAI logic behind the Phase 3 harness contract
- normalize OpenAI errors into harness-level failure categories
- keep current prompt-template behavior working through the new harness wiring
- preserve the current default request and response behavior for users

Acceptance criteria:

- the default shipped app still behaves like the current OpenAI-backed chat experience
- route handlers no longer catch OpenAI-specific exceptions directly
- OpenAI-specific wiring is localized to harness/provider code

What the user sees:
The default chat behavior should feel the same, but the implementation becomes much easier to swap or extend.

### P3-04 Context Builders And Harness-Owned Memory Assembly

Priority: P1

Problem:
Conversation history is currently handed to the provider in a straightforward way, but the app has no explicit place for harness-owned memory policy, context augmentation, or future summarization and retrieval experiments.

Deliver:

- introduce pluggable context-builder hooks owned by the harness layer
- keep the persisted transcript as the canonical raw conversation record
- provide a default context builder that reproduces current transcript-based behavior
- make prompt-template use, prompt assembly, and context augmentation part of harness execution rather than route behavior

Acceptance criteria:

- the harness can assemble model-facing context without route changes
- the default path preserves current multi-turn continuity semantics
- future memory experiments can be added behind the harness boundary instead of in web handlers

What the user sees:
No required UI change, but the app gains a clean place for better memory behavior later.

### P3-05 Streaming-Capable Harness Execution Surface

Priority: P1

Problem:
The current contract returns only a final string response. That makes later streaming support a redesign problem rather than an additive change.

Deliver:

- introduce an event-capable harness execution surface
- make `run_events()` the canonical execution path for `ChatHarness`
- keep `run()` only as a thin collector over `run_events()` for non-streaming callers
- support collection of a final assistant response for the existing non-streaming web flow
- define normalized event types that can later support streaming text, tool activity, and completion metadata
- make run/event metadata inspectable enough for the small control/service layer to reason about execution coherently
- keep the initial Phase 3 web UX simple even if the harness surface is stream-ready

Acceptance criteria:

- provider implementations do not maintain separate execution logic for `run()` and `run_events()`
- a harness can expose streaming-capable events without redesigning the app-facing contract
- the current HTMX send flow can still collect a final assistant message deterministically
- tests cover both collected-final-response behavior and event-surface normalization
- normalized events carry enough metadata to support later inspectability without exposing provider-specific payloads to routes

What the user sees:
Possibly no immediate UI change, but the app stops being architecturally blocked on future streaming support.

### P3-06 Tool Hook And Capability Foundation

Priority: P2

Problem:
If the Phase 3 contract is text-only, later tool-use experiments will either leak provider details or force another redesign soon after the harness boundary lands.

Deliver:

- add capability flags for tool-hook support
- define normalized tool-call and tool-result event shapes
- provide extension hooks for harness implementations that want tool orchestration later
- avoid shipping a heavy built-in tool loop in this phase

Acceptance criteria:

- the harness contract can represent tool activity without app-layer redesign
- harnesses that do not support tools can remain simple
- the default shipped app does not need built-in tools to satisfy the Phase 3 design

What the user sees:
Usually no visible change yet, but the harness contract becomes future-proof enough for tool experiments.

### P3-07 Control-Layer Refactor, Error-Handling, And Harness Observability

Priority: P1

Problem:
Even with a better harness contract, the app still needs a small control/service layer that owns request lifecycle, observability, and failure presentation so the web layer depends only on normalized harness outcomes.

Deliver:

- refactor route and service code so a small control/service layer consumes normalized harness results and failures
- move provider-specific error mapping out of route handlers
- normalize harness-level observability fields for logs and diagnostics across providers
- preserve the existing persistence and idempotency guarantees from Phase 2
- keep user-facing failure presentation understandable and deterministic

Acceptance criteria:

- route handlers do not branch on provider SDK exception classes
- the control/service layer owns normalized run lifecycle coordination without becoming a large orchestration system
- logs and diagnostics can identify the harness key, optional version, provider identity, and normalized failure category without provider-specific branching in routes
- request lifecycle behavior remains covered for success, failure, duplicate replay, and conflict cases
- the app layer remains responsible for persistence outcomes and user-facing rendering

What the user sees:
Failure behavior should remain predictable while becoming less tied to one provider backend.

### P3-08 Test, Docs, And Forking Guidance Alignment

Priority: P1

Problem:
Phase 3 will add important terminology and extension seams. Without explicit tests and documentation, contributors will drift back toward route-level coupling.

Deliver:

- add regression coverage for harness contract behavior, harness resolution, normalized failures, and default OpenAI parity
- add a fake or minimal test harness to prove the app is not coupled to OpenAI-specific wiring
- document how to add a new harness implementation without touching unrelated web-chat code
- update [`README.md`](/Users/jamie/Development/basic_chat_app/README.md) to explain the Phase 3 chat agent harness boundary, extension seam, and default customization path clearly
- update [`AGENTS.md`](/Users/jamie/Development/basic_chat_app/AGENTS.md) so the project summary, architecture notes, and contributor guidance stay aligned with the harness terminology
- update planning docs to keep Phase 3 terminology aligned with the contributor-facing docs and the newer workbench/control-layer framing
- align backlog, design, done, and contributor guidance as items ship

Acceptance criteria:

- contributors can follow one obvious path to add a new provider-backed harness
- Phase 3 terminology is consistent across code and docs
- [`README.md`](/Users/jamie/Development/basic_chat_app/README.md) and [`AGENTS.md`](/Users/jamie/Development/basic_chat_app/AGENTS.md) describe the same extension model as the Phase 3 planning docs
- the updated docs describe the UI, harness, and small control/service layer consistently
- tests lock the default harness behavior while leaving space for alternate implementations

What the user sees:
No direct product change, but the repo becomes much easier to understand and extend safely.

### P3-09 Alternative Harness Proof Implementation

Priority: P1

Problem:
The Phase 3 harness boundary can look clean on paper while still remaining OpenAI-shaped in practice. A fake harness helps test decoupling, but it does not prove that a real provider with different request, event, and failure shapes fits the contract well.

Deliver:

- implement one real non-default harness behind the Phase 3 harness contract, with Anthropic as the explicit Phase 3 proof target
- keep selection backend-configured only, with no user-facing harness picker
- validate that startup wiring, harness binding, observability, normalized failures, and default chat flow all work with the alternative harness
- use Anthropic specifically because it meaningfully stretches the contract instead of mostly mirroring an OpenAI-compatible wire shape

Acceptance criteria:

- the app can run end-to-end against Anthropic through backend configuration only
- no route-level provider-specific branching is needed to support the alternative harness
- harness logs and diagnostics remain normalized across the default and alternative harnesses
- the Anthropic harness proves the contract can absorb a materially different provider shape without reshaping the web chat layer

What the user sees:
No required UI change, but Phase 3 is now validated against a real alternative provider instead of only the default implementation.

## Sequencing Notes

- `P3-01` is already complete groundwork for the rest of Phase 3.
- `P3-02` and `P3-03` establish the control wiring and default-harness migration on top of that groundwork.
- `P3-04` and `P3-05` make the harness actually useful for memory and streaming evolution.
- `P3-06` should stay intentionally light unless a concrete tool use case appears.
- `P3-07` and `P3-08` should tighten the app-layer cleanup and documentation before the final proof step.
- `P3-09` should land late in Phase 3 as the real-world proof that the harness boundary is not only OpenAI in disguise.
