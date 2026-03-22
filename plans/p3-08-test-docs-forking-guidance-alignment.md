# Feature: P3-08 Test, Docs, And Forking Guidance Alignment

## Slug
p3-08-test-docs-forking-guidance-alignment

## Source
Phase 3 backlog item `P3-08 Test, Docs, And Forking Guidance Alignment` in [`plans/PHASE 3 BACKLOG.md`](/Users/jamie/Development/basic_chat_app/plans/PHASE%203%20BACKLOG.md)

## Scope
Tighten the Phase 3 harness boundary by adding explicit regression coverage for harness contracts, registry-backed resolution, normalized failures, and default OpenAI parity, while also aligning contributor-facing docs and Phase 3 planning docs around one consistent explanation of the UI layer, harness layer, and small control/service layer. This slice should also give fork maintainers one obvious path for adding a new harness implementation without touching unrelated route code.

## Non-goals
- Implementing the real alternative provider proof for `P3-09`.
- Adding a user-facing harness picker or changing the persisted chat UX.
- Introducing streaming UI, new tool orchestration behavior, or new persistence concepts.
- Reframing Phase 4 "chat/session forking" work; this slice only covers repository forking and contributor extension guidance.

## Acceptance Criteria
- [x] Regression coverage explicitly proves `ChatHarness` contract behavior, registry-backed binding resolution, normalized failure handling, and current OpenAI default parity.
- [x] Tests include a fake or minimal non-OpenAI harness path that exercises startup wiring and send flow without depending on OpenAI-specific construction.
- [ ] Contributors can follow one obvious documented path to add a new harness implementation behind `agents/chat_harness.py` and `agents/harness_registry.py` without reshaping routes.
- [ ] [`README.md`](/Users/jamie/Development/basic_chat_app/README.md), [`AGENTS.md`](/Users/jamie/Development/basic_chat_app/AGENTS.md), and the active Phase 3 planning docs describe the UI layer, harness layer, and control/service layer with consistent terminology.
- [ ] The updated docs explain the default OpenAI adapter as the shipped baseline, not the architectural model every new harness must copy.

## Risks / Assumptions
The repository already has meaningful harness and route coverage, so this increment is expected to expand and reorganize tests rather than invent a large new test framework. The current docs already mention the harness seam, but they are still somewhat OpenAI-first; this plan assumes terminology can be aligned without changing runtime behavior. It also assumes a dedicated fake/minimal harness can stay test-only and does not need to become a shipped app runtime.

## Implementation Steps
- [x] Step 1: Add or reorganize harness-boundary regression coverage so contract, registry, and default-parity expectations are explicit rather than scattered across unrelated tests. — files: `tests/test_chat_harness_contract.py`, `tests/test_chat_turn_service.py`, `tests/test_main_routes.py`, `tests/test_openai_agent.py`, `tests/test_diagnostics.py`, `tests/test_harness_registry.py`
- [x] Step 2: Introduce a fake or minimal harness fixture/helper that proves the app can boot and execute the normal send flow without OpenAI-specific startup wiring. — files: `tests/test_main_routes.py`, `tests/conftest.py`, `tests/test_chat_turn_service.py`, `tests/test_harness_registry.py`
- [ ] Step 3: Rewrite contributor guidance so adding a harness has one clear extension path and the layer split is described consistently across top-level docs. — files: `README.md`, `AGENTS.md`
- [ ] Step 4: Align active Phase 3 planning language with the shipped docs and current control-layer framing, while leaving ship-time backlog/done moves for the later feature-ship step. — files: `plans/PHASE 3 BACKLOG.md`, `plans/PHASE 3 DESIGN.md`, `plans/PHASES.md`, `plans/done/PHASE 3 DONE.md`

## Tests to Add
- [x] Add dedicated registry-resolution tests covering default selection, unknown harness keys, and optional version mismatches -> covers AC: Regression coverage explicitly proves `ChatHarness` contract behavior, registry-backed binding resolution, normalized failure handling, and current OpenAI default parity.
- [x] Add route/service regression coverage showing a fake harness can be startup-wired and can complete the normal HTMX send flow without OpenAI-specific construction -> covers AC: Tests include a fake or minimal non-OpenAI harness path that exercises startup wiring and send flow without depending on OpenAI-specific construction.
- [ ] Add or expand OpenAI parity tests that lock `run()`/`run_events()` parity, normalized observability, and failure normalization while keeping alternate harnesses possible -> covers AC: Regression coverage explicitly proves `ChatHarness` contract behavior, registry-backed binding resolution, normalized failure handling, and current OpenAI default parity.
- [x] Add a regression test for readiness or diagnostics metadata under non-default harness wiring so observability stays normalized across harness implementations -> covers AC: Tests include a fake or minimal non-OpenAI harness path that exercises startup wiring and send flow without depending on OpenAI-specific construction.

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
