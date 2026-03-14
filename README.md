# Python-First LLM Chat Workbench

A lightweight FastAPI + HTMX project for quickly experimenting with LLM chat behavior in Python.

This repository is intentionally a workbench, not a full-featured production chat platform. It is designed to be usable out of the box while staying easy to fork and extend.

## Vision And Roadmap

- Vision charter: `plans/VISION.md`
- Phase model: `plans/PHASES.md`

Those documents define the long-term direction and maturity phases. This README focuses on current usage and contributor workflow.

## Current Capability (Today)

- Server-rendered web chat UI with HTMX interactions.
- Single-turn request/response chat flow.
- In-flight request locking so duplicate submissions are ignored while a response is pending.
- Inline failure handling for validation, service-unavailable, and transport-error states.
- OpenAI-backed agent implementation (`gpt-5-mini` by default).
- Prompt-template-driven system and user prompt construction.
- Neutral `AI Chat` defaults with no implicit domain context or memory.
- Safe HTML rendering with fenced code block formatting.
- Responsive frontend suitable for desktop and mobile.

## Phase 1 Baseline Status

The portability and configuration baseline is now part of the current default behavior:

- Startup path resolution is project-root-aware rather than dependent on the shell's current working directory.
- Runtime behavior is configurable through environment variables instead of route-level or agent-level constants.
- Default CORS behavior matches the current no-auth posture: wildcard origins are allowed, but credentials stay disabled unless you opt into explicit origins.
- Prompt/template selection, OpenAI model choice, timeout, and compatible temperature settings can be changed without modifying application code.
- The browser chat flow prevents duplicate sends, uses a minimal typing indicator during normal requests, and renders degraded-service states inline when the backend is unavailable or a request fails.

## Phase 1 Complete Means

Phase 1 is complete when a contributor can clone the repository, set `OPENAI_API_KEY`, run the app, and successfully chat through the default web UI without changing code.

The completed Phase 1 baseline is:

- single-turn request/response chat only
- deterministic validation and inline request-failure handling
- portable startup and environment-driven runtime configuration
- no frontend build step required for the default UI
- clear extension seams for prompts, provider wiring, and chat UI behavior

Phase 1 does not include:

- authentication
- multi-chat continuity or persisted history
- streaming responses
- generalized chat-runtime/provider abstraction
- deployment hardening for public internet exposure

## Near-Term Product Shape

- Keep the core simple and predictable.
- Maintain a Python-first, minimal-JavaScript approach.
- Preserve obvious extension seams for model, memory, and tool experimentation.

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd basic_chat_app
```

2. Use Python 3.11+ and sync dependencies with `uv`:
```bash
uv sync
```

3. Create your local environment file from the checked-in example:
```bash
cp .env.example .env
```

4. Add your OpenAI API key to `.env`:
```dotenv
OPENAI_API_KEY=your_api_key_here
```

5. Run the application:
```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The application will be available at `http://localhost:8000`.

The app loads `.env` from the project root, so startup does not depend on your current working directory once the project is importable.

## Dependencies

- Python 3.11+
- FastAPI
- HTMX
- OpenAI Python Client
- Jinja2
- python-dotenv

## External Frontend Runtime Assumptions

The default UI intentionally depends on two browser-loaded public CDN assets so the project can stay runnable without a frontend build step in Phase 1.

- Required external hosts:
  - `unpkg.com` for HTMX
  - `cdn.tailwindcss.com` for Tailwind's browser runtime
- Current reviewed asset URLs:
  - HTMX: `https://unpkg.com/htmx.org@1.9.5`
  - Tailwind browser runtime: `https://cdn.tailwindcss.com`
- Responsibility split:
  - HTMX powers the default request/response interaction model for the chat form.
  - Tailwind's browser runtime provides the utility classes used by the page shell and chat layout.
  - `/static/css/chat.css` and `/static/js/chat.js` remain the project-owned frontend assets.
- If those external assets are blocked:
  - without HTMX, the chat form does not perform the intended inline request/append flow
  - without Tailwind's browser runtime, the page still renders HTML but loses much of its layout and visual styling
- Tradeoff:
  - this keeps the default setup minimal and avoids a frontend toolchain
  - it also means the baseline UI relies on public CDN availability and network access from the browser
- Guidance for forks:
  - if you need self-hosted, restricted-network, or air-gapped deployments, plan to replace these CDN references with locally served or otherwise controlled assets
  - treat any change to these asset URLs as an intentional runtime decision, not a cosmetic refactor

Maintainer note:

- HTMX version changes should remain exact and explicitly reviewed.
- Tailwind CDN usage is a temporary Phase 1 convenience for the no-build-step baseline, not a long-term commitment to public-CDN runtime delivery.

## Current Security Posture

The default template is for local development and experimentation, not for exposed public deployment.

- no authentication is included
- no persistence, rate limiting, or CSRF protection is included
- wildcard CORS is part of the current no-auth baseline, with credentials disabled by default
- deployment hardening is intentionally deferred beyond Phase 1

Forks that move beyond trusted local or internal use should plan explicit security and operational hardening.

## Project Structure

```
basic_chat_app/
├── agents/                 # AI agent implementations
│   ├── base_agent.py      # Abstract base agent class
│   └── openai_agent.py    # OpenAI-specific agent implementation
├── static/                # Static assets
│   ├── css/              # CSS styles
│   └── js/               # JavaScript files
├── templates/            # HTML templates
│   ├── components/       # Reusable components
│   └── prompts/         # AI prompt templates
├── utils/               # Utility functions
│   ├── diagnostics.py
│   ├── html_formatter.py
│   ├── logging_config.py
│   ├── prompt_manager.py
│   └── settings.py
├── main.py             # FastAPI application
├── pyproject.toml      # Project metadata and dependencies
└── uv.lock             # Locked dependency versions for uv
```

## Development

Dependency source of truth:
- `pyproject.toml` + `uv.lock`

Run tests with:
```bash
uv run python -m pytest
```

Install Playwright Chromium (required for `tests/e2e/test_chat_smoke.py`):
```bash
uv run playwright install chromium
```

Run the frontend smoke test only:
```bash
uv run python -m pytest tests/e2e -q
```

Run lint and type checks:
```bash
uv run ruff check .
uv run mypy .
```

Install git hooks:
```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

### Adding New Features

1. **New Agent Types**: Extend the `BaseAgent` class in `agents/base_agent.py`
2. **Custom Prompts**: Add new templates in `templates/prompts/<agent_type>/`
3. **UI Components**: Add new components in `templates/components/`

### Configuration

- Logging configuration can be modified in `utils/logging_config.py`
- Prompt templates can be customized in `templates/prompts/`
- UI styling can be adjusted in `static/css/chat.css`
- Runtime configuration is environment-driven through `.env` or process env vars.

Supported runtime environment variables:

- `OPENAI_API_KEY`: required API key for the OpenAI client.
- `OPENAI_MODEL`: optional model name. Default: `gpt-5-mini`.
- `OPENAI_PROMPT_NAME`: optional prompt template suffix. Default: `default`.
- `OPENAI_TEMPERATURE`: optional model temperature from `0.0` to `2.0`. Default: `1.0`.
- `OPENAI_TIMEOUT_SECONDS`: optional OpenAI request timeout. Default: `30`.
- `CORS_ALLOWED_ORIGINS`: comma-separated allowed origins. Default: `*`.
- `CORS_ALLOW_CREDENTIALS`: enables credentialed CORS requests. Default: `false`.
- `CORS_ALLOWED_METHODS`: comma-separated allowed HTTP methods. Default: `*`.
- `CORS_ALLOWED_HEADERS`: comma-separated allowed headers. Default: `*`.
- `LOG_LEVEL`, `COMPONENT_LOG_LEVELS`, `LOG_TO_FILE`, `LOG_DIR`, `APP_NAME`: optional logging controls.

For the default no-auth baseline, keep `CORS_ALLOW_CREDENTIALS=false`. If you enable credentials, use explicit `CORS_ALLOWED_ORIGINS` values instead of `*`.

### Safe Customization Points

- Prompts: edit `templates/prompts/openai/` to change the default system or user prompt behavior.
- Model and runtime settings: use environment variables first, then `utils/settings.py` if you need to change the supported configuration surface.
- Provider wiring: edit `agents/openai_agent.py` to change OpenAI-specific request construction or swap in a different agent implementation behind the existing app contract.
- Chat UI behavior: edit `templates/components/chat.html`, `static/js/chat.js`, and `static/css/chat.css`.

### Baseline Defaults

- The default assistant identity is `AI Chat`.
- The default chat request uses a fixed prompt name. With the default `gpt-5-mini` model, the effective request temperature remains the model default.
- The default system prompt is generic.
- The default user-context prompt remains available as a customization seam, but contributes nothing unless you explicitly add context variables or edit the template.
- The app does not keep multi-turn memory in Phase 1; each request is handled independently.
- The default request UX stays visually quiet on success: only the typing dots appear while a response is in flight, and the footer status area is reserved for validation or failure messaging.

### Best Practices

- Keep structure and APIs straightforward.
- Prefer small, localized changes over broad rewrites.
- Follow established error handling and logging patterns.
- Add or update tests with behavior changes.
- Preserve the current deterministic baseline coverage around startup/configuration, message formatting, and request failure paths.
- Keep docs aligned with `plans/VISION.md` and `plans/PHASES.md`.

## License

[MIT License](LICENSE)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
