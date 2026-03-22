# Feature: P3-04 Context Builders And Harness-Owned Memory Assembly

## Slug
p3-04-context-builders-and-harness-owned-memory-assembly

## Source
Phase 3 backlog item `P3-04 Context Builders And Harness-Owned Memory Assembly` in `plans/PHASE 3 BACKLOG.md`

## Scope
Introduce a harness-owned context-builder seam so each harness can turn the canonical persisted transcript and the latest user message into model-facing context without route-owned memory policy. Preserve the current shipped OpenAI behavior by moving its transcript ordering, prompt rendering, and optional context augmentation behind a default builder implementation that reproduces today’s multi-turn send flow.

## Non-goals
- No UI or HTMX contract changes.
- No summarization, retrieval, or long-term memory features.
- No streaming/event-surface redesign beyond what the existing contract already exposes.
- No tool orchestration or user-facing harness selection.
- No persistence schema change unless build-time inspection proves a small additive field is strictly necessary.

## Acceptance Criteria
- [x] The harness layer exposes a context-builder seam that can assemble model-facing context from the latest user message plus canonical prior transcript without route-level provider shaping.
- [x] The default OpenAI-backed path preserves current system prompt, optional context prompt, transcript ordering, and multi-turn continuity semantics.
- [ ] The web route and small control/service layer keep ownership of request lifecycle and persistence, while memory assembly decisions move behind the harness boundary.
- [ ] Regression tests prove that future memory or context experiments can be introduced behind the harness layer without changing the HTMX send contract.

## Risks / Assumptions
The main risk is accidentally changing prompt shape while refactoring the current OpenAI path, especially the exact ordering of prior turns and the optional prepended user-context template. This plan assumes the persisted `ChatMessage` transcript remains the canonical raw record and that only `user` and `assistant` turns need to participate in default context assembly for this slice. It also assumes `BaseAgent` compatibility can remain lightweight, even if richer context-builder support lands first in the native provider-backed path.

## Implementation Steps
- [x] Step 1: Add normalized context-builder vocabulary and harness request plumbing so the harness contract can express harness-owned context assembly without provider-specific types leaking upward. — files: `agents/chat_harness.py`, `agents/__init__.py`, `agents/context_builders.py`
- [x] Step 2: Refactor the default OpenAI harness to assemble provider messages through the new default context builder while preserving today’s prompt/template behavior and request payload parity. — files: `agents/openai_agent.py`, `utils/prompt_manager.py`, `templates/prompts/openai/system_default.j2`, `templates/prompts/openai/user_default.j2`
- [ ] Step 3: Move route-owned transcript shaping out of the send flow so the app hands canonical prior transcript data into the harness boundary without deciding memory policy itself. — files: `main.py`, `services/chat_turns.py`, `persistence/repository.py`
- [ ] Step 4: Add focused regression coverage for builder parity, harness-owned context assembly, and unchanged send-flow behavior so later memory experiments can stay behind the same seam. — files: `tests/test_chat_harness_contract.py`, `tests/test_openai_agent.py`, `tests/test_main_routes.py`, `tests/test_chat_turn_service.py`, `tests/test_prompt_manager.py`, `tests/test_context_builders.py`

## Tests to Add
- [x] Add builder-parity tests for the default context builder so it reproduces current system prompt, optional user-context prompt, and transcript ordering behavior. -> covers AC: The default OpenAI-backed path preserves current system prompt, optional context prompt, transcript ordering, and multi-turn continuity semantics.
- [x] Add OpenAI harness tests proving provider request construction now delegates through the builder seam without changing the completion request payload seen by the client stub. -> covers AC: The harness layer exposes a context-builder seam that can assemble model-facing context from the latest user message plus canonical prior transcript without route-level provider shaping.
- [ ] Add route/service regression tests proving `/send-message-htmx` still returns the same persisted follow-up behavior while the route no longer owns transcript-to-provider assembly decisions. -> covers AC: The web route and small control/service layer keep ownership of request lifecycle and persistence, while memory assembly decisions move behind the harness boundary.
- [ ] Add contract-level tests with a fake harness or fake builder showing alternate memory assembly can be introduced behind the harness seam without changing the HTMX send contract. -> covers AC: Regression tests prove that future memory or context experiments can be introduced behind the harness layer without changing the HTMX send contract.

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
