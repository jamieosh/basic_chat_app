# AGENTS.md

## Last Reviewed

- 2026-03-14

## Project Summary

This repository is a basic FastAPI + HTMX chat application that sends user messages to OpenAI and renders responses in a simple web UI.

Current stage:
- MVP/demo quality
- Works as a single-turn request/response chat loop
- Not a full production chat system yet

## What The App Does

- Serves a chat page at `/`
- Accepts message submissions at `/send-message-htmx`
- Calls OpenAI (currently `gpt-4o-mini`) through `agents/openai_agent.py`
- Formats text/code-block output into HTML
- Returns inline bot message HTML for HTMX insertion
- Exposes a basic health check at `/health`

## High-Level Architecture

- `main.py`
  - FastAPI app setup
  - CORS/static/template setup
  - Routes and response/error rendering
- `agents/`
  - `base_agent.py`: abstract interface
  - `openai_agent.py`: OpenAI implementation
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

- This is mostly stateless from a chat perspective:
  - It does not maintain multi-turn conversation history across requests.
- Prompting is template-driven:
  - System prompt and optional context prompt are loaded from `templates/prompts/openai/`.
- UI is optimized for a simple “send message -> append answer” flow with HTMX.

## Known Gaps (Important)

- No auth, persistence, rate controls, or streaming response support.

## Guidance For Future Contributors

- Keep changes minimal and end-to-end verifiable.
- Preserve the HTMX contract:
  - `/send-message-htmx` should return a message HTML snippet for append.
- If you add memory/history, decide whether it is:
  - client-side only, server session-based, or database-backed.
- If you update model behavior, keep prompt templates and model naming in sync.
- Add tests for:
  - route error paths
  - prompt loading/rendering
  - message formatting behavior

## Test Suite

Current tests are located in `tests/` and use `pytest`.

- `tests/test_main_routes.py`
  - Verifies `/`, `/health`, and basic `/send-message-htmx` behavior.
- `tests/test_openai_agent.py`
  - Verifies prompt/message construction and input validation.
- `tests/test_prompt_manager.py`
  - Verifies template rendering and missing-template handling.
- `tests/test_html_formatter.py`
  - Verifies escaping and fenced code-block formatting.
- `tests/e2e/test_chat_smoke.py`
  - Browser smoke test for page load and message send flow (Playwright).

Run tests with:
- `uv run python -m pytest`
- E2E prerequisite:
  - `uv run playwright install chromium`

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
