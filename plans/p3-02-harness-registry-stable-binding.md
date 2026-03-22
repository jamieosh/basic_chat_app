# Feature: P3-02 Harness Registry, Control Wiring, And Stable Binding

## Slug
p3-02-harness-registry-stable-binding

## Source
Phase 3 Backlog: `P3-02 Harness Registry, Control Wiring, And Stable Binding`

## Scope
Add the first real harness-binding layer behind the Phase 3 contract by introducing startup-time harness registry wiring, moving harness resolution out of route-owned app state access, and persisting a stable harness binding on each chat session. The increment should keep the shipped single-default OpenAI setup simple, but make chat creation and later message sends resolve the harness through a small control/service seam rather than treating `main.py` as the harness owner.

The implementation should cover both newly created chats and existing persisted chats so a chat can be resolved against the same harness key for its lifetime without storing provider configuration details directly on the chat row.

## Non-goals
- Migrating more OpenAI-specific request assembly or error handling than needed to support the registry and binding seam. That belongs to `P3-03` and `P3-07`.
- Adding streaming/event-surface changes from `P3-05`.
- Adding a user-facing harness selector or any multi-provider UI.
- Shipping a second real provider implementation. That belongs to `P3-09`.
- Reworking prompt-template ownership or context-builder logic beyond what is required for stable binding.

## Acceptance Criteria
- [x] Startup initializes a harness registry or equivalent factory/resolver, and the route layer no longer owns direct provider-selection wiring.
- [x] New chats persist a stable `harness_key` plus optional `harness_version`, and later sends for that chat resolve the harness from the persisted binding.
- [x] One chat remains bound to one harness configuration for its lifetime, including duplicate replay and revisit flows.
- [x] The default contributor path still works with a single shipped default harness and minimal environment configuration.
- [x] Existing persisted chats remain resolvable after the schema change without forcing contributors to reset local chat data.

## Risks / Assumptions
The current `chat_sessions` schema in [`persistence/db.py`](/Users/jamie/Development/basic_chat_app/persistence/db.py) has no harness-binding fields, so this slice likely needs an additive migration/backfill strategy rather than a schema reset. The plan assumes the stable binding stored on a chat should be the harness identity key and optional version, not provider/model configuration details.

The current request flow in [`main.py`](/Users/jamie/Development/basic_chat_app/main.py) reads a single `app.state.chat_harness` and calls it directly, while [`services/chat_turns.py`](/Users/jamie/Development/basic_chat_app/services/chat_turns.py) only owns turn-request lifecycle state. This increment assumes a small additional control seam is appropriate so route handlers can ask for chat-bound harness resolution without turning `ChatTurnService` into a large orchestration layer.

The shipped baseline should still expose one default registry entry backed by OpenAI, with backend configuration selecting that default and no user-visible harness picker.

## Implementation Steps
- [x] Step 1: Add registry and startup wiring for harness construction and resolution, including a default-harness selection path that keeps the current out-of-box setup simple. — files: `main.py`, `agents/chat_harness.py`, new `agents/harness_registry.py` or equivalent, `agents/__init__.py`, `utils/settings.py`, `tests/test_main_routes.py`, `tests/test_settings.py`
- [x] Step 2: Extend chat persistence to store and reload stable harness bindings, and make new-chat creation stamp the selected harness key/version while preserving compatibility with existing SQLite data. — files: `persistence/db.py`, `persistence/repository.py`, `persistence/__init__.py`, `tests/test_chat_repository.py`
- [x] Step 3: Introduce a small control/service seam that resolves the harness for a started or existing chat and make the send flow depend on that seam rather than a single route-scoped harness instance. — files: `services/chat_turns.py` and/or new `services/chat_control.py`, `services/__init__.py`, `main.py`, `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`
- [x] Step 4: Add regression coverage for stable per-chat binding, missing/unknown harness-key handling, and default-harness parity so the Phase 3 seam is locked in before later provider work. — files: `tests/test_chat_repository.py`, `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, `tests/test_chat_harness_contract.py`

## Tests to Add
- [x] Repository test: creating a chat persists `harness_key` and optional `harness_version`, and the values round-trip on reload -> covers AC: New chats persist a stable `harness_key` plus optional `harness_version`, and later sends for that chat resolve the harness from the persisted binding.
- [x] Repository migration/backfill test: an existing database without harness-binding values remains readable and resolves to the default binding after bootstrap/migration -> covers AC: Existing persisted chats remain resolvable after the schema change without forcing contributors to reset local chat data.
- [x] Service/control test: a started turn returns or can resolve the chat-bound harness identity for both new and existing chats without route-level provider branching -> covers AC: Startup initializes a harness registry or equivalent factory/resolver, and the route layer no longer owns direct provider-selection wiring.
- [x] Route test: `/send-message-htmx` uses the harness bound to the chat session on follow-up sends instead of assuming one global route-owned harness -> covers AC: One chat remains bound to one harness configuration for its lifetime, including duplicate replay and revisit flows.
- [x] Startup test: app startup still succeeds with the shipped single-default configuration and exposes the default harness through the new registry wiring -> covers AC: The default contributor path still works with a single shipped default harness and minimal environment configuration.

## Definition of Done
- [x] All acceptance criteria checked off
- [x] All new or updated tests pass
- [x] `uv run ruff check .` passes
- [x] `uv run mypy .` passes
- [x] `uv run python -m pytest` passes
- [ ] `README.md` updated if user-visible behavior changed
- [x] E2E or visual checks run when UI behavior changes materially
- [ ] `CHANGELOG.md` updated when the feature ships
- [ ] Matching phase backlog and `plans/done/PHASE X DONE.md` updated when the feature ships
- [ ] `AGENTS.md` updated if architecture or contributor guidance changes
