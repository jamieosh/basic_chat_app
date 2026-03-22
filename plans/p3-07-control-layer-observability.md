# Feature: P3-07 Control-Layer Refactor, Error Handling, And Harness Observability

## Slug
p3-07-control-layer-observability

## Source
`plans/PHASE 3 BACKLOG.md` -> `P3-07 Control-Layer Refactor, Error-Handling, And Harness Observability`

## Scope
Tighten the existing `ChatTurnService` into the small control layer that owns normalized harness execution, harness-resolution failure handling, lifecycle finalization, and observability metadata for a send request. Keep `main.py` responsible for HTTP validation, persistence-backed page rendering, and HTMX response shaping, but remove route-level branching that still depends on harness/provider exception details. Extend the current diagnostics/readiness path so normalized harness identity details are available for logs and runtime checks without reintroducing provider-specific logic into routes.

## Non-goals
- Add streaming UI or browser event rendering.
- Introduce a user-facing harness picker or change per-chat binding behavior.
- Add a new provider or alternative harness implementation.
- Turn the control layer into a broad orchestration framework.
- Rewrite unrelated route, template, or frontend behavior.

## Acceptance Criteria
- [x] Route handlers do not branch on provider SDK exception classes or provider-specific error types.
- [x] `ChatTurnService` owns normalized harness run lifecycle coordination, including harness resolution, execution collection, and failure finalization, without becoming a large orchestration system.
- [x] Logs and diagnostics can identify the harness key, optional version, provider identity, and normalized failure category through shared observability data rather than route-specific provider branching.
- [x] Success, failure, duplicate replay, and conflict persistence behavior remain covered by regression tests.
- [x] The app layer remains responsible for persistence-backed rendering and user-facing HTMX responses.
- [x] User-facing failure presentation remains deterministic for normalized failure codes, harness-unavailable cases, and unexpected errors.

## Risks / Assumptions
The current code already has part of the target shape: `services/chat_turns.py` owns duplicate-request lifecycle and failure presentation mapping, while `main.py` still catches `ChatHarnessExecutionError` and `HarnessResolutionError` directly during `/send-message-htmx`. This plan assumes the right increment is to move execution outcome normalization lower without moving HTML rendering into the service layer.

Readiness and startup diagnostics currently report only coarse startup/storage/harness booleans. This slice assumes it is sufficient to add normalized harness identity detail and failure-category visibility to diagnostics/logging without expanding readiness into a full runtime inspection API.

## Implementation Steps
- [x] Step 1: Introduce normalized control-layer execution/result types for send handling so harness resolution, collected execution, failure categorization, and persisted finalization can be coordinated in one service path. — files: `services/chat_turns.py`, `agents/chat_harness.py`, `services/__init__.py`
- [x] Step 2: Refactor `/send-message-htmx` to consume service outcomes instead of catching harness-specific execution and resolution failures inline, while keeping request validation and HTML/HTMX rendering in the route layer. — files: `main.py`, `services/chat_turns.py`
- [x] Step 3: Normalize harness observability fields used by logs and readiness/startup diagnostics so the app can report harness key, optional version, provider identity, and normalized failure category consistently. — files: `services/chat_turns.py`, `utils/diagnostics.py`, `main.py`, `agents/openai_agent.py`
- [x] Step 4: Expand regression coverage for success, normalized failure, harness-unavailable, duplicate replay, and conflict flows through the refactored control-layer path, plus readiness/diagnostic observability assertions. — files: `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, `tests/test_diagnostics.py`, `tests/test_openai_agent.py`

## Tests to Add
- [x] Add service-level coverage for normalized execution outcomes that include harness identity/observability and persisted failure finalization. -> covers AC: `ChatTurnService` owns normalized harness run lifecycle coordination, including harness resolution, execution collection, and failure finalization, without becoming a large orchestration system.
- [x] Add route coverage proving `/send-message-htmx` still renders deterministic error responses for normalized harness failure, harness-unavailable, and unexpected-error cases after the route stops handling harness exceptions directly. -> covers AC: `Route handlers do not branch on provider SDK exception classes or provider-specific error types.`
- [x] Add diagnostics/readiness coverage for normalized harness identity details and failure-category visibility in runtime checks/logging payloads. -> covers AC: `Logs and diagnostics can identify the harness key, optional version, provider identity, and normalized failure category through shared observability data rather than route-specific provider branching.`
- [x] Extend duplicate replay and conflict regressions to prove the refactor preserves existing persistence outcomes for success, failure, duplicate replay, and lifecycle-conflict cases. -> covers AC: `Success, failure, duplicate replay, and conflict persistence behavior remain covered by regression tests.`

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
