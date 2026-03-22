# Feature: P3-05 Streaming-Capable Harness Execution Surface

## Slug
p3-05-streaming-capable-harness-execution-surface

## Source
Phase 3 backlog item `P3-05 Streaming-Capable Harness Execution Surface` in [`plans/PHASE 3 BACKLOG.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%203%20BACKLOG.md)

## Scope
Make the harness contract event-first in practice so provider-backed implementations expose one canonical execution path through `run_events()`, while the current HTMX send flow still collects and persists a deterministic final assistant response without introducing user-visible streaming yet.

This increment should:

- refactor the normalized harness contract in [`agents/chat_harness.py`](/Users/jamie/Development/basic_chat_app/agents/chat_harness.py) so `run()` becomes a thin collector over `run_events()`
- tighten normalized event/result invariants so event metadata is coherent enough for later streaming and inspectability work
- update the shipped OpenAI harness in [`agents/openai_agent.py`](/Users/jamie/Development/basic_chat_app/agents/openai_agent.py) to emit one event-driven execution path instead of maintaining separate logic for `run()` and `run_events()`
- keep the current non-streaming web flow in [`main.py`](/Users/jamie/Development/basic_chat_app/main.py) and [`services/chat_turns.py`](/Users/jamie/Development/basic_chat_app/services/chat_turns.py) able to collect a final assistant message deterministically for persistence and rendering
- expand regression coverage so contract, adapter, service, and route tests lock the new event-first behavior

## Non-goals
- Shipping incremental browser streaming or changing the HTMX transcript UX
- Implementing tool execution loops or real tool-call handling beyond leaving the event surface extensible for later phases
- Adding a new provider, user-facing harness picker, or broader control-plane observability work planned for later Phase 3 slices
- Reworking chat persistence, duplicate replay semantics, or route ownership beyond what is required to consume the event-capable harness path safely

## Acceptance Criteria
- [x] `ChatHarness.run()` is only a collector over `run_events()`, and provider-backed harnesses do not maintain separate execution logic for the two paths.
- [x] The normalized event model can represent partial output, completion, failure, and execution metadata without leaking provider-specific payloads into routes.
- [x] The current `/send-message-htmx` flow still produces one deterministic final assistant message for persistence and HTML rendering when consuming the event-capable harness path.
- [x] Failure handling remains normalized and deterministic when execution fails partway through the event stream.
- [x] Tests cover successful event collection, failure propagation, and default OpenAI parity through the new canonical execution surface.

## Risks / Assumptions
The current shipped OpenAI path may still use a non-streaming provider request under the hood at first; this plan assumes Phase 3 only needs an event-capable contract, not an actual streaming transport from OpenAI to the browser.

The existing route and service split in [`main.py`](/Users/jamie/Development/basic_chat_app/main.py) and [`services/chat_turns.py`](/Users/jamie/Development/basic_chat_app/services/chat_turns.py) is intentionally kept small for this slice. If event collection starts turning into broader lifecycle orchestration, that work should be deferred to `P3-07` instead of growing this increment.

Result and event invariants need to stay strict enough that duplicate replay, conflict handling, and persisted assistant-message behavior remain deterministic even if a harness emits multiple output events before completion.

## Implementation Steps
- [x] Step 1: Refactor the core harness contract so `run_events()` is the canonical execution method, `run()` is a collector, and normalized event/result invariants cover partial output, completion, failure, and inspectable metadata. — files: [`agents/chat_harness.py`](/Users/jamie/Development/basic_chat_app/agents/chat_harness.py), [`tests/test_chat_harness_contract.py`](/Users/jamie/Development/basic_chat_app/tests/test_chat_harness_contract.py)
- [x] Step 2: Update compatibility and default provider harnesses to emit a single event-driven execution path, keeping provider-specific request building and failure normalization inside the harness adapter. — files: [`agents/chat_harness.py`](/Users/jamie/Development/basic_chat_app/agents/chat_harness.py), [`agents/openai_agent.py`](/Users/jamie/Development/basic_chat_app/agents/openai_agent.py), [`tests/test_openai_agent.py`](/Users/jamie/Development/basic_chat_app/tests/test_openai_agent.py)
- [x] Step 3: Add a small collection seam for the current non-streaming app flow so turn persistence and HTML rendering consume the event-capable harness path without changing the HTMX UX. — files: [`services/chat_turns.py`](/Users/jamie/Development/basic_chat_app/services/chat_turns.py), [`main.py`](/Users/jamie/Development/basic_chat_app/main.py), [`tests/test_chat_turn_service.py`](/Users/jamie/Development/basic_chat_app/tests/test_chat_turn_service.py), [`tests/test_main_routes.py`](/Users/jamie/Development/basic_chat_app/tests/test_main_routes.py)
- [ ] Step 4: Tighten contributor-facing terminology only where the new plan exposes changed contract expectations for harness implementers. — files: [`README.md`](/Users/jamie/Development/basic_chat_app/README.md), [`AGENTS.md`](/Users/jamie/Development/basic_chat_app/AGENTS.md)

## Tests to Add
- [x] Contract test proving `run()` collects a final result from multiple normalized events and preserves event ordering metadata. -> covers AC: `ChatHarness.run()` is only a collector over `run_events()`, and provider-backed harnesses do not maintain separate execution logic for the two paths.
- [x] Contract test proving a failure event stream becomes a normalized failed result or raised execution error without exposing provider-shaped exceptions. -> covers AC: Failure handling remains normalized and deterministic when execution fails partway through the event stream.
- [x] OpenAI adapter test proving the default harness exposes equivalent final output through both direct collection and the event surface while sharing one execution path. -> covers AC: Tests cover successful event collection, failure propagation, and default OpenAI parity through the new canonical execution surface.
- [x] Route/service regression test proving `/send-message-htmx` still persists and renders the final assistant reply correctly when the harness yields multiple output events before completion. -> covers AC: The current `/send-message-htmx` flow still produces one deterministic final assistant message for persistence and HTML rendering when consuming the event-capable harness path.
- [x] Route/service regression test proving an execution failure after one or more output events still resolves to the normalized failure path without persisting a partial assistant turn. -> covers AC: Failure handling remains normalized and deterministic when execution fails partway through the event stream.

## Definition of Done
- [ ] All acceptance criteria checked off
- [ ] All new or updated tests pass
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy .` passes
- [ ] `uv run python -m pytest` passes
- [ ] `README.md` updated if user-visible behavior changed
- [ ] E2E or visual checks run when UI behavior changes materially
- [ ] `CHANGELOG.md` updated when the feature ships
- [ ] Matching phase backlog and `plans/done/PHASE X DONE.md` updated when the feature ships
- [ ] `AGENTS.md` updated if architecture or contributor guidance changes
