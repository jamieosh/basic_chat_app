# AGENTS.md

## Last Reviewed

- 2026-03-22

## Project Summary

This repository is a FastAPI + HTMX chat workbench with persisted multi-turn chats, route-backed chat restoration, and a Phase 3 chat-harness boundary with startup-wired harness resolution and stable per-chat runtime binding.

Current stage:
- Phase 2 baseline complete
- Phase 3 harness decoupling in progress
- Multi-chat, persisted, browser-cookie-scoped local-first chat experience
- Still not a full production chat platform

## What The App Does

- Serves a chat page at `/`
- Redirects `/` into the latest visible chat for the current browser/client when one exists
- Serves chat pages at `/chats/{chat_id}` and a start screen at `/chat-start`
- Renders transcript and chat-list partials for HTMX navigation updates
- Accepts message submissions at `/send-message-htmx`
- Persists user/assistant turns in SQLite and restores transcripts after reload or direct URL revisit
- Prevents duplicate request processing with persisted request IDs and conflict-aware replay
- Supports chat delete while keeping archive backend-only in Phase 2
- Executes chat requests through the `ChatHarness` contract, a startup-wired `HarnessRegistry`, and a shipped OpenAI-backed default harness adapter (`gpt-5-mini`)
- Resolves harness execution through a canonical `run_events()` surface, while the current web flow still collects one deterministic final reply for non-streaming HTMX rendering
- Keeps the harness contract ready for future tool experiments with normalized tool-call/tool-result events and an optional tool orchestration hook
- Persists a stable harness key and optional harness version on each chat session
- Lets harness-owned context builders assemble model-facing prompt and transcript context from the persisted raw conversation record
- Formats text/code-block output into HTML
- Returns inline bot message HTML for HTMX insertion
- Exposes a basic health check at `/health`
- Exposes a readiness check at `/health/ready`

## High-Level Architecture

- `main.py`
  - FastAPI app setup
  - CORS/static/template setup
  - Full page routes, HTMX partial routes, send lifecycle, readiness wiring, and response/error rendering
- `agents/`
  - `base_agent.py`: legacy compatibility shim and harness re-export
  - `chat_harness.py`: app-facing `ChatHarness` contract plus normalized request/result/event/failure/context types, tool vocabulary, and optional tool orchestration seam
  - `context_builders.py`: harness-owned context-builder vocabulary and the shipped default transcript-based builder
  - `harness_registry.py`: startup-time harness construction plus stable binding resolution
  - `openai_agent.py`: default OpenAI-backed harness adapter with provider-specific request construction, default context assembly, and error normalization
- `services/`
  - `chat_turns.py`: small control/service layer for turn-request lifecycle, harness resolution, harness-request construction, failure presentation, and idempotent replay coordination
- `persistence/`
  - `db.py`: SQLite bootstrap and additive schema/backfill for persisted harness binding columns
  - `repository.py`: chat, message, persisted harness binding, and turn-request persistence helpers
- `utils/`
  - `client_identity.py`: browser-cookie-scoped anonymous client identity
  - `diagnostics.py`: startup and readiness diagnostics
  - `prompt_manager.py`: Jinja template loading for system/user prompts
  - `html_formatter.py`: escapes output and formats basic markdown code fences
  - `logging_config.py`: logger bootstrap/config
  - `settings.py`: environment-driven runtime settings
- `templates/`
  - `index.html`: main page shell
  - `components/chat.html`: chat body + form
  - `prompts/openai/*.j2`: prompt templates
- `static/`
  - `js/chat.js`: input handling, typing indicator, HTMX UX wiring
  - `css/chat.css`: chat layout styling

## Dependency Management

- Source of truth for dependencies is:
  - `pyproject.toml` (declared constraints)
  - `uv.lock` (resolved/pinned graph)
- If dependencies change:
  - update via `uv add`/`uv remove` (which updates `pyproject.toml` and `uv.lock`).
  - keep `uv.lock` committed and use `uv sync --frozen` in CI/local verification.

## Planning And Branch Workflow

- Phase planning lives under `plans/`.
- The current active backlog is `plans/PHASE 3 BACKLOG.md`.
- Shipped backlog items move to `plans/done/PHASE 3 DONE.md`.
- Feature implementation plans should live at `plans/<slug>.md` on a matching `codex/<slug>` branch.
- The local helper skills in `.agents/skills/` assume this workflow:
  - `feature-start`: choose/refine a backlog slice and write `plans/<slug>.md`
  - `feature-build`: implement the checked plan incrementally on `codex/<slug>`
  - `feature-ship`: update docs/backlog/changelog, verify, merge to `main`, and clean up
  - `feature-abandon`: safely discard an in-progress `codex/<slug>` branch after confirmation
- Do not overwrite existing user edits in `plans/`, `CHANGELOG.md`, or other shared docs just because a skill expects to update them.

## Run Locally

1. Use Python 3.11+.
2. Install dependencies with `uv`:
   - `uv sync`
3. Create `.env` with:
   - `OPENAI_API_KEY=...`
4. Start app:
   - `uv run uvicorn main:app --reload`
5. Open:
   - `http://localhost:8000`

## Product/Behavior Notes

- Chats are persisted in SQLite and scoped to an anonymous browser cookie.
- Existing chat URLs restore the saved transcript on full page load.
- Follow-up sends append to the same persisted chat until the user starts a new chat or switches chats.
- Duplicate request IDs replay the stored outcome instead of creating duplicate turns.
- The app layer now depends on normalized harness contracts, registry-backed harness resolution, and persisted chat binding rather than provider SDK exceptions or route-owned harness selection.
- The default shipped runtime remains OpenAI-backed, but provider-specific behavior and failure translation should stay inside harness adapter code.
- The harness contract can now represent tool-call and tool-result activity in-memory without changing the current persisted transcript or HTMX response flow.
- New chats are created with the default configured harness binding and keep that binding for their lifetime.
- Prompting is template-driven:
  - System prompt and optional context prompt are loaded from `templates/prompts/openai/`.
- The harness layer now owns prompt assembly and context/memory shaping:
  - routes persist and supply the canonical raw transcript
  - harness-owned context builders turn that transcript into model-facing context
- UI stays server-rendered and HTMX-first rather than introducing SPA-owned chat state.

## Known Gaps (Important)

- No auth, user-facing archive browsing, rate controls, or streaming response support.
- The harness contract is normalized and ready for further Phase 3 work, but the repo is still mid-migration toward richer runtime binding, streaming-ready events, and alternative harness implementations.

## Guidance For Future Contributors

- Keep changes minimal and end-to-end verifiable.
- Preserve the HTMX contract:
  - `/send-message-htmx` should return a message HTML snippet for append.
- Keep the route-backed restore behavior and hidden `chat_session_id` wiring intact when editing the shell.
- Keep provider-specific logic behind `agents/chat_harness.py` interfaces rather than reintroducing it into route handlers.
- Keep prompt assembly and memory/context shaping behind harness-owned context builders rather than in routes.
- Keep tool-call vocabulary, tool-result handling, and any future tool orchestration hooks behind the harness contract rather than adding tool-specific branching to routes.
- Keep default harness selection and binding resolution behind `agents/harness_registry.py` and the small service/control layer rather than in routes.
- Prefer native `run_events()` implementations for provider-backed harnesses, with `run()` left as the shared collector; keep `BaseAgent` and `process_message()` only as compatibility shims for older agent code.
- If you update model behavior, keep prompt templates, settings defaults, harness registry defaults, and persisted binding expectations in sync.
- If you ship a backlog item, keep `README.md`, `AGENTS.md`, `CHANGELOG.md`, and the matching `plans/` backlog/done files aligned.
- Add tests for:
  - repository/service lifecycle behavior
  - route error paths
  - restore/revisit browser behavior when routing changes
  - harness registry and binding resolution behavior
  - harness contract behavior and normalized failure paths
  - prompt loading/rendering
  - message formatting behavior

## Test Suite

Current tests are located in `tests/` and use `pytest`.

- `tests/test_main_routes.py`
  - Verifies page routes, HTMX partials, send replay/conflict paths, and error rendering.
- `tests/test_chat_repository.py`
  - Verifies chat/message persistence plus turn-request lifecycle storage behavior.
- `tests/test_chat_turn_service.py`
  - Verifies idempotent replay and lifecycle conflict behavior through the service layer.
- `tests/test_chat_harness_contract.py`
  - Verifies normalized harness types and compatibility behavior.
- `tests/test_openai_agent.py`
  - Verifies OpenAI harness request construction, normalization, and input validation.
- `tests/test_prompt_manager.py`
  - Verifies template rendering and missing-template handling.
- `tests/test_html_formatter.py`
  - Verifies escaping and fenced code-block formatting.
- `tests/test_settings.py`
  - Verifies environment-driven runtime settings parsing and validation.
- `tests/test_diagnostics.py`
  - Verifies startup and readiness diagnostics behavior.
- `tests/test_logging_config.py`
  - Verifies logging setup behavior.
- `tests/e2e/test_chat_smoke.py`
  - Browser coverage for page load, send flow, restore/revisit behavior, and visual snapshots (Playwright).

Run tests with:
- `uv run python -m pytest`
- E2E prerequisite:
  - `uv run playwright install chromium`
- Visual regression workflow:
  - run `uv run python -m pytest tests/e2e/test_chat_smoke.py -q -k "visual_"`
  - refresh `tests/e2e/snapshots/` only for deliberate UI changes via `UPDATE_VISUAL_BASELINES=1 uv run python -m pytest tests/e2e/test_chat_smoke.py -q -k "visual_"`

## CI Quality Gates

CI runs and enforces all of the following:
- `ruff` linting
- `mypy` type checking
- `pytest` (unit + e2e tests)

## Test Creation Rules

When adding or changing behavior, create or update tests with these rules:

- Place tests under `tests/` and name files/functions with `test_` prefixes.
- Test behavior, not implementation details.
- Use Arrange/Act/Assert structure with clear assertions.
- Keep tests deterministic:
  - no external network calls
  - no real OpenAI API calls
  - mock/stub external dependencies
- Add at least one regression test for every bug fix.
- Keep tests small and focused:
  - one primary behavior per test
  - avoid broad, brittle integration-only tests for simple logic changes
- If the change affects harness/provider boundaries, add or update contract-level tests so route code stays decoupled from provider-specific behavior.
