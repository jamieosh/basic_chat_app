# Feature: P3-01 Chat Harness Vocabulary And Contracts

## Slug
p3-01-chat-harness-contracts

## Scope
Define the Phase 3 app-facing chat harness contract and the normalized vocabulary around it. This slice introduces serialization-friendly types for harness identity, capabilities, execution requests/results/events, normalized failures, and observability metadata; evolves the current `BaseAgent` seam into a `ChatHarness`-style contract; and updates the app-facing route/startup/diagnostic surface to depend on harness-level types instead of OpenAI-specific exceptions or naming. The implementation should keep the app runnable with the shipped OpenAI path while making the new contract the one clear interface future harnesses must satisfy.

## Non-goals
- Adding a harness registry, startup factory, or per-chat harness binding persistence. That belongs to `P3-02`.
- Delivering a full OpenAI adapter migration or alternative provider implementation. That belongs mainly to `P3-03` and later slices.
- Shipping a streaming UI, tool loop, or context-builder feature work. Those belong to `P3-04` through `P3-06`.
- Introducing user-facing harness selection or changing the current chat UX.

## Acceptance Criteria
- [x] The main app-facing execution contract, route logic, and startup wiring no longer depend on OpenAI SDK exception classes or other OpenAI-specific request/response types.
- [x] Core harness types cover identity, capabilities, execution request, execution result, execution events, normalized failures, and observability metadata using serialization-friendly Python data structures.
- [ ] Contributors can identify one clear app-facing interface to implement for a new harness, with app-layer versus harness/provider responsibilities documented in the codebase.
- [x] The existing OpenAI-backed chat flow remains behaviorally equivalent for the current non-streaming app path.

## Risks / Assumptions
This slice assumes the contract and vocabulary can land before harness registry and chat binding work without forcing a large persistence change. The main risk is scope creep into `P3-02` and `P3-03`: once normalized failures and a new interface exist, it will be tempting to also finish registry wiring or fully relocate all provider code. The plan should keep `P3-01` limited to the durable app-facing seam, with only the minimum OpenAI changes needed to preserve runtime behavior behind that seam.

## Implementation Steps
- [x] Step 1: Define the normalized chat harness contract and supporting data models, replacing or evolving the current `BaseAgent` abstraction into a `ChatHarness`-style interface with explicit request/result/event/failure metadata types — files: `agents/base_agent.py`, `agents/__init__.py`, new harness contract/types module(s) if needed
- [x] Step 2: Refactor the application-facing route, startup, and diagnostics vocabulary to depend on the harness contract and normalized failure categories instead of OpenAI exception handling or app-state naming that assumes one concrete provider agent — files: `main.py`, `utils/diagnostics.py`, `services/chat_turns.py`
- [x] Step 3: Adapt the shipped OpenAI implementation to satisfy the new harness contract while preserving current prompt, transcript, and response behavior through normalized results/failures — files: `agents/openai_agent.py`, `utils/prompt_manager.py`
- [ ] Step 4: Update contributor-facing documentation to clarify the app layer versus harness/provider layer split and identify the single interface future harnesses should implement — files: `README.md`, `plans/PHASE 3 DESIGN.md`

## Tests to Add
- [x] Add contract tests that verify the new harness request/result/event/failure models are serialization-friendly and encode the expected vocabulary -> covers AC: The main app-facing execution contract, route logic, and startup wiring no longer depend on OpenAI SDK exception classes or other OpenAI-specific request/response types.
- [x] Add route/startup regression tests proving `main.py` handles normalized harness failures without catching OpenAI SDK exception classes directly -> covers AC: The main app-facing execution contract, route logic, and startup wiring no longer depend on OpenAI SDK exception classes or other OpenAI-specific request/response types.
- [x] Update OpenAI harness tests to verify the shipped implementation still preserves current prompt assembly, transcript ordering, and final response behavior behind the new contract -> covers AC: The existing OpenAI-backed chat flow remains behaviorally equivalent for the current non-streaming app path.
- [x] Add diagnostics/readiness tests covering the updated harness-oriented startup vocabulary and availability reporting -> covers AC: Contributors can identify one clear app-facing interface to implement for a new harness, with app-layer versus harness/provider responsibilities documented in the codebase.

## Definition of Done
- [ ] All acceptance criteria checked off
- [ ] All new or updated tests pass
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy .` passes
- [ ] `uv run python -m pytest` passes
- [ ] `README.md` updated if user-visible behavior changed
- [ ] `CHANGELOG.md` updated if the feature ships
- [ ] `plans/PHASE 3 BACKLOG.md` updated when the feature ships
