# Feature: P3-03 OpenAI Harness Adapter Migration

## Slug
openai-harness-adapter-migration

## Source
Phase 3 backlog item `P3-03 OpenAI Harness Adapter Migration`

## Scope
Finish the remaining migration work needed to make the shipped OpenAI runtime behave as a true harness adapter behind the Phase 3 contract. This increment is intentionally narrower than the original backlog text because `P3-01` and `P3-02` already shipped the base contract, registry wiring, and stable chat binding. The work here should preserve the current default OpenAI-backed chat behavior while removing remaining legacy seams that still let the app layer, tests, or failure mapping behave as though `process_message()` and OpenAI-shaped errors are first-class application interfaces.

## Non-goals
- Adding a new provider or alternative harness implementation.
- Introducing streaming, tool hooks, or context-builder abstractions.
- Changing the user-facing prompt set, chat UX, or persistence lifecycle semantics.
- Refactoring the full route/service architecture beyond what is needed to complete the adapter migration cleanly.

## Acceptance Criteria
- [x] The default shipped chat flow still produces the same OpenAI-backed request/response behavior, prompt-template usage, and persisted turn lifecycle as today.
- [x] The main send path depends on normalized `ChatHarness.run()` execution and normalized failure codes rather than legacy `process_message()` monkeypatching or OpenAI SDK exception assumptions.
- [x] OpenAI-specific error translation is localized to `agents/openai_agent.py` and app/service failure presentation only consumes normalized harness failure codes.
- [x] Legacy compatibility aliases that keep provider-shaped failure codes alive in app-facing behavior are removed or clearly reduced to non-routing compatibility shims.
- [x] Regression coverage proves default OpenAI parity while locking route and service behavior to normalized harness results/failures.

## Risks / Assumptions
The main risk is over-scoping into broader Phase 3 cleanup that belongs in later items such as `P3-05` or `P3-07`. This plan assumes the contract, registry, and persisted binding model from `P3-01` and `P3-02` remain intact and only need migration cleanup around the default OpenAI adapter. There is also a compatibility risk in tightening tests away from `process_message()`: some existing tests currently patch the legacy shim directly, so the migration needs careful test updates to avoid accidentally reducing coverage of user-visible failure behavior.

## Implementation Steps
- [x] Step 1: Audit and tighten the OpenAI harness adapter so `run()` is the canonical app-facing execution path and OpenAI error normalization stays fully inside the adapter boundary. — files: `agents/openai_agent.py`, `agents/chat_harness.py`, `agents/base_agent.py`
- [x] Step 2: Remove route/service reliance on provider-shaped or legacy compatibility failure handling, keeping only normalized harness failure presentation in the app layer. — files: `main.py`, `services/chat_turns.py`
- [x] Step 3: Update unit and route tests to exercise the normalized harness path directly while preserving current OpenAI-backed behavior and prompt assembly parity. — files: `tests/test_openai_agent.py`, `tests/test_main_routes.py`, `tests/test_chat_harness_contract.py`, `tests/test_chat_turn_service.py`
- [ ] Step 4: Refresh contributor-facing docs so they describe the shipped OpenAI runtime as a harness adapter behind the registry/contract boundary rather than a route-adjacent agent. — files: `README.md`, `AGENTS.md`

## Tests to Add
- [x] Route failure regression that injects `ChatHarnessExecutionError` through `run()` for each user-visible failure category and verifies the rendered HTMX response -> covers AC: The main send path depends on normalized `ChatHarness.run()` execution and normalized failure codes rather than legacy `process_message()` monkeypatching or OpenAI SDK exception assumptions.
- [x] OpenAI adapter regression that proves provider SDK exceptions are translated into normalized `ChatHarnessFailure` codes and observability metadata without leaking SDK types across the app boundary -> covers AC: OpenAI-specific error translation is localized to `agents/openai_agent.py` and app/service failure presentation only consumes normalized harness failure codes.
- [x] Default OpenAI parity regression that verifies prompt-template loading, conversation-history assembly, request construction, and final `ChatHarnessResult` output remain unchanged for the shipped default path -> covers AC: The default shipped chat flow still produces the same OpenAI-backed request/response behavior, prompt-template usage, and persisted turn lifecycle as today.
- [x] Failure-presentation regression that removes coverage dependence on provider-shaped aliases such as `bad_request`, `api_error`, and `empty_model_response` unless they are intentionally retained as compatibility-only shims -> covers AC: Legacy compatibility aliases that keep provider-shaped failure codes alive in app-facing behavior are removed or clearly reduced to non-routing compatibility shims.

## Definition of Done
- [ ] All acceptance criteria checked off
- [x] All new or updated tests pass
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy .` passes
- [ ] `uv run python -m pytest` passes
- [ ] `README.md` updated if user-visible behavior changed
- [ ] E2E or visual checks run when UI behavior changes materially
- [ ] `CHANGELOG.md` updated when the feature ships
- [ ] Matching phase backlog and `plans/done/PHASE X DONE.md` updated when the feature ships
- [ ] `AGENTS.md` updated if architecture or contributor guidance changes
