# Feature: P3-06 Tool Hook And Capability Foundation

## Slug
p3-06-tool-hook-and-capability-foundation

## Source
Phase 3 backlog item `P3-06 Tool Hook And Capability Foundation` in [`plans/PHASE 3 BACKLOG.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%203%20BACKLOG.md)

## Scope
Extend the Phase 3 harness contract so tool-aware harnesses have a normalized place to advertise tool capability, describe tool activity, and plug in later orchestration hooks without changing the current app-layer send flow. Keep this slice intentionally light and in-memory: the default app should remain a normal text chat, while the contract becomes ready for future tool experiments.

This increment should focus on:

- evolving the coarse tool-support capability flag into a clearer capability surface for future tool hooks
- adding normalized tool-call and tool-result vocabulary alongside the existing text, completion, and failure event model
- defining a small extension seam that a future harness can use for tool orchestration without forcing a built-in tool loop now
- preserving the current non-streaming collector and service behavior for harnesses that never emit tool activity

## Non-goals
- Shipping a built-in tool catalog or generic tool-execution loop
- Adding UI for tool calls, approvals, or tool traces
- Persisting tool-call or tool-result events in SQLite during this slice
- Changing chat routing, HTMX contracts, or transcript persistence shape beyond what is needed to tolerate tool events in-memory
- Adding a real alternative provider implementation; that remains later Phase 3 work

## Acceptance Criteria
- [x] The harness contract exposes normalized tool capability metadata and tool-related event payloads without leaking provider-specific shapes into routes or services.
- [x] `ChatHarness` event collection can tolerate tool activity in the event stream while still producing the same final assistant text result for the current non-streaming app flow.
- [x] Harnesses that do not support tools, including the shipped default OpenAI path and `BaseAgent` compatibility shim, remain simple and keep their current behavior.
- [x] The contract includes an explicit extension seam for future tool orchestration, but this slice does not require a built-in tool loop.
- [x] Regression tests cover contract serialization/invariants, collector behavior with tool events, and default-harness backward compatibility.

## Risks / Assumptions
Assume Phase 3 keeps tool activity normalized in-memory only, while the canonical persisted transcript remains user and assistant turns. The main risk is over-designing a tool abstraction before a concrete use case exists; implementation should prefer a narrow vocabulary and one obvious extension seam over a flexible plugin system. Backward compatibility matters because current route, service, and harness tests assume a simple text-collection path, so the new event types must not destabilize non-tool execution.

## Implementation Steps
- [x] Step 1: Extend the harness contract vocabulary with normalized tool capability, tool-call, and tool-result types plus event invariants that fit the existing serialization-friendly model. — files: `agents/chat_harness.py`, `agents/base_agent.py`, `agents/__init__.py`
- [x] Step 2: Introduce a minimal no-op extension seam for future tool orchestration and keep the shipped OpenAI harness explicitly non-tool-aware by default. — files: `agents/chat_harness.py`, `agents/openai_agent.py`
- [x] Step 3: Update event collection and control-layer touchpoints so tool events can pass through the current run lifecycle without changing the web contract or persistence model. — files: `agents/chat_harness.py`, `services/chat_turns.py`
- [x] Step 4: Add regression coverage proving tool events are normalized, collector-safe, and backward compatible for the default harness and route/service flow. — files: `tests/test_chat_harness_contract.py`, `tests/test_openai_agent.py`, `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`

## Tests to Add
- [x] Contract test for JSON-serializable tool capability, tool-call, and tool-result payloads -> covers AC: The harness contract exposes normalized tool capability metadata and tool-related event payloads without leaking provider-specific shapes into routes or services.
- [x] Collector test proving a mixed stream of text, tool-call, tool-result, and completion events still yields the expected final assistant reply -> covers AC: `ChatHarness` event collection can tolerate tool activity in the event stream while still producing the same final assistant text result for the current non-streaming app flow.
- [x] Default-harness test proving the shipped OpenAI adapter still advertises no tool support and keeps the current two-event text/completion behavior -> covers AC: Harnesses that do not support tools, including the shipped default OpenAI path and `BaseAgent` compatibility shim, remain simple and keep their current behavior.
- [x] Service or route regression test proving the existing send flow still succeeds when a fake harness emits intermediate tool events before completion -> covers AC: `ChatHarness` event collection can tolerate tool activity in the event stream while still producing the same final assistant text result for the current non-streaming app flow.

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
