# AGENTS.md

## Last Reviewed

- 2026-03-15

## Project Summary

This repository is a FastAPI + HTMX chat workbench with persisted multi-turn chats, route-backed chat restoration, and OpenAI-backed responses.

Current stage:
- Phase 2 baseline complete
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
- Calls OpenAI (currently `gpt-5-mini`) through `agents/openai_agent.py`
- Formats text/code-block output into HTML
- Returns inline bot message HTML for HTMX insertion
- Exposes a basic health check at `/health`

## High-Level Architecture

- `main.py`
  - FastAPI app setup
  - CORS/static/template setup
  - Full page routes, HTMX partial routes, send lifecycle, and response/error rendering
- `agents/`
  - `base_agent.py`: abstract interface
  - `openai_agent.py`: OpenAI implementation
- `services/`
  - `chat_turns.py`: turn-request lifecycle, failure mapping, and idempotent replay contract
- `persistence/`
  - `db.py`: SQLite bootstrap
  - `repository.py`: chat, message, and turn-request persistence helpers
- `utils/`
  - `prompt_manager.py`: Jinja template loading for system/user prompts
  - `html_formatter.py`: escapes output and formats basic markdown code fences
  - `logging_config.py`: logger bootstrap/config
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
- Prompting is template-driven:
  - System prompt and optional context prompt are loaded from `templates/prompts/openai/`.
- UI stays server-rendered and HTMX-first rather than introducing SPA-owned chat state.

## Known Gaps (Important)

- No auth, user-facing archive browsing, rate controls, or streaming response support.

## Guidance For Future Contributors

- Keep changes minimal and end-to-end verifiable.
- Preserve the HTMX contract:
  - `/send-message-htmx` should return a message HTML snippet for append.
- Keep the route-backed restore behavior and hidden `chat_session_id` wiring intact when editing the shell.
- If you update model behavior, keep prompt templates and model naming in sync.
- Add tests for:
  - repository/service lifecycle behavior
  - route error paths
  - restore/revisit browser behavior when routing changes
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
- `tests/test_openai_agent.py`
  - Verifies prompt/message construction and input validation.
- `tests/test_prompt_manager.py`
  - Verifies template rendering and missing-template handling.
- `tests/test_html_formatter.py`
  - Verifies escaping and fenced code-block formatting.
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
