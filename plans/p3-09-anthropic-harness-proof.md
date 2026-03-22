# Feature: P3-09 Anthropic Harness Proof Implementation

## Slug
p3-09-anthropic-harness-proof

## Source
Phase 3 Backlog — `P3-09 Alternative Harness Proof Implementation`

## Scope
Implement a real Anthropic-backed chat harness behind the existing `ChatHarness` contract and register it alongside the shipped OpenAI harness. Extend runtime settings, startup diagnostics, and registry wiring so new chats can be configured to bind to either `openai` or `anthropic` through backend configuration only, with no route-level provider branching and no user-facing harness picker. Update contributor and runtime docs so the provider-selection path is explicit in `.env`, `README.md`, and `AGENTS.md`.

## Non-goals
- No user-facing provider or model picker in the chat UI.
- No retroactive migration of existing chats from one harness binding to another.
- No attempt to unify OpenAI and Anthropic request construction into one provider-agnostic implementation class.
- No streaming UI work, tool orchestration changes, or multi-provider feature parity beyond the Phase 3 proof target.
- No expansion into a larger provider matrix beyond the shipped OpenAI harness and one Anthropic proof harness.

## Acceptance Criteria
- [x] The registry can build and resolve both `openai` and `anthropic` harnesses, and `DEFAULT_CHAT_HARNESS_KEY` can choose either one as the default for newly created chats.
- [x] Anthropic execution runs end-to-end through the existing `ChatHarness` contract with normalized observability and normalized failure mapping, without adding provider-specific branching to routes or the service layer.
- [x] Startup validation and readiness reporting correctly reflect the configured harness choice, including required credentials and prompt-template paths for Anthropic when it is selected.
- [x] New chats persist the configured harness binding, existing chats keep their stored binding, and the configuration path is clearly documented in `.env.example`, `README.md`, and `AGENTS.md`.

## Risks / Assumptions
Anthropic will require a new SDK dependency and a provider-specific adapter rather than a shallow copy of `agents/openai_agent.py`. The current startup diagnostics are OpenAI-shaped, so this slice likely needs a more harness-aware startup validation path without pushing provider logic back into `main.py`. Prompt-template handling may need a parallel `templates/prompts/anthropic/` tree or an explicit decision to reuse a minimal shared prompt set while still keeping harness-owned prompt assembly intact. This plan assumes the existing persisted `harness_key` and `harness_version` model remains sufficient and that changing `DEFAULT_CHAT_HARNESS_KEY` should continue to affect only newly created chats.

## Implementation Steps
- [x] Step 1: Add Anthropic runtime support and harness wiring — files: `pyproject.toml`, `uv.lock`, `agents/anthropic_agent.py`, `agents/__init__.py`, `agents/harness_registry.py`, `utils/settings.py`, `templates/prompts/anthropic/`
- [x] Step 2: Generalize startup diagnostics and startup wiring around the configured default harness while preserving normalized readiness metadata — files: `utils/diagnostics.py`, `main.py`, `tests/test_diagnostics.py`, `tests/test_harness_registry.py`, `tests/test_main_routes.py`
- [x] Step 3: Lock contract, service, and provider behavior with regression coverage for Anthropic selection, normalized failures, and persisted binding behavior — files: `tests/test_anthropic_agent.py`, `tests/test_chat_turn_service.py`, `tests/test_chat_harness_contract.py`, `tests/test_settings.py`
- [x] Step 4: Document the provider-selection flow and shipped configuration surface clearly for contributors and local runtime setup — files: `.env.example`, `README.md`, `AGENTS.md`

## Tests to Add
- [x] Add Anthropic harness adapter tests for identity, context assembly, request construction, event collection parity, and provider-specific failure normalization -> covers AC: Anthropic execution runs end-to-end through the existing `ChatHarness` contract with normalized observability and normalized failure mapping, without adding provider-specific branching to routes or the service layer.
- [x] Add registry and settings tests proving both `openai` and `anthropic` can be configured as valid defaults and that Anthropic-specific env vars are parsed and validated correctly -> covers AC: The registry can build and resolve both `openai` and `anthropic` harnesses, and `DEFAULT_CHAT_HARNESS_KEY` can choose either one as the default for newly created chats.
- [x] Add diagnostics and route-startup tests proving startup failures reference the correct provider credentials/templates and readiness metadata reflects the selected harness -> covers AC: Startup validation and readiness reporting correctly reflect the configured harness choice, including required credentials and prompt-template paths for Anthropic when it is selected.
- [x] Add service and route lifecycle tests proving new chats bind to the configured default while existing chats continue using their stored harness binding after the default changes -> covers AC: New chats persist the configured harness binding, existing chats keep their stored binding, and the configuration path is clearly documented in `.env.example`, `README.md`, and `AGENTS.md`.

## Definition of Done
- [x] All acceptance criteria checked off
- [x] All new or updated tests pass
- [x] `uv run ruff check .` passes
- [x] `uv run mypy .` passes
- [x] `uv run python -m pytest` passes
- [x] `README.md` updated if user-visible behavior changed
- [x] E2E or visual checks run when UI behavior changes materially
- [ ] `CHANGELOG.md` updated when the feature ships
- [ ] Matching phase backlog and `plans/done/PHASE X DONE.md` updated when the feature ships
- [x] `AGENTS.md` updated if architecture or contributor guidance changes
